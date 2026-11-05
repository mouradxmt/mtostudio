package org.wordcraft.offline;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.function.BooleanSupplier;
import java.util.function.IntConsumer;

final class ReleaseDownload {
    static HttpURLConnection connect(String address) throws Exception {
        URL url = new URL(address);
        for (int redirect = 0; redirect < 6; redirect++) {
            if (!UpdateRelease.trustedTransport(url)) throw new SecurityException("Untrusted release host");
            HttpURLConnection connection = (HttpURLConnection) url.openConnection();
            connection.setInstanceFollowRedirects(false); connection.setConnectTimeout(15000); connection.setReadTimeout(20000);
            connection.setRequestProperty("User-Agent", "Mtouaa-Studio-Android");
            int status = connection.getResponseCode();
            if (status == 200) return connection;
            String location = connection.getHeaderField("Location"); connection.disconnect();
            if (status < 300 || status >= 400 || location == null) throw new java.io.IOException("Release service unavailable (" + status + ")");
            url = new URL(url, location);
        }
        throw new SecurityException("Too many release redirects");
    }
    static byte[] small(String url, int limit) throws Exception {
        HttpURLConnection connection = connect(url);
        try (InputStream input = connection.getInputStream(); ByteArrayOutputStream output = new ByteArrayOutputStream()) {
            byte[] bytes = new byte[8192]; int read;
            while ((read = input.read(bytes)) != -1) { if (output.size() + read > limit) throw new SecurityException("Oversized release response"); output.write(bytes, 0, read); }
            return output.toByteArray();
        } finally { connection.disconnect(); }
    }
    static void apk(UpdateRelease release, File target, BooleanSupplier cancelled, IntConsumer progress) throws Exception {
        HttpURLConnection connection = connect(release.url); File partial = new File(target.getParentFile(), "download.partial");
        try (InputStream input = connection.getInputStream(); FileOutputStream output = new FileOutputStream(partial)) {
            byte[] bytes = new byte[65536]; long total = 0; int count, previous = -1;
            while ((count = input.read(bytes)) != -1) {
                if (cancelled.getAsBoolean() || Thread.currentThread().isInterrupted()) throw new java.io.InterruptedIOException("Update closed");
                total += count; if (total > release.size) throw new SecurityException("APK exceeds declared size");
                output.write(bytes, 0, count);
                int percent = (int) (100 * total / release.size); if (percent != previous) { progress.accept(percent); previous = percent; }
            }
            if (total != release.size) throw new SecurityException("Incomplete APK");
            output.getFD().sync();
        } catch (Exception error) { partial.delete(); throw error; }
        finally { connection.disconnect(); }
        if (!partial.renameTo(target)) { partial.delete(); throw new java.io.IOException("Could not retain update"); }
    }
}
