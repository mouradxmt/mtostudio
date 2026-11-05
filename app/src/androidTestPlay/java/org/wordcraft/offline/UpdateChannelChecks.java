package org.wordcraft.offline;

import android.app.Activity;
import android.app.AlertDialog;
import android.app.Instrumentation;
import android.content.Intent;
import android.os.Bundle;
import android.os.SystemClock;
import android.widget.Button;
import android.widget.LinearLayout;
import com.google.android.play.core.appupdate.testing.FakeAppUpdateManager;
import java.util.concurrent.atomic.AtomicBoolean;

/** Exercise the production controller against Google's official fake service. */
public final class UpdateChannelChecks {
    private static void require(boolean ok, String message) { if (!ok) throw new AssertionError(message); }
    public static int run(Instrumentation test, Bundle arguments) throws Exception {
        Activity activity = test.startActivitySync(new Intent(test.getTargetContext(), MainActivity.class).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK));
        FakeAppUpdateManager manager = new FakeAppUpdateManager(activity);
        AtomicBoolean safe = new AtomicBoolean(true);
        AppUpdates[] updates = new AppUpdates[1]; LinearLayout[] layout = new LinearLayout[1];
        test.runOnMainSync(() -> {
            updates[0] = new AppUpdates(activity, safe::get, manager);
            layout[0] = new LinearLayout(activity); layout[0].setOrientation(LinearLayout.VERTICAL);
            activity.setContentView(layout[0]); updates[0].addTo(layout[0]);
            manager.setUpdateAvailable(BuildConfig.VERSION_CODE+1); updates[0].clicked();
        });
        test.waitForIdleSync(); SystemClock.sleep(200);
        test.runOnMainSync(() -> require(((Button)layout[0].getChildAt(1)).getText().toString().equals("Download update"), "Available update not shown"));
        test.runOnMainSync(() -> { safe.set(false); updates[0].clicked(); require(!manager.isConfirmationDialogVisible(), "Update started with unsaved editor state"); safe.set(true); updates[0].clicked(); });
        test.waitForIdleSync(); SystemClock.sleep(200);
        require(manager.isConfirmationDialogVisible(), "Flexible update consent not requested");
        test.runOnMainSync(() -> { manager.userAcceptsUpdate(); manager.downloadStarts(); manager.setTotalBytesToDownload(100); manager.setBytesDownloaded(50); });
        test.waitForIdleSync();
        test.runOnMainSync(() -> require(!((Button)layout[0].getChildAt(1)).isEnabled(), "Duplicate downloads allowed"));
        test.runOnMainSync(() -> manager.downloadCompletes()); test.waitForIdleSync();
        test.runOnMainSync(() -> require(((Button)layout[0].getChildAt(1)).getText().toString().equals("Restart to update"), "Downloaded update not offered"));
        require(!manager.isInstallSplashScreenVisible(), "Update restarted without consent");
        test.runOnMainSync(() -> { safe.set(false); updates[0].clicked(); });
        require(!manager.isInstallSplashScreenVisible(), "Update installed while editor active");
        // Use the same native confirmation as the real controller, then reject it.
        test.runOnMainSync(() -> { safe.set(true); updates[0].clicked(); }); test.waitForIdleSync();
        java.lang.reflect.Field promptField = AppUpdates.class.getDeclaredField("restartPrompt"); promptField.setAccessible(true);
        AlertDialog cancelled = (AlertDialog) promptField.get(updates[0]);
        test.runOnMainSync(() -> cancelled.getButton(AlertDialog.BUTTON_NEGATIVE).performClick()); test.waitForIdleSync();
        require(!manager.isInstallSplashScreenVisible(), "Cancelling restart installed update");
        test.runOnMainSync(() -> updates[0].clicked()); test.waitForIdleSync();
        AlertDialog confirmed = (AlertDialog) promptField.get(updates[0]);
        test.runOnMainSync(() -> confirmed.getButton(AlertDialog.BUTTON_POSITIVE).performClick());
        test.waitForIdleSync(); SystemClock.sleep(300);
        require(manager.isInstallSplashScreenVisible(), "Explicit restart did not complete the update");
        test.runOnMainSync(() -> manager.installCompletes());
        test.runOnMainSync(() -> updates[0].close());
        android.util.Log.i("SuiteSmoke", "PLAY UPDATE PASS 9 availability, flexible consent, progress, save gates and confirmed/cancelled restart checks");
        return 9;
    }
}
