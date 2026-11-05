package org.wordcraft.offline;

import android.util.Base64;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.security.PublicKey;
import java.security.Signature;
import org.json.JSONObject;

/** A release descriptor authenticated by the installed APK's signing key. */
final class UpdateRelease {
    static final long MAX_APK_BYTES = 768L * 1024 * 1024;
    final long code, size;
    final String version, url, sha256;
    private UpdateRelease(long code, long size, String version, String url, String sha256) {
        this.code = code; this.size = size; this.version = version; this.url = url; this.sha256 = sha256;
    }
    static UpdateRelease read(byte[] envelopeBytes, PublicKey trustedKey, String packageName, long installedCode, String repository) throws Exception {
        if (envelopeBytes.length > 256 * 1024) throw new SecurityException("Oversized release descriptor");
        JSONObject envelope = new JSONObject(new String(envelopeBytes, StandardCharsets.UTF_8));
        if (envelope.getInt("format") != 1 || !envelope.getString("algorithm").equals("SHA256withRSA")) throw new SecurityException("Unknown release signature format");
        byte[] payload = Base64.decode(envelope.getString("payload"), Base64.DEFAULT);
        byte[] signature = Base64.decode(envelope.getString("signature"), Base64.DEFAULT);
        Signature verifier = Signature.getInstance("SHA256withRSA"); verifier.initVerify(trustedKey); verifier.update(payload);
        if (!verifier.verify(signature)) throw new SecurityException("Release signature mismatch");
        JSONObject release = new JSONObject(new String(payload, StandardCharsets.UTF_8));
        if (release.getInt("format") != 1 || !release.getString("channel").equals("huawei") || !release.getString("applicationId").equals(packageName)) throw new SecurityException("Wrong release channel or application");
        long code = release.getLong("versionCode"); String version = release.getString("versionName");
        JSONObject apk = release.getJSONObject("apk"); long size = apk.getLong("size"); String hash = apk.getString("sha256"), url = apk.getString("url");
        if (code <= 0 || code > 2100000000L || !version.matches("[0-9]+\\.[0-9]+\\.[0-9]+") || size <= 0 || size > MAX_APK_BYTES || !hash.matches("[a-f0-9]{64}")) throw new SecurityException("Invalid release fields");
        String expected = "https://github.com/" + repository + "/releases/download/v" + version + "/Mtouaa-Studio-" + version + "-huawei.apk";
        if (!url.equals(expected)) throw new SecurityException("Unexpected APK location");
        return code > installedCode ? new UpdateRelease(code, size, version, url, hash) : null;
    }
    static boolean trustedTransport(URL url) {
        String host = url.getHost();
        return url.getProtocol().equals("https") && url.getUserInfo() == null && (url.getPort() == -1 || url.getPort() == 443)
            && (host.equals("api.github.com") || host.equals("github.com") || host.equals("release-assets.githubusercontent.com")
                || host.equals("objects.githubusercontent.com") || host.equals("github-releases.githubusercontent.com"));
    }
}
