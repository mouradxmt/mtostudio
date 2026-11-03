package org.wordcraft.offline;

import android.annotation.SuppressLint;
import android.app.Activity;
import android.app.AlertDialog;
import android.content.Intent;
import android.graphics.Color;
import android.net.ConnectivityManager;
import android.net.NetworkCapabilities;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.util.Base64;
import android.view.WindowInsets;
import android.view.WindowInsetsController;
import android.view.View;
import android.view.KeyEvent;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.FrameLayout;
import android.widget.Button;
import android.widget.CheckBox;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

import androidx.webkit.WebViewAssetLoader;
import androidx.webkit.WebViewCompat;
import androidx.webkit.WebViewFeature;

import org.json.JSONObject;

import java.io.ByteArrayInputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.OutputStream;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.net.URLConnection;
import java.util.Collections;
import java.util.HashMap;
import java.util.UUID;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/** Offline creative suite with native file dialogs and distribution-specific updates. */
public final class MainActivity extends Activity {
    interface Reply { void send(String message); }
    private static final int OPEN = 10, SAVE = 11;
    private static final long MAX_SAVE_BYTES = 256L * 1024 * 1024;
    private final ExecutorService files = Executors.newSingleThreadExecutor();
    private final ExecutorService updates = Executors.newSingleThreadExecutor();
    private SuiteManager suite;
    private SuiteManager.App currentApp;
    private FrameLayout root;
    private TextView updateStatus;
    private boolean checking, installing;
    private boolean immersive;
    private Button fullscreenControl;
    private String status = "All 15 apps are included and ready offline.";
    private WebView web;
    private OfflineGecko gecko;
    volatile JSONObject engineState;
    private ValueCallback<Uri[]> openCallback;
    private Reply pickerReply;
    private int pickerId;
    // These fields belong to the file executor; picker completion schedules its work there.
    private volatile String token;
    private Uri destination;
    private File staged;
    private OutputStream stageOutput;
    private long stagedBytes;

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        File[] oldImports = PickedDocuments.root(this).listFiles();
        files.execute(() -> {
            File[] leftovers = getCacheDir().listFiles((dir, name) -> name.startsWith("wordcraft-save-") && name.endsWith(".tmp"));
            if (leftovers != null) for (File leftover : leftovers) leftover.delete();
            if (oldImports != null) for (File leftover : oldImports) PickedDocuments.delete(leftover);
        });
        root = new FrameLayout(this);
        setContentView(root);
        if (Build.VERSION.SDK_INT >= 30) {
            getWindow().setDecorFitsSystemWindows(false);
            WindowInsetsController controller = getWindow().getInsetsController();
            if (controller != null) controller.setSystemBarsAppearance(
                WindowInsetsController.APPEARANCE_LIGHT_STATUS_BARS | WindowInsetsController.APPEARANCE_LIGHT_NAVIGATION_BARS,
                WindowInsetsController.APPEARANCE_LIGHT_STATUS_BARS | WindowInsetsController.APPEARANCE_LIGHT_NAVIGATION_BARS);
            root.setOnApplyWindowInsetsListener((view, insets) -> {
                android.graphics.Insets bars = insets.getInsets(WindowInsets.Type.systemBars() | WindowInsets.Type.ime());
                view.setPadding(bars.left, bars.top, bars.right, bars.bottom);
                return insets;
            });
        }
        try { suite = new SuiteManager(getApplicationContext()); }
        catch (Exception error) {
            new AlertDialog.Builder(this).setTitle("Suite could not load").setMessage(error.getMessage())
                .setPositiveButton("Close", (dialog, which) -> finish()).show();
            return;
        }
        immersive = suite.prefs.getBoolean("immersive", false);
        showHome();
        applyFullscreen();
        maybeCheckUpdates();
        SuiteManager.App target = AppShortcuts.target(getIntent(), suite);
        if (target != null) openApp(target);
    }

    @Override protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        setIntent(intent);
        if (suite == null) return;
        navigateTo(AppShortcuts.target(intent, suite));
    }

    private Button fullscreenButton() {
        Button control = button(immersive ? "Exit full screen" : "Full screen", () -> {});
        fullscreenControl = control;
        control.setOnClickListener(view -> {
            immersive = !immersive;
            suite.prefs.edit().putBoolean("immersive", immersive).apply();
            applyFullscreen();
            control.setText(immersive ? "Exit full screen" : "Full screen");
        });
        return control;
    }

    private void applyFullscreen() {
        if (Build.VERSION.SDK_INT >= 30) {
            WindowInsetsController controller = getWindow().getInsetsController();
            if (controller == null) return;
            controller.setSystemBarsBehavior(WindowInsetsController.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE);
            if (immersive) controller.hide(WindowInsets.Type.systemBars());
            else controller.show(WindowInsets.Type.systemBars());
        } else {
            getWindow().getDecorView().setSystemUiVisibility(immersive ? View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY
                | View.SYSTEM_UI_FLAG_FULLSCREEN | View.SYSTEM_UI_FLAG_HIDE_NAVIGATION
                | View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN | View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION
                | View.SYSTEM_UI_FLAG_LAYOUT_STABLE : View.SYSTEM_UI_FLAG_VISIBLE);
        }
    }

    @Override public boolean dispatchKeyEvent(KeyEvent event) {
        if (event.getAction() == KeyEvent.ACTION_DOWN && event.getRepeatCount() == 0
            && (event.getKeyCode() == KeyEvent.KEYCODE_F11 || event.isCtrlPressed() && event.isAltPressed() && event.getKeyCode() == KeyEvent.KEYCODE_F)) {
            immersive = !immersive;
            if (suite != null) suite.prefs.edit().putBoolean("immersive", immersive).apply();
            applyFullscreen();
            if (fullscreenControl != null) fullscreenControl.setText(immersive ? "Exit full screen" : "Full screen");
            return true;
        }
        return super.dispatchKeyEvent(event);
    }

    private int dp(int size) { return Math.round(size * getResources().getDisplayMetrics().density); }

    private TextView text(String value, int size, int color) {
        TextView label = new TextView(this);
        label.setText(value); label.setTextSize(size); label.setTextColor(color);
        label.setPadding(0, dp(4), 0, dp(4));
        return label;
    }

    private Button button(String title, Runnable action) {
        Button button = new Button(this);
        button.setText(title); button.setAllCaps(false); button.setOnClickListener(view -> action.run());
        return button;
    }

    private void showHome() {
        if (gecko != null) { gecko.close(); gecko = null; }
        engineState = null;
        WebView retired = web;
        web = null;
        if (retired != null) retired.destroy();
        currentApp = null;
        root.removeAllViews();
        ScrollView scroll = new ScrollView(this);
        LinearLayout column = new LinearLayout(this);
        column.setOrientation(LinearLayout.VERTICAL);
        column.setPadding(dp(20), dp(20), dp(20), dp(24));
        column.setBackgroundColor(Color.rgb(243, 245, 248));
        column.addView(text(getString(R.string.app_name), 28, Color.rgb(15, 23, 42)));
        column.addView(text("15 creative apps · Your files, on your device", 15, Color.rgb(71, 85, 105)));
        column.addView(fullscreenButton());
        updateStatus = text(status, 14, Color.rgb(71, 85, 105));
        column.addView(updateStatus);
        if (BuildConfig.EXTERNAL_UPDATES) {
        Button check = button(checking ? "Checking GitHub…" : "Check GitHub updates", this::checkUpdates);
        check.setEnabled(!checking && !installing); column.addView(check);
        CheckBox auto = new CheckBox(this);
        auto.setText(R.string.auto_update_check);
        auto.setChecked(suite.prefs.getBoolean("autoCheck", true));
        auto.setOnCheckedChangeListener((view, enabled) -> suite.prefs.edit().putBoolean("autoCheck", enabled).apply());
        column.addView(auto);
        int available = 0;
        for (SuiteManager.App app : suite.apps) if (suite.available(app) != null) available++;
        if (available > 0) {
            Button all = button("Update all (" + available + ")", () -> installUpdates(null));
            all.setEnabled(!checking && !installing); column.addView(all);
        }
        }
        for (SuiteManager.App app : suite.apps) {
            LinearLayout card = new LinearLayout(this);
            card.setOrientation(LinearLayout.VERTICAL); card.setPadding(dp(16), dp(12), dp(16), dp(12));
            card.setBackgroundColor(Color.WHITE);
            LinearLayout.LayoutParams layout = new LinearLayout.LayoutParams(-1, -2); layout.topMargin = dp(12);
            column.addView(card, layout);
            card.addView(text(app.name, 21, Color.rgb(15, 23, 42)));
            card.addView(text(app.description, 14, Color.rgb(71, 85, 105)));
            String installed = suite.installedVersion(app);
            JSONObject candidate = suite.available(app);
            card.addView(text("Installed " + installed + (candidate == null ? " · Ready offline" : " · Update " + candidate.optString("version") + " available"), 13, Color.rgb(71, 85, 105)));
            LinearLayout actions = new LinearLayout(this);
            Button open = button("Open", () -> openApp(app)); open.setEnabled(!installing); actions.addView(open);
            actions.addView(button("Add to Home", () -> AppShortcuts.pin(this, app)));
            if (candidate != null) {
                Button update = button("Update", () -> installUpdates(app)); update.setEnabled(!checking && !installing); actions.addView(update);
            }
            card.addView(actions);
            if (suite.installedRoot(app) != null) {
                Button restore = button("Use bundled " + app.bundledVersion, () -> new AlertDialog.Builder(this)
                    .setTitle("Use bundled " + app.name + "?").setMessage("The bundled version is " + app.bundledVersion + ". Save any work first.")
                    .setNegativeButton("Cancel", null).setPositiveButton("Use bundled", (dialog, which) -> { suite.useBundled(app); showHome(); }).show());
                restore.setEnabled(!installing); card.addView(restore);
            }
        }
        column.addView(text("Published by " + BuildConfig.PUBLISHER_NAME + ". Save before switching apps. Editing stays on your device."
            + (BuildConfig.EXTERNAL_UPDATES ? " Engine updates use GitHub." : " App updates are delivered through Google Play."), 13, Color.rgb(71, 85, 105)));
        column.addView(button("Privacy policy", () -> showAssetText("Privacy policy", "privacy-policy.txt")));
        column.addView(button("Support", () -> {
            try { startActivity(new Intent(Intent.ACTION_VIEW, Uri.parse(BuildConfig.PUBLISHER_WEBSITE))); }
            catch (Exception error) { Toast.makeText(this, BuildConfig.PUBLISHER_WEBSITE, Toast.LENGTH_LONG).show(); }
        }));
        column.addView(button("About & licenses", () -> {
            try (InputStream input = getAssets().open("THIRD_PARTY_NOTICES.txt")) {
                TextView notice = text(new String(SuiteManager.read(input, 1024 * 1024), StandardCharsets.UTF_8), 14, Color.rgb(15, 23, 42));
                notice.setTextIsSelectable(true); notice.setPadding(dp(20), dp(16), dp(20), dp(16));
                ScrollView page = new ScrollView(this); page.addView(notice);
                new AlertDialog.Builder(this).setTitle("About " + getString(R.string.app_name)).setView(page).setPositiveButton("Close", null).show();
            } catch (Exception error) { Toast.makeText(this, "Could not read notices", Toast.LENGTH_SHORT).show(); }
        }));
        scroll.addView(column); root.addView(scroll);
    }

    private void showAssetText(String title, String path) {
        try (InputStream input = getAssets().open(path)) {
            TextView content = text(new String(SuiteManager.read(input, 1024 * 1024), StandardCharsets.UTF_8), 14, Color.rgb(15, 23, 42));
            content.setTextIsSelectable(true); content.setPadding(dp(20), dp(16), dp(20), dp(16));
            ScrollView page = new ScrollView(this); page.addView(content);
            new AlertDialog.Builder(this).setTitle(title).setView(page).setPositiveButton("Close", null).show();
        } catch (Exception error) { Toast.makeText(this, "Could not read " + title, Toast.LENGTH_SHORT).show(); }
    }

    private boolean online() {
        ConnectivityManager manager = (ConnectivityManager) getSystemService(CONNECTIVITY_SERVICE);
        NetworkCapabilities capabilities = manager.getNetworkCapabilities(manager.getActiveNetwork());
        return capabilities != null && capabilities.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)
            && capabilities.hasCapability(NetworkCapabilities.NET_CAPABILITY_VALIDATED);
    }

    private void progress(String message) {
        runOnUiThread(() -> {
            if (isDestroyed()) return;
            status = message;
            if (currentApp == null && updateStatus != null) updateStatus.setText(message);
        });
    }

    private void checkUpdates() {
        if (!BuildConfig.EXTERNAL_UPDATES) return;
        if (checking || installing) return;
        if (!online()) { progress("You are offline. All installed apps are still ready to open."); return; }
        checking = true; showHome();
        updates.execute(() -> {
            try { suite.checkUpdates(this::progress); }
            catch (Exception error) { progress("Could not check updates: " + error.getMessage()); }
            runOnUiThread(() -> { checking = false; if (!isDestroyed() && currentApp == null) showHome(); });
        });
    }

    private void maybeCheckUpdates() {
        if (!BuildConfig.EXTERNAL_UPDATES) return;
        if (!checking && !installing && currentApp == null && suite.prefs.getBoolean("autoCheck", true)
            && System.currentTimeMillis() - suite.prefs.getLong("lastCheck", 0) > 86400000L && online()) checkUpdates();
    }

    private void installUpdates(SuiteManager.App selected) {
        if (checking || installing) return;
        if (!online()) { progress("Connect to the Internet to download updates."); return; }
        installing = true; showHome();
        updates.execute(() -> {
            int installed = 0, failed = 0;
            String lastFailure = "";
            for (SuiteManager.App app : suite.apps) {
                if (selected != null && app != selected) continue;
                JSONObject candidate = suite.available(app);
                if (candidate == null) continue;
                try { suite.install(app, candidate, this::progress); installed++; }
                catch (Exception error) { failed++; lastFailure = app.name + ": " + error.getMessage(); }
            }
            progress("Updated " + installed + " apps." + (failed > 0 ? " " + failed + " failed; previous versions kept. " + lastFailure : " Ready offline."));
            runOnUiThread(() -> { installing = false; if (!isDestroyed() && currentApp == null) showHome(); });
        });
    }

    private void openApp(SuiteManager.App app) {
        if (installing) return;
        if (suite.prefs.getBoolean("systemEngine", false)) { openSystemApp(app); return; }
        currentApp = app;
        engineState = null;
        root.removeAllViews();
        LinearLayout screen = new LinearLayout(this); screen.setOrientation(LinearLayout.VERTICAL);
        LinearLayout toolbar = new LinearLayout(this); toolbar.setGravity(android.view.Gravity.CENTER_VERTICAL);
        toolbar.addView(button("‹ Apps", this::leaveEditor));
        toolbar.addView(fullscreenButton());
        toolbar.addView(text(app.name + " " + suite.installedVersion(app), 16, Color.rgb(15, 23, 42)));
        screen.addView(toolbar);
        root.addView(screen);
        try {
            gecko = new OfflineGecko(this, suite, app, this::handleMessage, (callback, multiple) -> {
                if (openCallback != null) openCallback.onReceiveValue(null);
                openCallback = callback;
                Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT).addCategory(Intent.CATEGORY_OPENABLE)
                    .setType("*/*").addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
                    .putExtra(Intent.EXTRA_ALLOW_MULTIPLE, multiple).putExtra(Intent.EXTRA_LOCAL_ONLY, true);
                try { startActivityForResult(intent, OPEN); }
                catch (Exception error) { openCallback.onReceiveValue(null); openCallback = null; }
            }, () -> {
                pickerReply = null;
                files.execute(MainActivity.this::cleanup);
                new AlertDialog.Builder(this).setTitle(app.name + " stopped")
                    .setMessage("The editor could not continue. Save frequently to preserve your work.")
                    .setPositiveButton("Back to apps", (dialog, which) -> showHome()).setCancelable(false).show();
            });
            screen.addView(gecko.view, new LinearLayout.LayoutParams(-1, 0, 1));
        } catch (Exception error) {
            new AlertDialog.Builder(this).setTitle("Could not start editor").setMessage(error.getMessage())
                .setPositiveButton("Back to apps", (dialog, which) -> showHome()).show();
        }
    }

    private void handleMessage(JSONObject data, Reply reply) {
        int id = data.optInt("id", -1);
        try {
            String action = data.getString("action");
            if (action.equals("ping")) respond(reply, id, true, null, false);
            else if (action.equals("health")) {
                engineState = data.getJSONObject("state");
                respond(reply, id, true, null, false);
            } else if (action.equals("pick")) pick(data, id, reply);
            else if (action.equals("notice")) {
                Toast.makeText(this, data.optString("message", "Save failed"), Toast.LENGTH_LONG).show();
                respond(reply, id, true, null, false);
            } else {
                final int requestId = id;
                files.execute(() -> process(data, requestId, reply));
            }
        } catch (Exception error) { respond(reply, id, null, "Invalid editor request", false); }
    }

    // JavaScript is required by the bundled WASM apps; remote pages and resources are blocked.
    @SuppressLint("SetJavaScriptEnabled")
    private void openSystemApp(SuiteManager.App app) {
        if (installing) return;
        currentApp = app;
        root.removeAllViews();
        LinearLayout screen = new LinearLayout(this); screen.setOrientation(LinearLayout.VERTICAL);
        LinearLayout toolbar = new LinearLayout(this); toolbar.setGravity(android.view.Gravity.CENTER_VERTICAL);
        toolbar.addView(button("‹ Apps", this::leaveEditor));
        toolbar.addView(fullscreenButton());
        toolbar.addView(text(app.name + " " + suite.installedVersion(app), 16, Color.rgb(15, 23, 42)));
        screen.addView(toolbar);
        web = new WebView(this);
        screen.addView(web, new LinearLayout.LayoutParams(-1, 0, 1)); root.addView(screen);
        WebSettings settings = web.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setAllowFileAccess(false);
        settings.setAllowContentAccess(true); // Only user-picked document URIs.
        settings.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        settings.setMediaPlaybackRequiresUserGesture(true);
        WebView.setWebContentsDebuggingEnabled(BuildConfig.DEBUG);

        WebViewAssetLoader loader = new WebViewAssetLoader.Builder()
            .setDomain(app.id + ".artcraft.invalid")
            .addPathHandler("/", path -> {
                try {
                    if (path.isEmpty()) path = "index.html";
                    InputStream input = suite.open(app, path);
                    if (path.equals("index.html")) {
                        String html;
                        try (InputStream source = input) { html = new String(SuiteManager.read(source, 4 * 1024 * 1024), StandardCharsets.UTF_8); }
                        if (!html.contains("/__native-save.js")) html = html.replaceFirst("(?i)<head\\b[^>]*>", "$0<script src=\"/__native-save.js\"></script>");
                        input = new ByteArrayInputStream(html.getBytes(StandardCharsets.UTF_8));
                    }
                    String mime = path.endsWith(".wasm") ? "application/wasm" : path.endsWith(".js") ? "text/javascript"
                        : path.endsWith(".html") ? "text/html" : path.endsWith(".css") ? "text/css"
                        : path.endsWith(".json") ? "application/json" : URLConnection.guessContentTypeFromName(path);
                    return new WebResourceResponse(mime == null ? "application/octet-stream" : mime, null, input);
                } catch (Exception e) {
                    if (BuildConfig.DEBUG) android.util.Log.e("SuiteAssets", app.id + "/" + path, e);
                    return blocked();
                }
            }).build();
        web.setWebViewClient(new WebViewClient() {
            @Override public WebResourceResponse shouldInterceptRequest(WebView view, WebResourceRequest request) {
                WebResourceResponse local = loader.shouldInterceptRequest(request.getUrl());
                return local != null ? local : blocked();
            }
            @Override public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                Uri uri = request.getUrl();
                // Allow local reloads and renderer fallback; remote navigation remains blocked.
                return !"https".equals(uri.getScheme()) || !(app.id + ".artcraft.invalid").equals(uri.getHost());
            }
            @Override public boolean onRenderProcessGone(WebView view, android.webkit.RenderProcessGoneDetail detail) {
                if (view != web) return true;
                view.destroy();
                web = null;
                pickerReply = null;
                files.execute(MainActivity.this::cleanup);
                new AlertDialog.Builder(MainActivity.this).setTitle(app.name + " stopped")
                    .setMessage("The editor ran out of resources or stopped unexpectedly. Unsaved edits may be lost. You can reopen your last saved file.")
                    .setPositiveButton("Back to apps", (dialog, which) -> showHome()).setCancelable(false).show();
                return true;
            }
        });
        web.setWebChromeClient(new WebChromeClient() {
            @Override public boolean onShowFileChooser(WebView view, ValueCallback<Uri[]> callback, FileChooserParams params) {
                if (openCallback != null) openCallback.onReceiveValue(null);
                openCallback = callback;
                Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT).addCategory(Intent.CATEGORY_OPENABLE)
                    .setType("*/*").putExtra(Intent.EXTRA_ALLOW_MULTIPLE, params.getMode() == FileChooserParams.MODE_OPEN_MULTIPLE);
                intent.putExtra(Intent.EXTRA_LOCAL_ONLY, true);
                try { startActivityForResult(intent, OPEN); }
                catch (Exception error) { openCallback.onReceiveValue(null); openCallback = null; }
                return true;
            }
        });
        web.setDownloadListener((url, userAgent, disposition, mime, length) ->
            Toast.makeText(this, "Use File → Save As or Export to save this file.", Toast.LENGTH_LONG).show());

        if (WebViewFeature.isFeatureSupported(WebViewFeature.WEB_MESSAGE_LISTENER)) {
            WebViewCompat.addWebMessageListener(web, "AndroidDocuments", Collections.singleton(app.origin()),
                (view, message, origin, mainFrame, proxy) -> {
                    Reply reply = proxy::postMessage;
                    if (!mainFrame || !app.origin().equals(origin.toString())) return;
                    try { handleMessage(new JSONObject(message.getData()), reply); }
                    catch (Exception error) { respond(reply, -1, null, "Invalid editor request", false); }
                });
        } else {
            new AlertDialog.Builder(this).setTitle("Update Android System WebView")
                .setMessage("This app needs a newer Android System WebView. Update it once, then use the suite offline.")
                .setPositiveButton("Back to apps", (dialog, which) -> showHome()).setCancelable(false).show();
            return;
        }
        web.loadUrl(app.origin() + "/index.html?webgl");
    }

    private static WebResourceResponse blocked() {
        return new WebResourceResponse("text/plain", "UTF-8", 404, "Not Found", new HashMap<>(),
            new ByteArrayInputStream(new byte[0]));
    }

    private void pick(JSONObject data, int id, Reply reply) {
        if (pickerReply != null) { respond(reply, id, null, "Another save picker is open", false); return; }
        pickerReply = reply;
        pickerId = id;
        String name = data.optString("name", "Document.docx").replaceAll("[/\\\\\\p{Cntrl}]", "_");
        String mime = data.optString("mime", "application/octet-stream");
        Intent intent = new Intent(Intent.ACTION_CREATE_DOCUMENT).addCategory(Intent.CATEGORY_OPENABLE)
            .setType(mime).putExtra(Intent.EXTRA_TITLE, name).putExtra(Intent.EXTRA_LOCAL_ONLY, true);
        try { startActivityForResult(intent, SAVE); }
        catch (Exception error) {
            pickerReply = null;
            respond(reply, id, null, "No document picker is available", false);
        }
    }

    @Override protected void onActivityResult(int request, int result, Intent data) {
        super.onActivityResult(request, result, data);
        if (request == OPEN && openCallback != null) {
            Uri[] uris = null;
            if (result == RESULT_OK && data != null) {
                if (data.getClipData() != null) {
                    int count = Math.min(data.getClipData().getItemCount(), 2000);
                    uris = new Uri[count];
                    for (int i = 0; i < count; i++) uris[i] = data.getClipData().getItemAt(i).getUri();
                } else if (data.getData() != null) uris = new Uri[]{data.getData()};
            }
            openCallback.onReceiveValue(uris);
            openCallback = null;
        }
        if (request == SAVE && pickerReply != null) {
            Reply reply = pickerReply;
            int id = pickerId;
            pickerReply = null;
            if (result != RESULT_OK || data == null || data.getData() == null) {
                respond(reply, id, null, "Save cancelled", true);
                return;
            }
            Uri uri = data.getData();
            files.execute(() -> {
                try {
                    if (token != null) throw new IllegalStateException("Finish the previous save first");
                    staged = File.createTempFile("wordcraft-save-", ".tmp", getCacheDir());
                    stageOutput = new FileOutputStream(staged);
                    destination = uri;
                    stagedBytes = 0;
                    token = UUID.randomUUID().toString();
                    respond(reply, id, token, null, false);
                } catch (Exception error) { respond(reply, id, null, "Could not start save: " + error.getMessage(), false); }
            });
        }
    }

    private void process(JSONObject data, int id, Reply reply) {
        try {
            if (token == null || !token.equals(data.optString("token"))) throw new IllegalStateException("Save is no longer active");
            switch (data.getString("action")) {
                case "append": {
                    String encoded = data.getString("bytes");
                    if (encoded.length() > 65536) throw new IllegalArgumentException("Save chunk is too large");
                    byte[] bytes = Base64.decode(encoded, Base64.NO_WRAP);
                    if (stagedBytes + bytes.length > MAX_SAVE_BYTES) throw new IllegalArgumentException("File exceeds the 256 MB save limit");
                    stageOutput.write(bytes);
                    stagedBytes += bytes.length;
                    break;
                }
                case "finish": {
                    stageOutput.close();
                    stageOutput = null;
                    try (OutputStream output = getContentResolver().openOutputStream(destination, "wt");
                         FileInputStream input = new FileInputStream(staged)) {
                        if (output == null) throw new IllegalStateException("Cannot open destination");
                        byte[] buffer = new byte[65536];
                        int count;
                        while ((count = input.read(buffer)) != -1) output.write(buffer, 0, count);
                        output.flush();
                    }
                    cleanup();
                    break;
                }
                case "abort": cleanup(); break;
                default: throw new IllegalArgumentException("Unknown save operation");
            }
            respond(reply, id, true, null, false);
        } catch (Exception error) {
            cleanup();
            respond(reply, id, null, "Could not save: " + error.getMessage(), false);
        }
    }

    private void cleanup() {
        try { if (stageOutput != null) stageOutput.close(); } catch (Exception ignored) { }
        if (staged != null) staged.delete();
        stageOutput = null;
        staged = null;
        destination = null;
        token = null;
        stagedBytes = 0;
    }

    private void respond(Reply reply, int id, Object value, String error, boolean cancelled) {
        try {
            JSONObject response = new JSONObject().put("id", id).put("value", value)
                .put("error", error).put("cancelled", cancelled);
            runOnUiThread(() -> {
                if (!isDestroyed()) {
                    try { reply.send(response.toString()); }
                    catch (IllegalStateException ignored) { /* The editor's renderer has gone away. */ }
                }
            });
        } catch (Exception ignored) { }
    }

    private void leaveEditor() {
        navigateTo(null);
    }

    private void navigateTo(SuiteManager.App next) {
        if (installing) {
            Toast.makeText(this, "Wait for the update to finish before switching apps.", Toast.LENGTH_LONG).show();
            return;
        }
        if (next != null && next == currentApp) return;
        if (token != null || pickerReply != null) {
            Toast.makeText(this, "Wait for the save to finish before switching apps.", Toast.LENGTH_LONG).show();
            return;
        }
        Runnable change = () -> {
            if (openCallback != null) { openCallback.onReceiveValue(null); openCallback = null; }
            showHome();
            if (next != null) openApp(next);
            else maybeCheckUpdates();
        };
        if (currentApp == null) { change.run(); return; }
        new AlertDialog.Builder(this).setTitle(next == null ? "Return to the suite?" : "Open " + next.name + "?")
            .setMessage("Save your work before switching apps. Unsaved edits will be lost.")
            .setNegativeButton("Keep editing", null)
            .setPositiveButton(next == null ? "Back to apps" : "Switch app", (dialog, which) -> change.run()).show();
    }

    @Override public void onBackPressed() {
        if (currentApp != null) { leaveEditor(); return; }
        if (installing) {
            Toast.makeText(this, "An update is installing. Wait for it to finish.", Toast.LENGTH_LONG).show();
            return;
        }
        finish();
    }

    @Override protected void onDestroy() {
        if (openCallback != null) openCallback.onReceiveValue(null);
        files.execute(this::cleanup);
        files.shutdown();
        updates.shutdown();
        if (gecko != null) { gecko.close(); gecko = null; }
        WebView retired = web;
        web = null;
        if (retired != null) retired.destroy();
        super.onDestroy();
    }
}
