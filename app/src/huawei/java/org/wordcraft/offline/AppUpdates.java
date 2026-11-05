package org.wordcraft.offline;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.Intent;
import android.net.Uri;
import android.provider.Settings;
import androidx.core.content.FileProvider;
import java.io.File;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.function.BooleanSupplier;
import org.json.JSONArray;
import org.json.JSONObject;

/** Signed Mtouaa APK updates, independent of Google Play Services. */
final class AppUpdates extends UpdateControls {
    static final int PERMISSION = 61002;
    private final ExecutorService worker = Executors.newSingleThreadExecutor();
    private UpdateRelease release;
    private File ready;
    private AlertDialog installPrompt;
    private boolean busy, awaitingPermission;
    AppUpdates(Activity activity, BooleanSupplier safe) { super(activity, safe); }
    @Override void clicked() {
        if (busy || !readyToInstall()) return;
        if (BuildConfig.DEBUG) { state("Install the signed Huawei edition to receive release updates.", "Check for updates", true); return; }
        if (ready != null) { confirmInstall(); return; }
        if (release != null) { download(); return; }
        busy = true; state("Checking for a Mtouaa Studio release…", "Checking…", false);
        worker.execute(() -> {
            try {
                String repo = BuildConfig.RELEASE_REPOSITORY;
                JSONObject latest = new JSONObject(new String(ReleaseDownload.small("https://api.github.com/repos/" + repo + "/releases/latest", 256 * 1024), StandardCharsets.UTF_8));
                String tag = latest.getString("tag_name");
                if (latest.optBoolean("draft") || latest.optBoolean("prerelease") || !tag.matches("v[0-9]+\\.[0-9]+\\.[0-9]+")) throw new SecurityException("Invalid published release");
                String manifest = "https://github.com/" + repo + "/releases/download/" + tag + "/mtouaa-update.json";
                JSONArray assets = latest.getJSONArray("assets"); boolean found = false;
                for (int i = 0; i < assets.length(); i++) if (assets.getJSONObject(i).getString("name").equals("mtouaa-update.json") && assets.getJSONObject(i).getString("browser_download_url").equals(manifest)) found = true;
                if (!found) throw new java.io.IOException("No published Mtouaa update descriptor");
                UpdateRelease candidate = UpdateRelease.read(ReleaseDownload.small(manifest, 256 * 1024), ApkVerifier.publicKey(activity), activity.getPackageName(), ApkVerifier.code(ApkVerifier.info(activity, null)), repo);
                File directory = new File(activity.getCacheDir(), "updates");
                if (!directory.isDirectory() && !directory.mkdirs()) throw new java.io.IOException("No cache storage");
                File cached = candidate == null ? null : new File(directory, "update-" + candidate.code + "-" + candidate.sha256 + ".apk");
                boolean verified = false;
                if (cached != null && cached.isFile()) { try { ApkVerifier.verify(activity, cached, candidate); verified = true; } catch (Exception invalid) { cached.delete(); } }
                final boolean complete = verified;
                activity.runOnUiThread(() -> {
                    if (closed) return;
                    busy = false; release = candidate; ready = complete ? cached : null;
                    state(candidate == null ? "Mtouaa Studio is up to date." : "Mtouaa Studio " + candidate.version + (complete ? " is ready to install." : " is available."), complete ? "Install update" : candidate == null ? "Check for updates" : "Download update", true);
                });
            } catch (Exception error) { failed(error); }
        });
    }
    private void download() {
        busy = true; UpdateRelease selected = release;
        state("Downloading Mtouaa Studio " + selected.version + "…", "Downloading…", false);
        worker.execute(() -> {
            File target = new File(new File(activity.getCacheDir(), "updates"), "update-" + selected.code + "-" + selected.sha256 + ".apk");
            try {
                ReleaseDownload.apk(selected, target, () -> closed, value -> state("Downloading update: " + value + "%", "Downloading…", false));
                ApkVerifier.verify(activity, target, selected);
                activity.runOnUiThread(() -> { if (!closed) { busy = false; ready = target; state("The signed update is ready. Save your work before installing.", "Install update", true); } });
            } catch (Exception error) { target.delete(); failed(error); }
        });
    }
    private void failed(Exception error) {
        if (BuildConfig.DEBUG) android.util.Log.e("MtouaaUpdate", "Update check/download failed", error);
        activity.runOnUiThread(() -> {
            if (closed) return;
            busy = false;
            state(error instanceof SecurityException ? "The update could not be verified. Please try again later." : "Updates are unavailable right now. Check your connection and try again.", release == null ? "Check for updates" : "Retry download", true);
        });
    }
    private void confirmInstall() {
        if (!readyToInstall()) return;
        if (installPrompt != null && installPrompt.isShowing()) return;
        installPrompt = new AlertDialog.Builder(activity).setTitle("Install Mtouaa Studio " + release.version + "?")
            .setMessage("Save and close your documents first. Android will ask you to confirm installation and may close the app.")
            .setNegativeButton("Later", null).setPositiveButton("Continue", (dialog, which) -> install()).show();
    }
    private void install() {
        if (!readyToInstall() || ready == null) return;
        if (!activity.getPackageManager().canRequestPackageInstalls()) {
            awaitingPermission = true;
            try { activity.startActivityForResult(new Intent(Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES, Uri.parse("package:" + activity.getPackageName())), PERMISSION); }
            catch (Exception unavailable) { awaitingPermission = false; state("Allow installation from Mtouaa Studio in Android settings, then try again.", "Install update", true); }
            return;
        }
        busy = true;
        File selected = ready; UpdateRelease selectedRelease = release;
        state("Verifying the signed update…", "Verifying…", false);
        worker.execute(() -> {
            try {
                // Hash large APKs off the main thread, including the final check.
                ApkVerifier.verify(activity, selected, selectedRelease);
                activity.runOnUiThread(() -> {
                    if (closed) return;
                    busy = false;
                    state("The signed update is ready to install.", "Install update", true);
                    if (!readyToInstall()) return;
                    try {
                        Uri apk = FileProvider.getUriForFile(activity, activity.getPackageName() + ".updates", selected);
                        Intent intent = new Intent(Intent.ACTION_VIEW).setDataAndType(apk, "application/vnd.android.package-archive").addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
                        activity.startActivity(intent);
                    } catch (Exception error) { failed(error); }
                });
            } catch (Exception error) { selected.delete(); activity.runOnUiThread(() -> ready = null); failed(error); }
        });
    }
    @Override void resumed() {
        if (awaitingPermission) {
            awaitingPermission = false;
            if (activity.getPackageManager().canRequestPackageInstalls() && readyToInstall()) confirmInstall();
            else state("Installation permission was not enabled. You can try again later.", "Install update", true);
        }
    }
    @Override boolean activityResult(int request, int result, Intent data) { return request == PERMISSION; }
    @Override void close() {
        if (installPrompt != null) installPrompt.dismiss();
        super.close(); worker.shutdownNow();
    }
}
