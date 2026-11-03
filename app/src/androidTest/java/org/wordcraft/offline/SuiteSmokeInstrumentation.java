package org.wordcraft.offline;

import android.app.Activity;
import android.app.Instrumentation;
import android.content.Intent;
import android.graphics.Bitmap;
import android.os.Bundle;
import android.os.ParcelFileDescriptor;
import android.os.SystemClock;
import android.util.Log;
import android.view.View;
import android.view.ViewGroup;
import android.webkit.WebView;
import android.widget.Button;
import android.widget.TextView;
import org.json.JSONArray;
import org.json.JSONObject;
import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.lang.reflect.Method;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;

/** Device-only integration test: real offline WebViews and an actual GitHub package update. */
public final class SuiteSmokeInstrumentation extends Instrumentation {
    private MainActivity activity;
    private int checks;
    private File results;
    private boolean menusOnly;
    private boolean importsOnly;
    private final java.util.List<String> engineFailures = new java.util.ArrayList<>();
    private void require(boolean condition, String message) { if (!condition) throw new AssertionError(message); }
    private void log(String message) { Log.i("SuiteSmoke", message); }
    @Override public void onCreate(Bundle arguments) {
        super.onCreate(arguments);
        menusOnly = arguments != null && "true".equals(arguments.getString("menusOnly"));
        importsOnly = arguments != null && "true".equals(arguments.getString("importsOnly"));
        start();
    }

