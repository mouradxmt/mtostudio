package org.wordcraft.offline;

import android.app.Activity;
import android.content.ComponentName;
import android.content.Intent;
import android.content.pm.ShortcutInfo;
import android.content.pm.ShortcutManager;
import android.graphics.drawable.Icon;
import android.widget.Toast;

final class AppShortcuts {
    static String alias(SuiteManager.App app) { return app.alias; }

    static SuiteManager.App target(Intent intent, SuiteManager suite) {
        String requested = intent.getStringExtra("app_id");
        ComponentName component = intent.getComponent();
        String className = component == null ? "" : component.getClassName();
        for (SuiteManager.App app : suite.apps) {
            if (app.id.equals(requested) || className.equals("org.wordcraft.offline." + alias(app))) return app;
        }
        return null;
    }

    static void pin(Activity activity, SuiteManager.App app) {
        ShortcutManager manager = activity.getSystemService(ShortcutManager.class);
        if (manager == null || !manager.isRequestPinShortcutSupported()) {
            Toast.makeText(activity, "Open your app drawer and drag " + app.name + " onto the home screen.", Toast.LENGTH_LONG).show();
            return;
        }
        Intent intent = new Intent(Intent.ACTION_MAIN)
            .setComponent(new ComponentName(activity.getPackageName(), MainActivity.class.getPackage().getName() + "." + alias(app)))
            .addCategory(Intent.CATEGORY_LAUNCHER).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP);
        ShortcutInfo shortcut = new ShortcutInfo.Builder(activity, "editor-" + app.id)
            .setShortLabel(app.name).setLongLabel("Open " + app.name)
            .setActivity(new ComponentName(activity, MainActivity.class))
            .setIcon(Icon.createWithResource(activity, shortcutIcon(app.id))).setIntent(intent).build();
        boolean requested = manager.requestPinShortcut(shortcut, null);
        Toast.makeText(activity, requested ? "Confirm with your launcher to add " + app.name + "." : "Your launcher could not add this shortcut.", Toast.LENGTH_LONG).show();
    }

    private static int shortcutIcon(String id) {
        return switch (id) {
            case "photocraft" -> R.drawable.ic_photocraft;
            case "vectorcraft" -> R.drawable.ic_vectorcraft;
            case "filmcraft" -> R.drawable.ic_filmcraft;
            case "lightcraft" -> R.drawable.ic_lightcraft;
            case "pdfcraft" -> R.drawable.ic_pdfcraft;
            case "effectcraft" -> R.drawable.ic_effectcraft;
            case "designcraft" -> R.drawable.ic_designcraft;
            case "figcraft" -> R.drawable.ic_figcraft;
            case "texturecraft" -> R.drawable.ic_texturecraft;
            case "wordcraft" -> R.drawable.ic_wordcraft;
            case "soundcraft" -> R.drawable.ic_soundcraft;
            case "deckcraft" -> R.drawable.ic_deckcraft;
            case "cadcraft" -> R.drawable.ic_cadcraft;
            case "gridcraft" -> R.drawable.ic_gridcraft;
            case "craft-anything" -> R.drawable.ic_craft_anything;
            default -> R.drawable.ic_launcher;
        };
    }
}
