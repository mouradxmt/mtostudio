package org.wordcraft.offline;

import android.content.ContentProvider;
import android.content.ContentValues;
import android.database.Cursor;
import android.database.MatrixCursor;
import android.net.Uri;
import android.os.ParcelFileDescriptor;
import android.provider.OpenableColumns;
import java.io.File;
import java.io.FileNotFoundException;
import java.io.FileOutputStream;
import java.io.IOException;

/** Synthetic provider deliberately has no filesystem/_data column. Test APK only. */
public final class ImportFixtureProvider extends ContentProvider {
    static byte[] bytes(boolean second) {
        byte[] data = new byte[131079];
        for (int i = 0; i < data.length; i++) data[i] = (byte) (i * 37 + (second ? 11 : 3));
        return data;
    }
    @Override public boolean onCreate() { return true; }
    @Override public String getType(Uri uri) { return "application/pdf"; }
    @Override public Cursor query(Uri uri, String[] projection, String selection, String[] args, String order) {
        if ("nameless".equals(uri.getLastPathSegment())) {
            MatrixCursor cursor = new MatrixCursor(new String[]{OpenableColumns.SIZE});
            cursor.addRow(new Object[]{bytes(false).length}); return cursor;
        }
        MatrixCursor cursor = new MatrixCursor(new String[]{OpenableColumns.SIZE, OpenableColumns.DISPLAY_NAME});
        String name = uri.getQueryParameter("name");
        cursor.addRow(new Object[]{bytes(false).length, name == null ? "Résumé document.pdf" : name});
        return cursor;
    }
    @Override public ParcelFileDescriptor openFile(Uri uri, String mode) throws FileNotFoundException {
        if (!"r".equals(mode) || "missing".equals(uri.getLastPathSegment())) throw new FileNotFoundException("Fixture unavailable");
        try {
            File file = File.createTempFile("selected-fixture-", ".bin", getContext().getCacheDir());
            try (FileOutputStream output = new FileOutputStream(file)) { output.write(bytes("two".equals(uri.getLastPathSegment()))); }
            return ParcelFileDescriptor.open(file, ParcelFileDescriptor.MODE_READ_ONLY);
        } catch (IOException error) { throw new FileNotFoundException(error.getMessage()); }
    }
    @Override public Uri insert(Uri uri, ContentValues values) { throw new UnsupportedOperationException(); }
    @Override public int delete(Uri uri, String selection, String[] args) { throw new UnsupportedOperationException(); }
    @Override public int update(Uri uri, ContentValues values, String selection, String[] args) { throw new UnsupportedOperationException(); }
}
