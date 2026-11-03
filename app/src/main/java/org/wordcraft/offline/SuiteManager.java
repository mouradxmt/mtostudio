package org.wordcraft.offline;

import android.content.Context;
import android.content.SharedPreferences;
import org.json.JSONArray;
import org.json.JSONObject;
import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

final class SuiteManager {
    static final class App {
        final String id, name, description, repo, bundledVersion, alias;
        App(JSONObject data) throws Exception {
            id = data.getString("id"); name = data.getString("name"); description = data.getString("description");
            repo = data.getString("repo"); bundledVersion = data.getString("version");
            alias = data.optString("alias", name.replaceAll("[^A-Za-z0-9]", ""));
            if (!id.matches("[a-z][a-z0-9-]+") || !repo.equals("storytold/" + id)) throw new IllegalArgumentException("Invalid app catalog");
        }
        String origin() { return "https://" + id + ".artcraft.invalid"; }
    }
    interface Progress { void show(String text); }
    final List<App> apps = new ArrayList<>();
    private final Context context;
    final SharedPreferences prefs;

    SuiteManager(Context context) throws Exception {
        this.context = context;
        prefs = context.getSharedPreferences("suite", Context.MODE_PRIVATE);
        try (InputStream input = context.getAssets().open("suite/catalog.json")) {
            JSONArray catalog = new JSONArray(new String(read(input, 1024 * 1024), StandardCharsets.UTF_8));
            for (int i = 0; i < catalog.length(); i++) apps.add(new App(catalog.getJSONObject(i)));
        }
    }

    String installedVersion(App app) {
        return installedRoot(app) != null ? prefs.getString(app.id + ".version", app.bundledVersion) : app.bundledVersion;
    }

    File installedRoot(App app) {
        if (!BuildConfig.EXTERNAL_UPDATES) return null;
        String directory = prefs.getString(app.id + ".directory", "");
        if (!directory.matches("[a-zA-Z0-9][a-zA-Z0-9._-]*")) return null;
        File folder = new File(new File(context.getFilesDir(), "packs/" + app.id), directory);
        return new File(folder, "index.html").isFile() ? folder : null;
    }

    InputStream open(App app, String path) throws Exception {
        if (path.startsWith("/") || path.contains("\\")) throw new IllegalArgumentException("Invalid asset path");
        for (String segment : path.split("/")) if (segment.equals("..") || segment.equals(".")) throw new IllegalArgumentException("Invalid asset path");
        if (path.equals("__native-save.js")) return context.getAssets().open("native-save.js");
        if (path.equals("__gecko-save.js")) {
            return new java.io.SequenceInputStream(context.getAssets().open("gecko-prelude.js"), context.getAssets().open("native-save.js"));
        }
        File folder = installedRoot(app);
        try {
            return folder == null ? context.getAssets().open("suite/" + app.id + "/" + path) : new FileInputStream(new File(folder, path));
        } catch (java.io.FileNotFoundException missing) {
            // PhotoCraft 0.19 puts app glue under app/ but its imported eframe snippets at root.
            // Serve the same bytes at the glue's relative URL; keep upstream JS/SRI untouched.
            if (!app.id.equals("photocraft") || !path.startsWith("app/snippets/")) throw missing;
            String alias = path.substring("app/".length());
            return folder == null ? context.getAssets().open("suite/" + app.id + "/" + alias) : new FileInputStream(new File(folder, alias));
        }
    }

    JSONObject available(App app) {
        if (!BuildConfig.EXTERNAL_UPDATES) return null;
        try {
            JSONObject candidate = new JSONObject(prefs.getString(app.id + ".available", "{}"));
            return PackArchive.newer(candidate.optString("version"), installedVersion(app)) ? candidate : null;
        } catch (Exception ignored) { return null; }
    }

    void checkUpdates(Progress progress) throws Exception {
        if (!BuildConfig.EXTERNAL_UPDATES) throw new IllegalStateException("This edition is updated through Google Play");
        int failures = 0, updates = 0;
        String lastError = "";
        for (App app : apps) {
            progress.show("Checking " + app.name + "…");
            try {
                HttpURLConnection connection = connect("https://api.github.com/repos/" + app.repo + "/releases/latest");
                JSONObject release;
                try (InputStream input = connection.getInputStream()) {
                    release = new JSONObject(new String(read(input, 4 * 1024 * 1024), StandardCharsets.UTF_8));
                } finally { connection.disconnect(); }
                if (release.optBoolean("draft") || release.optBoolean("prerelease")) continue;
                String version = release.getString("tag_name").replaceFirst("^v", "");
                JSONObject candidate = null;
                JSONArray assets = release.getJSONArray("assets");
                for (int i = 0; i < assets.length(); i++) {
                    JSONObject asset = assets.getJSONObject(i);
                    if (!asset.getString("name").equals(app.id + "-web-" + version + ".zip")) continue;
                    String digest = asset.optString("digest");
                    if (!digest.matches("sha256:[0-9a-f]{64}")) throw new IllegalStateException("GitHub has no SHA-256 for " + app.name);
                    String url = asset.getString("browser_download_url");
                    if (!url.startsWith("https://github.com/" + app.repo + "/releases/download/")) throw new IllegalStateException("Unexpected release source");
                    candidate = new JSONObject().put("version", version).put("url", url)
                        .put("sha256", digest.substring(7)).put("size", asset.getLong("size"));
                    break;
                }
                if (candidate != null) prefs.edit().putString(app.id + ".available", candidate.toString()).apply();
                else prefs.edit().remove(app.id + ".available").apply();
                if (available(app) != null) updates++;
            } catch (Exception error) { failures++; lastError = error.getMessage(); }
        }
        prefs.edit().putLong("lastCheck", System.currentTimeMillis()).apply();
        String result = updates == 0 ? "Installed apps are up to date." : updates + " app updates available.";
        if (failures > 0) result = "Checked " + (apps.size() - failures) + "/" + apps.size() + " apps. " + updates
            + " updates available. Could not reach all GitHub releases; installed apps still work offline. " + lastError;
        progress.show(result);
    }

