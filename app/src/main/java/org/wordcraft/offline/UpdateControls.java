package org.wordcraft.offline;

import android.app.Activity;
import android.content.Intent;
import android.graphics.Color;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;
import java.util.function.BooleanSupplier;

/** Native home-screen controls; no update is installed while an editor or save is active. */
abstract class UpdateControls {
    final Activity activity;
    final BooleanSupplier safe;
    volatile boolean closed;
    private TextView label;
    private Button button;
    private String message = "Check for a new Mtouaa Studio release when you are online.";
    private String action = "Check for updates";
    private boolean enabled = true;

    UpdateControls(Activity activity, BooleanSupplier safe) { this.activity = activity; this.safe = safe; }
    void addTo(LinearLayout parent) {
        label = new TextView(activity); label.setTextSize(14); label.setTextColor(Color.rgb(71, 85, 105));
        parent.addView(label);
        button = new Button(activity); button.setAllCaps(false); button.setOnClickListener(view -> clicked());
        parent.addView(button); redraw();
    }
    final void state(String text, String caption, boolean active) {
        activity.runOnUiThread(() -> {
            if (closed || activity.isDestroyed()) return;
            message = text; action = caption; enabled = active; redraw();
        });
    }
    private void redraw() {
        if (label != null) label.setText(message);
        if (button != null) { button.setText(action); button.setEnabled(enabled); }
    }
    final boolean readyToInstall() {
        if (safe.getAsBoolean()) return true;
        Toast.makeText(activity, "Finish saving and return to Apps before installing an update.", Toast.LENGTH_LONG).show();
        return false;
    }
    abstract void clicked();
    void resumed() { }
    boolean activityResult(int request, int result, Intent data) { return false; }
    void close() { closed = true; label = null; button = null; }
}
