package org.wordcraft.offline;

import android.net.Uri;
import java.io.BufferedInputStream;
import java.io.BufferedOutputStream;
import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.InetAddress;
import java.net.ServerSocket;
import java.net.Socket;
import java.net.URLConnection;
import java.nio.charset.StandardCharsets;
import java.util.Locale;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/** Serves only public editor package assets on loopback, never user documents. */
final class LoopbackAssets {
    static final int PORT = BuildConfig.LOCAL_PORT;
    private static LoopbackAssets instance;
    private final SuiteManager suite;
    private final ServerSocket socket;
    private final ExecutorService requests = Executors.newFixedThreadPool(6);

    static synchronized LoopbackAssets get(SuiteManager suite) throws Exception {
        if (instance == null) instance = new LoopbackAssets(suite);
        return instance;
    }
    static String origin(SuiteManager.App app) { return "http://" + app.id + ".localhost:" + PORT; }

    private LoopbackAssets(SuiteManager suite) throws Exception {
        this.suite = suite;
        socket = new ServerSocket(PORT, 32, InetAddress.getByName("127.0.0.1"));
        Thread accept = new Thread(() -> {
            while (!socket.isClosed()) {
                try { Socket client = socket.accept(); requests.execute(() -> serve(client)); }
                catch (Exception error) { if (BuildConfig.DEBUG) android.util.Log.e("SuiteLocal", "Local request failed", error); }
            }
        }, "suite-loopback");
        accept.setDaemon(true); accept.start();
    }

    private static String line(InputStream input) throws Exception {
        ByteArrayOutputStream output = new ByteArrayOutputStream();
        int b;
        while ((b = input.read()) != -1 && b != '\n') {
            if (output.size() > 8192) throw new IllegalArgumentException("HTTP line too large");
            if (b != '\r') output.write(b);
        }
        return output.toString("UTF-8");
    }

    private void serve(Socket client) {
        try (Socket connection = client;
             InputStream input = new BufferedInputStream(client.getInputStream());
             OutputStream output = new BufferedOutputStream(client.getOutputStream(), 65536)) {
            connection.setSoTimeout(10000);
            String[] request = line(input).split(" ");
            if (request.length != 3 || !(request[0].equals("GET") || request[0].equals("HEAD"))) { error(output); return; }
            String host = "";
            int headers = 0;
            for (String header = line(input); !header.isEmpty(); header = line(input)) {
                if (++headers > 100) throw new IllegalArgumentException("Too many HTTP headers");
                if (header.toLowerCase(Locale.ROOT).startsWith("host:")) host = header.substring(5).trim().toLowerCase(Locale.ROOT);
            }
            SuiteManager.App app = null;
            for (SuiteManager.App candidate : suite.apps) if (host.equals(candidate.id + ".localhost:" + PORT)) app = candidate;
            if (app == null || !request[1].startsWith("/")) { error(output); return; }
            String path = Uri.parse(request[1]).getPath();
            if (path == null) { error(output); return; }
            path = path.substring(1);
            if (path.isEmpty()) path = "index.html";
            InputStream asset;
            String mime;
            try {
                asset = suite.open(app, path.equals("__native-save.js") ? "__gecko-save.js" : path);
                if (path.equals("index.html")) {
                    String html;
                    try (InputStream source = asset) { html = new String(SuiteManager.read(source, 4 * 1024 * 1024), StandardCharsets.UTF_8); }
                    if (!html.contains("/__native-save.js")) html = html.replaceFirst("(?i)<head\\b[^>]*>", "$0<script src=\"/__native-save.js\"></script>");
                    asset = new ByteArrayInputStream(html.getBytes(StandardCharsets.UTF_8));
                }
                mime = path.endsWith(".wasm") ? "application/wasm" : path.endsWith(".js") ? "text/javascript"
                    : path.endsWith(".html") ? "text/html" : path.endsWith(".css") ? "text/css"
                    : path.endsWith(".json") ? "application/json" : URLConnection.guessContentTypeFromName(path);
            } catch (Exception missing) { error(output); return; }
            try (InputStream source = asset) {
                String response = "HTTP/1.1 200 OK\r\nContent-Type: " + (mime == null ? "application/octet-stream" : mime)
                    + "\r\nCache-Control: no-store\r\nX-Content-Type-Options: nosniff\r\nConnection: close\r\n\r\n";
                output.write(response.getBytes(StandardCharsets.US_ASCII));
                if (request[0].equals("GET")) {
                    byte[] bytes = new byte[65536]; int count;
                    while ((count = source.read(bytes)) != -1) output.write(bytes, 0, count);
                }
            }
        } catch (Exception error) { if (BuildConfig.DEBUG) android.util.Log.d("SuiteLocal", error.toString()); }
    }

    private static void error(OutputStream output) throws Exception {
        output.write("HTTP/1.1 404 Not Found\r\nContent-Length: 0\r\nConnection: close\r\n\r\n".getBytes(StandardCharsets.US_ASCII));
    }
}