    void install(App app, JSONObject candidate, Progress progress) throws Exception {
        if (!BuildConfig.EXTERNAL_UPDATES) throw new IllegalStateException("This edition is updated through Google Play");
        File previous = installedRoot(app);
        long expectedSize = candidate.getLong("size");
        if (expectedSize <= 0 || expectedSize > 512L * 1024 * 1024) throw new IllegalStateException("Package exceeds download limit");
        File download = new File(context.getCacheDir(), "suite-download-" + UUID.randomUUID() + ".zip");
        HttpURLConnection connection = connect(candidate.getString("url"));
        try {
            long total = 0, lastReport = 0;
            try (InputStream input = connection.getInputStream(); FileOutputStream output = new FileOutputStream(download)) {
                byte[] bytes = new byte[65536];
                int count;
                while ((count = input.read(bytes)) != -1) {
                    total += count;
                    if (total > expectedSize) throw new IllegalStateException("Download exceeds declared package size");
                    output.write(bytes, 0, count);
                    if (total - lastReport > 1024 * 1024) {
                        progress.show("Downloading " + app.name + ": " + (100 * total / expectedSize) + "%");
                        lastReport = total;
                    }
                }
                output.getFD().sync();
            }
            if (total != expectedSize) throw new IllegalStateException("Incomplete download");
            progress.show("Verifying and installing " + app.name + "…");
            String version = candidate.getString("version"), digest = candidate.getString("sha256");
            String directory = version + "-" + digest.substring(0, 12) + "-" + UUID.randomUUID();
            File installed = PackArchive.install(download, digest, new File(context.getFilesDir(), "packs/" + app.id), directory);
            if (!prefs.edit().putString(app.id + ".directory", installed.getName()).putString(app.id + ".version", version).commit()) {
                PackArchive.deleteTree(installed);
                throw new IllegalStateException("Could not activate package; previous version retained");
            }
            if (previous != null && !previous.equals(installed)) PackArchive.deleteTree(previous);
            progress.show(app.name + " " + version + " is installed and ready offline.");
        } finally { connection.disconnect(); download.delete(); }
    }

    void useBundled(App app) { prefs.edit().remove(app.id + ".directory").remove(app.id + ".version").apply(); }

    private static HttpURLConnection connect(String address) throws Exception {
        URL url = new URL(address);
        for (int redirects = 0; redirects < 6; redirects++) {
            String host = url.getHost();
            if (!url.getProtocol().equals("https") || !(host.equals("api.github.com") || host.equals("github.com")
                || host.equals("release-assets.githubusercontent.com") || host.equals("objects.githubusercontent.com")
                || host.equals("github-releases.githubusercontent.com"))) throw new IllegalStateException("Untrusted update host");
            HttpURLConnection connection = (HttpURLConnection) url.openConnection();
            connection.setConnectTimeout(15000); connection.setReadTimeout(45000);
            connection.setRequestProperty("User-Agent", "Mtouaa-Studio-Android/" + BuildConfig.VERSION_NAME);
            connection.setRequestProperty("Accept", "application/vnd.github+json");
            connection.setInstanceFollowRedirects(false);
            int status = connection.getResponseCode();
            if (status == 301 || status == 302 || status == 303 || status == 307 || status == 308) {
                String location = connection.getHeaderField("Location");
                connection.disconnect();
                url = new URL(url, location);
            } else if (status == 200) return connection;
            else {
                connection.disconnect();
                throw new IllegalStateException(status == 403 || status == 429 ? "GitHub rate limit reached; try later." : "GitHub returned HTTP " + status);
            }
        }
        throw new IllegalStateException("Too many update redirects");
    }

    static byte[] read(InputStream input, int limit) throws Exception {
        ByteArrayOutputStream output = new ByteArrayOutputStream();
        byte[] bytes = new byte[16384];
        int count;
        while ((count = input.read(bytes)) != -1) {
            if (output.size() + count > limit) throw new IllegalStateException("Response is too large");
            output.write(bytes, 0, count);
        }
        return output.toByteArray();
    }
}
