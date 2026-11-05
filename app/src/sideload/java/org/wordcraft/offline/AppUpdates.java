package org.wordcraft.offline;

import android.app.Activity;
import android.widget.LinearLayout;
import java.util.function.BooleanSupplier;

/** Historical prototype retains its separate engine updater. */
final class AppUpdates extends UpdateControls {
    AppUpdates(Activity activity, BooleanSupplier safe) { super(activity, safe); }
    @Override void addTo(LinearLayout parent) { }
    @Override void clicked() { }
}