    @Override public void onStart() {
        Bundle result = new Bundle();
        try {
            if (importsOnly) {
                checks = DocumentImportChecks.run(this);
                result.putString("stream", "Passed " + checks + " document-provider import checks.\n");
                finish(Activity.RESULT_OK, result);
                return;
            }
            getTargetContext().getSharedPreferences("suite", 0).edit()
                .putBoolean("autoCheck", false).putBoolean("immersive", false).commit();
            results = new File(getTargetContext().getFilesDir(), "smoke-results"); results.mkdirs();
            shell("cmd connectivity airplane-mode enable");
            activity = (MainActivity) startActivitySync(new Intent(getTargetContext(), MainActivity.class).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK));
            SuiteManager manager = new SuiteManager(getTargetContext());
            if (menusOnly) {
                menuRegression(manager);
                shell("cmd connectivity airplane-mode disable");
                result.putString("stream", "Passed " + checks + " offline menu interaction checks. Screenshots in files/smoke-results.\n");
                finish(Activity.RESULT_OK, result);
                return;
            }
            require(manager.apps.size() == 15, "Expected all 15 apps");
            Intent icons = new Intent(Intent.ACTION_MAIN).addCategory(Intent.CATEGORY_LAUNCHER).setPackage(getTargetContext().getPackageName());
            require(getTargetContext().getPackageManager().queryIntentActivities(icons, 0).size() == 16, "Missing suite/app launcher icons");
            checks++; log("SHORTCUT PASS suite icon and all 15 app icons registered");
            runOnMainSync(() -> {
                TextView control = label(activity.getWindow().getDecorView(), "Full screen");
                require(control != null, "Missing full screen control"); control.performClick();
            });
            SystemClock.sleep(600);
            require(manager.prefs.getBoolean("immersive", false), "Fullscreen control did not persist");
            runOnMainSync(() -> require(!activity.getWindow().getDecorView().getRootWindowInsets()
                .isVisible(android.view.WindowInsets.Type.statusBars()), "Full screen did not hide the status bar"));
            runOnMainSync(() -> activity.dispatchKeyEvent(new android.view.KeyEvent(android.view.KeyEvent.ACTION_DOWN, android.view.KeyEvent.KEYCODE_F11)));
            SystemClock.sleep(600);
            require(!manager.prefs.getBoolean("immersive", true), "F11 did not exit fullscreen");
            runOnMainSync(() -> require(activity.getWindow().getDecorView().getRootWindowInsets()
                .isVisible(android.view.WindowInsets.Type.statusBars()), "F11 did not restore the status bar"));
            checks++; log("FULLSCREEN PASS native control and F11");
            screenshot("launcher");
            for (SuiteManager.App app : manager.apps) {
                try {
                    runOnMainSync(() -> activity.startActivity(new Intent(Intent.ACTION_MAIN)
                        .setComponent(new android.content.ComponentName(getTargetContext().getPackageName(), MainActivity.class.getPackage().getName() + "." + AppShortcuts.alias(app)))
                        .addCategory(Intent.CATEGORY_LAUNCHER)));
                    waitForIdleSync(); ready(app.id); screenshot(app.id);
                    checks++; log("OFFLINE SHORTCUT PASS " + app.name);
                } catch (AssertionError error) {
                    engineFailures.add(error.toString()); log("ENGINE FAIL " + error);
                    log("GL LIMIT " + glLimit()); screenshot("failed-" + app.id);
                } finally { home(); }
            }
            if (!BuildConfig.EXTERNAL_UPDATES) {
                SuiteManager.App first = manager.apps.get(0);
                manager.prefs.edit().putString(first.id + ".available", "{\"version\":\"99.0.0\"}").commit();
                require(manager.available(first) == null, "Play edition exposed an external update");
                boolean denied = false;
                try { manager.checkUpdates(this::log); } catch (IllegalStateException expected) { denied = true; }
                require(denied, "Play edition did not reject the external update API");
                File forbiddenPack = new File(getTargetContext().getFilesDir(), "packs/" + first.id + "/external-test");
                forbiddenPack.mkdirs();
                try (FileOutputStream output = new FileOutputStream(new File(forbiddenPack, "index.html"))) {
                    output.write("Untrusted external editor".getBytes(StandardCharsets.UTF_8));
                }
                manager.prefs.edit().putString(first.id + ".directory", "external-test").putString(first.id + ".version", "99.0.0").commit();
                require(manager.installedRoot(first) == null, "Play edition accepted an external engine pack");
                require(manager.installedVersion(first).equals(first.bundledVersion), "External version replaced the packaged editor");
                denied = false;
                try { manager.install(first, new JSONObject(), this::log); }
                catch (IllegalStateException expected) { denied = expected.getMessage().contains("Google Play"); }
                require(denied, "Play edition reached the external installer");
                manager.prefs.edit().remove(first.id + ".available").remove(first.id + ".directory").remove(first.id + ".version").commit();
                PackArchive.deleteTree(forbiddenPack);
                runOnMainSync(() -> {
                    require(label(activity.getWindow().getDecorView(), "Privacy policy") != null, "Missing privacy policy");
                    require(label(activity.getWindow().getDecorView(), "Support") != null, "Missing publisher support");
                    require(label(activity.getWindow().getDecorView(), "Check GitHub updates") == null, "Play edition shows GitHub updater");
                });
                runOnMainSync(() -> label(activity.getWindow().getDecorView(), "Privacy policy").performClick());
                waitForIdleSync(); SystemClock.sleep(300);
                android.view.accessibility.AccessibilityNodeInfo policy = getUiAutomation().getRootInActiveWindow();
                require(policy != null && accessibilityText(policy).contains("Your documents"), "Privacy policy did not open offline");
                screenshot("privacy-policy");
                sendKeyDownUpSync(android.view.KeyEvent.KEYCODE_BACK);
                checks++; log("PLAY PASS external updater disabled; privacy and support available offline");
                shell("cmd connectivity airplane-mode disable");
                require(engineFailures.isEmpty(), "Engine startup failures: " + engineFailures);
                result.putString("stream", "Passed " + checks + " Google Play edition integration checks.\n");
                finish(Activity.RESULT_OK, result);
                return;
            }
            shell("cmd connectivity airplane-mode disable");
            SystemClock.sleep(4000);
            SuiteManager.App app = manager.apps.get(manager.apps.size() - 1);
            File previous = new File(getTargetContext().getFilesDir(), "packs/" + app.id + "/smoke-previous");
            previous.mkdirs();
            try (FileOutputStream output = new FileOutputStream(new File(previous, "index.html"))) { output.write("previous".getBytes(StandardCharsets.UTF_8)); }
            manager.prefs.edit().putString(app.id + ".directory", previous.getName()).putString(app.id + ".version", "0.0.0").commit();
            manager.checkUpdates(this::log);
            JSONObject candidate = manager.available(app);
            require(candidate != null, "Real GitHub check did not find the simulated app update");
            manager.install(app, candidate, this::log);
            require(manager.installedVersion(app).equals(candidate.getString("version")), "Updated version was not activated");
            require(manager.installedRoot(app) != null && new File(manager.installedRoot(app), "index.html").isFile(), "No installed package");
            checks++; log("UPDATE PASS GitHub check → download → checksum → activation");
            try { open(app); ready(app.id); screenshot("updated-" + app.id); }
            catch (AssertionError error) { engineFailures.add(error.toString()); }
            finally { home(); }
            File active = manager.installedRoot(app);
            JSONObject bad = new JSONObject(candidate.toString()).put("sha256", "0".repeat(64));
            boolean rejected = false;
            try { manager.install(app, bad, this::log); } catch (Exception expected) { rejected = true; }
            require(rejected && active.equals(manager.installedRoot(app)), "Bad update replaced the working version");
            checks++; log("INTEGRITY PASS bad checksum retains the installed version");
            manager.useBundled(app);
            require(manager.installedRoot(app) == null && manager.installedVersion(app).equals(app.bundledVersion), "Bundled fallback failed");
            checks++; log("FALLBACK PASS bundled version restored");
            manager.prefs.edit().putBoolean("autoCheck", true).commit();
            shell("cmd connectivity airplane-mode enable");
            home();
            try { open(app); ready(app.id); checks++; log("OFFLINE PASS bundled fallback launches with network disabled"); }
            catch (AssertionError error) { engineFailures.add(error.toString()); }
            finally { home(); }
            shell("cmd connectivity airplane-mode disable");
            require(engineFailures.isEmpty(), "Engine startup failures: " + engineFailures);
            result.putString("stream", "Passed " + checks + " Android integration checks. Screenshots in files/smoke-results.\n");
            finish(Activity.RESULT_OK, result);
        } catch (Throwable error) {
            log("FAIL " + error);
            result.putString("stream", "FAILED after " + checks + " checks: " + error + "\n");
            result.putString("error", error.toString());
            finish(Activity.RESULT_CANCELED, result);
        }
    }

    private String accessibilityText(android.view.accessibility.AccessibilityNodeInfo node) {
        StringBuilder text = new StringBuilder(String.valueOf(node.getText()));
        for (int i = 0; i < node.getChildCount(); i++) {
            android.view.accessibility.AccessibilityNodeInfo child = node.getChild(i);
            if (child != null) text.append('\n').append(accessibilityText(child));
        }
        return text.toString();
    }

    /** Canvas menus have no Android text nodes. Compare their rendered dropdown region,
     * excluding the hovered title, to catch a menu that opens then closes in the same tap.
     * Coordinates are CSS points in the pinned PdfCraft 0.17 tablet layout. */
    private void menuRegression(SuiteManager manager) throws Exception {
        SuiteManager.App pdf = manager.apps.stream().filter(app -> app.id.equals("pdfcraft")).findFirst().orElseThrow();
        open(pdf); ready(pdf.id); SystemClock.sleep(1000);
        View[] editor = new View[1]; int[] location = new int[2];
        runOnMainSync(() -> {
            editor[0] = geckoView(activity.getWindow().getDecorView());
            require(editor[0] != null, "No Gecko editor"); editor[0].getLocationOnScreen(location);
        });
        float scale = getTargetContext().getResources().getDisplayMetrics().density;
        require(editor[0].getWidth() / scale >= 1200, "Menu regression requires the 2560 × 1600 tablet AVD");
        String[] names = {"File", "Edit", "View", "Sign", "Window", "Help"};
        int[] x = {31, 74, 121, 170, 228, 287};
        for (int index = 0; index < names.length; index++) {
            Bitmap base = getUiAutomation().takeScreenshot();
            tap(location[0] + x[index] * scale, location[1] + 64 * scale, 80);
            SystemClock.sleep(700);
            Bitmap opened = getUiAutomation().takeScreenshot();
            int changed = menuDifference(base, opened, location, scale);
            require(changed > 700, names[index] + " menu did not remain open after touch release: " + changed);
            screenshot("menu-" + names[index].toLowerCase());
            // A second press on the same title must close once, rather than reopening.
            tap(location[0] + x[index] * scale, location[1] + 64 * scale, 80);
            SystemClock.sleep(500);
            Bitmap closed = getUiAutomation().takeScreenshot();
            require(menuDifference(base, closed, location, scale) < changed / 3, names[index] + " menu did not close on second tap");
            base.recycle(); opened.recycle(); closed.recycle();
            checks++; log("MENU PASS " + names[index] + " opens on touch, persists after release, closes on second tap");
        }
    }

    private View geckoView(View view) {
        if (view instanceof org.mozilla.geckoview.GeckoView) return view;
        if (view instanceof ViewGroup) for (int i = 0; i < ((ViewGroup) view).getChildCount(); i++) {
            View found = geckoView(((ViewGroup) view).getChildAt(i)); if (found != null) return found;
        }
        return null;
    }

    private void tap(float x, float y, long duration) {
        long down = SystemClock.uptimeMillis();
        android.view.MotionEvent event = android.view.MotionEvent.obtain(down, down, android.view.MotionEvent.ACTION_DOWN, x, y, 0);
        event.setSource(android.view.InputDevice.SOURCE_TOUCHSCREEN); sendPointerSync(event); event.recycle();
        SystemClock.sleep(duration);
        event = android.view.MotionEvent.obtain(down, SystemClock.uptimeMillis(), android.view.MotionEvent.ACTION_UP, x, y, 0);
        event.setSource(android.view.InputDevice.SOURCE_TOUCHSCREEN); sendPointerSync(event); event.recycle();
    }

    private int menuDifference(Bitmap before, Bitmap after, int[] origin, float scale) {
        require(before != null && after != null, "No menu screenshots");
        int changed = 0;
        for (int y = origin[1] + (int) (80 * scale); y < Math.min(before.getHeight(), origin[1] + (int) (520 * scale)); y += 2) {
            for (int x = origin[0]; x < Math.min(before.getWidth(), origin[0] + (int) (560 * scale)); x += 2) {
                int a = before.getPixel(x, y), b = after.getPixel(x, y);
                if (Math.abs(android.graphics.Color.red(a) - android.graphics.Color.red(b))
                    + Math.abs(android.graphics.Color.green(a) - android.graphics.Color.green(b))
                    + Math.abs(android.graphics.Color.blue(a) - android.graphics.Color.blue(b)) > 70) changed++;
            }
        }
        return changed;
    }

    private void shell(String command) throws Exception {
        try (ParcelFileDescriptor descriptor = getUiAutomation().executeShellCommand(command);
             InputStream input = new ParcelFileDescriptor.AutoCloseInputStream(descriptor)) {
            byte[] bytes = new byte[1024]; while (input.read(bytes) != -1) { }
        }
        SystemClock.sleep(500);
    }

    private TextView label(View view, String text) {
        if (view instanceof TextView && ((TextView) view).getText().toString().equals(text)) return (TextView) view;
        if (view instanceof ViewGroup) {
            ViewGroup group = (ViewGroup) view;
            for (int i = 0; i < group.getChildCount(); i++) {
                TextView found = label(group.getChildAt(i), text); if (found != null) return found;
            }
        }
        return null;
    }

    private void open(SuiteManager.App app) {
        runOnMainSync(() -> {
            TextView name = label(activity.getWindow().getDecorView(), app.name);
            require(name != null, "Missing suite card: " + app.name);
            TextView open = label((View) name.getParent(), "Open");
            require(open instanceof Button && open.isEnabled(), "Missing enabled Open button: " + app.name);
            open.performClick();
        });
    }

    private void home() {
        runOnMainSync(() -> {
            try {
                Method method = MainActivity.class.getDeclaredMethod("showHome"); method.setAccessible(true); method.invoke(activity);
            } catch (Exception error) { throw new RuntimeException(error); }
        });
    }

    private WebView web(View view) {
        if (view instanceof WebView) return (WebView) view;
        if (view instanceof ViewGroup) for (int i = 0; i < ((ViewGroup) view).getChildCount(); i++) {
            WebView found = web(((ViewGroup) view).getChildAt(i)); if (found != null) return found;
        }
        return null;
    }

    private void ready(String id) throws Exception {
        if (!getTargetContext().getSharedPreferences("suite", 0).getBoolean("systemEngine", false)) {
            long end = SystemClock.uptimeMillis() + 60000;
            while (SystemClock.uptimeMillis() < end) {
                JSONObject state = activity.engineState;
                if (state != null) {
                    require(state.optString("origin").equals("http://" + id + ".localhost:" + LoopbackAssets.PORT), "Gecko app origin is not isolated");
                    if (state.optBoolean("ready")) return;
                    if (state.optBoolean("error")) throw new AssertionError(id + ": " + state.optString("text"));
                }
                SystemClock.sleep(500);
            }
            throw new AssertionError(id + " did not start in Gecko: " + activity.engineState);
        }
        long deadline = SystemClock.uptimeMillis() + 60000;
        String last = "";
        while (SystemClock.uptimeMillis() < deadline) {
            CountDownLatch latch = new CountDownLatch(1);
            String[] answer = new String[1];
            runOnMainSync(() -> {
                WebView web = web(activity.getWindow().getDecorView());
                require(web != null, "Missing editor WebView");
                require(web.getUrl().startsWith("https://" + id + ".artcraft.invalid/"), "App origin is not isolated");
                web.evaluateJavascript("JSON.stringify({bridge:typeof window.showSaveFilePicker==='function' && !!window.AndroidDocuments,ready:!!document.querySelector('input:not([type=file]),textarea') && !!document.querySelector('canvas') && ![...document.querySelectorAll('[id$=\"_loading\"],#loading')].some(el=>getComputedStyle(el).display!=='none'&&el.getClientRects().length>0),text:document.body?.innerText.slice(0,800),resources:performance.getEntriesByType('resource').map(r=>({name:r.name,duration:r.duration,size:r.decodedBodySize}))})", value -> { answer[0] = value; latch.countDown(); });
            });
            require(latch.await(5, TimeUnit.SECONDS), "WebView did not answer readiness probe");
            last = answer[0];
            if (last != null && !last.equals("null")) {
                JSONObject state = new JSONObject(new JSONArray("[" + last + "]").getString(0));
                if (state.optBoolean("ready") && state.optBoolean("bridge")) return;
                String body = state.optString("text").toLowerCase();
                if (body.contains("failed to start:") || body.contains("failed to load:")) throw new AssertionError(id + ": " + state.optString("text"));
            }
            SystemClock.sleep(750);
        }
        screenshot("failed-" + id);
        throw new AssertionError(id + " did not finish starting: " + last);
    }

    private void screenshot(String name) throws Exception {
        SystemClock.sleep(200);
        Bitmap bitmap = getUiAutomation().takeScreenshot();
        require(bitmap != null, "No screenshot");
        try (FileOutputStream output = new FileOutputStream(new File(results, name + ".png"))) { bitmap.compress(Bitmap.CompressFormat.PNG, 100, output); }
        bitmap.recycle();
    }

    private String glLimit() throws Exception {
        if (!getTargetContext().getSharedPreferences("suite", 0).getBoolean("systemEngine", false)) return String.valueOf(activity.engineState);
        String[] result = new String[1]; CountDownLatch latch = new CountDownLatch(1);
        runOnMainSync(() -> web(activity.getWindow().getDecorView()).evaluateJavascript("(()=>{const gl=document.querySelector('canvas')?.getContext('webgl2');return gl?{maxTexture:gl.getParameter(gl.MAX_TEXTURE_SIZE),maxRenderbuffer:gl.getParameter(gl.MAX_RENDERBUFFER_SIZE),version:gl.getParameter(gl.VERSION)}:null})()", value -> { result[0]=value; latch.countDown(); }));
        latch.await(5, TimeUnit.SECONDS); return result[0];
    }
}
