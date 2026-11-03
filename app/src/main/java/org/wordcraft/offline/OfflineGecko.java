package org.wordcraft.offline;

import android.app.Activity;
import android.content.Intent;
import android.net.Uri;
import android.webkit.ValueCallback;
import org.json.JSONObject;
import org.mozilla.geckoview.AllowOrDeny;
import org.mozilla.geckoview.GeckoResult;
import org.mozilla.geckoview.GeckoRuntime;
import org.mozilla.geckoview.GeckoRuntimeSettings;
import org.mozilla.geckoview.GeckoSession;
import org.mozilla.geckoview.GeckoView;
import org.mozilla.geckoview.WebExtension;
import org.mozilla.geckoview.WebRequestError;

/** Bundled browser runtime: no Google Play Services or system WebView dependency. */
final class OfflineGecko {
    interface Bridge { void request(JSONObject data, MainActivity.Reply reply); }
    interface Picker { void open(ValueCallback<Uri[]> callback, boolean multiple); }
    private static GeckoRuntime runtime;
    private final GeckoSession session = new GeckoSession();
    final GeckoView view;
    private boolean closed;

    OfflineGecko(Activity activity, SuiteManager suite, SuiteManager.App app, Bridge bridge, Picker picker, Runnable crashed) throws Exception {
        LoopbackAssets.get(suite);
        if (runtime == null) {
            runtime = GeckoRuntime.create(activity.getApplicationContext(), new GeckoRuntimeSettings.Builder()
                .javaScriptEnabled(true).consoleOutput(BuildConfig.DEBUG).remoteDebuggingEnabled(BuildConfig.DEBUG).build());
        }
        String origin = LoopbackAssets.origin(app);
        view = new GeckoView(activity);
        session.setNavigationDelegate(new GeckoSession.NavigationDelegate() {
            @Override public GeckoResult<String> onLoadError(GeckoSession source, String uri, WebRequestError error) {
                try {
                    bridge.request(new JSONObject().put("id", 0).put("action", "health").put("state", new JSONObject()
                        .put("origin", origin).put("ready", false).put("error", true)
                        .put("text", "Local editor could not load: " + error.code)), ignored -> {});
                } catch (Exception ignored) { }
                return null;
            }
            @Override public GeckoResult<AllowOrDeny> onLoadRequest(GeckoSession source, LoadRequest request) {
                Uri destination = Uri.parse(request.uri);
                Uri publisher = Uri.parse(BuildConfig.PUBLISHER_WEBSITE);
                if (request.hasUserGesture && "https".equals(destination.getScheme())
                    && publisher.getHost() != null && publisher.getHost().equalsIgnoreCase(destination.getHost())) {
                    try { activity.startActivity(new Intent(Intent.ACTION_VIEW, destination)); }
                    catch (Exception unavailable) { android.widget.Toast.makeText(activity, BuildConfig.PUBLISHER_WEBSITE, android.widget.Toast.LENGTH_LONG).show(); }
                    return GeckoResult.fromValue(AllowOrDeny.DENY);
                }
                return GeckoResult.fromValue(request.uri.startsWith(origin + "/") ? AllowOrDeny.ALLOW : AllowOrDeny.DENY);
            }
            @Override public GeckoResult<AllowOrDeny> onSubframeLoadRequest(GeckoSession source, LoadRequest request) {
                return GeckoResult.fromValue(request.uri.startsWith(origin + "/") || request.uri.startsWith("blob:" + origin + "/")
                    ? AllowOrDeny.ALLOW : AllowOrDeny.DENY);
            }
        });
        session.setPromptDelegate(new GeckoSession.PromptDelegate() {
            @Override public GeckoResult<PromptResponse> onFilePrompt(GeckoSession source, FilePrompt prompt) {
                GeckoResult<PromptResponse> result = new GeckoResult<>();
                if (prompt.type == FilePrompt.Type.FOLDER) { result.complete(prompt.dismiss()); return result; }
                picker.open(uris -> result.complete(uris == null ? prompt.dismiss() : prompt.confirm(activity.getApplicationContext(), uris)),
                    prompt.type == FilePrompt.Type.MULTIPLE);
                return result;
            }
        });
        session.setContentDelegate(new GeckoSession.ContentDelegate() {
            @Override public void onCrash(GeckoSession source) { if (!closed) crashed.run(); }
        });
        session.open(runtime);
        view.setSession(session);
        runtime.getWebExtensionController().ensureBuiltIn("resource://android/assets/gecko-extension/", "offline-bridge@mtouaa.local")
            .accept(extension -> activity.runOnUiThread(() -> {
                if (closed) return;
                session.getWebExtensionController().setMessageDelegate(extension, new WebExtension.MessageDelegate() {
                    @Override public GeckoResult<Object> onMessage(String nativeApp, Object message, WebExtension.MessageSender sender) {
                        GeckoResult<Object> result = new GeckoResult<>();
                        if (closed || sender.session != session || !sender.isTopLevel() || !sender.url.startsWith(origin + "/") || !(message instanceof JSONObject)) {
                            result.completeExceptionally(new SecurityException("Untrusted editor message"));
                            return result;
                        }
                        bridge.request((JSONObject) message, result::complete);
                        return result;
                    }
                }, "AndroidDocuments");
                session.loadUri(origin + "/index.html?webgl&nosw");
            }), error -> activity.runOnUiThread(() -> {
                if (BuildConfig.DEBUG) android.util.Log.e("SuiteGecko", "Could not install built-in bridge", error);
                if (!closed) crashed.run();
            }));
    }

    void close() {
        closed = true;
        view.releaseSession();
        session.close();
    }
}
