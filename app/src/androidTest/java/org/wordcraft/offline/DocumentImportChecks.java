package org.wordcraft.offline;

import android.app.Instrumentation;
import android.content.pm.PackageInfo;
import android.content.pm.PackageManager;
import android.content.pm.ProviderInfo;
import android.net.Uri;
import java.io.File;
import java.io.InputStream;
import java.lang.reflect.Method;
import java.util.Arrays;
import org.mozilla.geckoview.GeckoSession;

/** Exercises real provider streams and the pinned Gecko file-prompt resolver. */
final class DocumentImportChecks {
    private static void require(boolean condition, String message) { if (!condition) throw new AssertionError(message); }
    private static int files(File root) {
        if (root.isFile()) return 1;
        int total = 0;
        File[] children = root.listFiles();
        if (children != null) for (File child : children) total += files(child);
        return total;
    }
    private static byte[] read(Instrumentation runner, Uri uri) throws Exception {
        try (InputStream input = runner.getTargetContext().getContentResolver().openInputStream(uri)) {
            require(input != null, "Missing input stream"); return input.readAllBytes();
        }
    }
    static int run(Instrumentation runner) throws Exception {
        PackageInfo pkg = runner.getContext().getPackageManager().getPackageInfo(runner.getContext().getPackageName(), PackageManager.GET_PROVIDERS);
        String authority = null;
        for (ProviderInfo provider : pkg.providers) if (provider.name.equals(ImportFixtureProvider.class.getName())) authority = provider.authority;
        require(authority != null, "Test provider missing");
        Uri first = Uri.parse("content://" + authority + "/one"), second = Uri.parse("content://" + authority + "/two");
        PickedDocuments documents = new PickedDocuments(runner.getTargetContext());
        int checks = 0;
        try {
            Uri[] picked = documents.copy(new Uri[]{first}, () -> false);
            require(Arrays.equals(read(runner, picked[0]), ImportFixtureProvider.bytes(false)), "Provider bytes changed");
            require(new File(picked[0].getPath()).getName().equals("Résumé document.pdf"), "Display name/extension changed");
            checks++;
            Method resolver = GeckoSession.PromptDelegate.FilePrompt.class.getDeclaredMethod("getFile", android.content.Context.class, Uri.class);
            resolver.setAccessible(true);
            String path = (String) resolver.invoke(null, runner.getTargetContext(), picked[0]);
            require(path != null && new File(path).canRead(), "Gecko cannot resolve the staged file"); checks++;
            Uri[] many = documents.copy(new Uri[]{first, second}, () -> false);
            require(!many[0].equals(many[1]), "Duplicate display names overwrite each other");
            require(Arrays.equals(read(runner, many[0]), ImportFixtureProvider.bytes(false)) && Arrays.equals(read(runner, many[1]), ImportFixtureProvider.bytes(true)), "Multi-selection bytes changed"); checks++;
            Uri hostile = first.buildUpon().appendQueryParameter("name", "../../outside.docx").build();
            Uri safe = documents.copy(new Uri[]{hostile}, () -> false)[0];
            require(!new File(safe.getPath()).getName().contains("/") && new File(safe.getPath()).getCanonicalPath().startsWith(PickedDocuments.root(runner.getTargetContext()).getCanonicalPath() + "/"), "Unsafe provider name escaped cache");
            require(safe.getLastPathSegment().endsWith(".docx"), "Safe extension lost"); checks++;
            int retained = files(PickedDocuments.root(runner.getTargetContext()));
            int[] calls = {0}; boolean cancelled = false;
            try { documents.copy(new Uri[]{first}, () -> calls[0]++ > 1); }
            catch (java.io.InterruptedIOException expected) { cancelled = true; }
            require(cancelled && new File(picked[0].getPath()).isFile(), "Cancellation lost a prior successful selection"); checks++;
            require(files(PickedDocuments.root(runner.getTargetContext())) == retained, "Cancelled copy left partial files");
            boolean failed = false;
            try { documents.copy(new Uri[]{first, Uri.parse("content://" + authority + "/missing")}, () -> false); }
            catch (java.io.IOException expected) { failed = true; }
            require(failed, "Unreadable selection did not fail");
            require(files(PickedDocuments.root(runner.getTargetContext())) == retained, "Failed multi-selection left partial files");
            Uri nameless = documents.copy(new Uri[]{Uri.parse("content://" + authority + "/nameless")}, () -> false)[0];
            require(nameless.getLastPathSegment().endsWith(".pdf"), "Missing-metadata MIME fallback lost extension"); checks++;
            documents.clear();
            require(!new File(picked[0].getPath()).exists(), "Session cache retained");
            require(Arrays.equals(read(runner, first), ImportFixtureProvider.bytes(false)), "Cleanup changed the original provider document"); checks++;
            return checks;
        } finally { documents.clear(); }
    }
}
