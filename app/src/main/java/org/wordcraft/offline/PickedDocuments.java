package org.wordcraft.offline;

import android.content.Context;
import android.database.Cursor;
import android.net.Uri;
import android.provider.OpenableColumns;
import android.webkit.MimeTypeMap;
import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.InterruptedIOException;
import java.nio.charset.StandardCharsets;
import java.util.UUID;
import java.util.function.BooleanSupplier;

/** Read selected document URIs through their grants, not provider-specific filesystem paths. */
final class PickedDocuments {
    private final Context context;
    private final File directory;

    PickedDocuments(Context context) {
        this.context = context.getApplicationContext();
        directory = new File(root(context), UUID.randomUUID().toString());
    }

    static File root(Context context) { return new File(context.getCacheDir(), "picked-documents"); }

    Uri[] copy(Uri[] selected, BooleanSupplier cancelled) throws IOException {
        File batch = new File(directory, UUID.randomUUID().toString());
        Uri[] local = new Uri[selected.length];
        try {
            for (int index = 0; index < selected.length; index++) {
                if (cancelled.getAsBoolean()) throw new InterruptedIOException("Selection closed");
                // Separate folders preserve duplicate display names in multi-file selections.
                File folder = new File(batch, Integer.toString(index));
                if (!folder.mkdirs()) throw new IOException("Cannot prepare selected document");
                File target = new File(folder, displayName(selected[index]));
                try (InputStream source = context.getContentResolver().openInputStream(selected[index]);
                     FileOutputStream output = new FileOutputStream(target)) {
                    if (source == null) throw new IOException("Selected document is unavailable");
                    byte[] buffer = new byte[65536];
                    int count;
                    while ((count = source.read(buffer)) != -1) {
                        if (cancelled.getAsBoolean()) throw new InterruptedIOException("Selection closed");
                        output.write(buffer, 0, count);
                    }
                }
                local[index] = Uri.fromFile(target);
            }
            return local;
        } catch (IOException | RuntimeException error) {
            delete(batch);
            throw error;
        }
    }

    private String displayName(Uri uri) {
        String name = null;
        try (Cursor cursor = context.getContentResolver().query(uri,
                new String[]{OpenableColumns.DISPLAY_NAME}, null, null, null)) {
            if (cursor != null && cursor.moveToFirst()) {
                int column = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME);
                if (column >= 0) name = cursor.getString(column);
            }
        } catch (RuntimeException unavailable) { /* Metadata is optional; the read grant is not. */ }
        if (name == null || name.trim().isEmpty()) name = uri.getLastPathSegment();
        if (name == null) name = "Document";
        name = name.replaceAll("[/\\\\\\p{Cntrl}]", "_");
        if (name.equals(".") || name.equals("..") || name.isEmpty()) name = "Document";
        String extension = "";
        int dot = name.lastIndexOf('.');
        if (dot >= 0 && name.substring(dot).matches("\\.[A-Za-z0-9]{1,16}")) extension = name.substring(dot);
        if (name.getBytes(StandardCharsets.UTF_8).length > 240) name = "Document" + extension;
        if (!name.contains(".")) {
            try {
                String suffix = MimeTypeMap.getSingleton().getExtensionFromMimeType(context.getContentResolver().getType(uri));
                if (suffix != null && suffix.matches("[A-Za-z0-9]+")) name += "." + suffix;
            } catch (RuntimeException unavailable) { }
        }
        return name;
    }

    void clear() { delete(directory); }

    static void delete(File file) {
        File[] children = file.listFiles();
        if (children != null) for (File child : children) delete(child);
        file.delete();
    }
}
