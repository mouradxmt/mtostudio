package org.wordcraft.offline;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.Intent;
import com.google.android.play.core.appupdate.AppUpdateInfo;
import com.google.android.play.core.appupdate.AppUpdateManager;
import com.google.android.play.core.appupdate.AppUpdateManagerFactory;
import com.google.android.play.core.appupdate.AppUpdateOptions;
import com.google.android.play.core.install.InstallStateUpdatedListener;
import com.google.android.play.core.install.model.AppUpdateType;
import com.google.android.play.core.install.model.InstallStatus;
import com.google.android.play.core.install.model.UpdateAvailability;
import java.util.function.BooleanSupplier;

/** Google Play controls distribution and installation in this edition. */
final class AppUpdates extends UpdateControls {
    static final int REQUEST = 61001;
    private final AppUpdateManager manager;
    private AppUpdateInfo available;
    private boolean downloaded, requested, busy;
    private AlertDialog restartPrompt;
    private final InstallStateUpdatedListener listener = update -> {
        if (update.installStatus() == InstallStatus.DOWNLOADED) {
            downloaded = true; busy = false;
            state("The update is ready. Save your work before restarting.", "Restart to update", true);
        } else if (update.installStatus() == InstallStatus.DOWNLOADING) {
            busy = true;
            long total = update.totalBytesToDownload();
            state(total > 0 ? "Downloading update: " + (100 * update.bytesDownloaded() / total) + "%" : "Downloading update…", "Downloading…", false);
        } else if (update.installStatus() == InstallStatus.FAILED || update.installStatus() == InstallStatus.CANCELED) {
            busy = false; state("The update did not finish. You can try again.", "Check for updates", true);
        }
    };
    AppUpdates(Activity activity, BooleanSupplier safe) { this(activity, safe, AppUpdateManagerFactory.create(activity)); }
    AppUpdates(Activity activity, BooleanSupplier safe, AppUpdateManager manager) {
        super(activity, safe); this.manager = manager; manager.registerListener(listener);
    }
    @Override void clicked() {
        if (!readyToInstall() || busy) return;
        if (downloaded) {
            if (restartPrompt != null && restartPrompt.isShowing()) return;
            restartPrompt = new AlertDialog.Builder(activity).setTitle("Restart to update?")
                .setMessage("Save and close your documents first. Google Play will restart Mtouaa Studio to finish the update.")
                .setNegativeButton("Later", null).setPositiveButton("Restart", (dialog, which) -> {
                    if (!readyToInstall()) return;
                    manager.completeUpdate().addOnFailureListener(error -> state("The update could not finish. Try again from Apps.", "Restart to update", true));
                }).show();
        } else if (available != null) {
            // AppUpdateInfo can be consumed once only. Always obtain a fresh instance.
            check(true);
        } else check(false);
    }
    private void check(boolean start) {
        busy = true; requested = true; state("Checking Google Play…", "Checking…", false);
        manager.getAppUpdateInfo().addOnSuccessListener(activity, info -> {
            if (closed) return;
            busy = false;
            if (info.installStatus() == InstallStatus.DOWNLOADED) {
                downloaded = true; state("The update is ready. Save your work before restarting.", "Restart to update", true);
            } else if (info.installStatus() == InstallStatus.DOWNLOADING || info.installStatus() == InstallStatus.PENDING) {
                busy = true; available = null;
                state("Google Play is downloading the update…", "Downloading…", false);
            } else if (info.updateAvailability() == UpdateAvailability.UPDATE_AVAILABLE && info.isUpdateTypeAllowed(AppUpdateType.FLEXIBLE)) {
                available = info;
                state("A new version is available from Google Play.", "Download update", true);
                if (start && readyToInstall()) {
                    available = null;
                    try {
                        busy = manager.startUpdateFlowForResult(info, activity, AppUpdateOptions.newBuilder(AppUpdateType.FLEXIBLE).build(), REQUEST);
                        if (!busy) unavailable();
                    } catch (Exception error) { unavailable(); }
                }
            } else {
                available = null; state("Google Play has no update available for this installation.", "Check for updates", true);
            }
        }).addOnFailureListener(activity, error -> unavailable());
    }
    private void unavailable() {
        if (closed) return;
        busy = false; available = null;
        state("Updates require a Google Play installation of Mtouaa Studio. You can continue using the installed editors.", "Check for updates", true);
    }
    @Override void resumed() {
        if (requested && !busy) check(false);
    }
    @Override boolean activityResult(int request, int result, Intent data) {
        if (request != REQUEST) return false;
        if (result != Activity.RESULT_OK) { busy = false; available = null; state("Update cancelled. You can check again later.", "Check for updates", true); }
        return true;
    }
    @Override void close() {
        manager.unregisterListener(listener);
        if (restartPrompt != null) restartPrompt.dismiss();
        super.close();
    }
}
