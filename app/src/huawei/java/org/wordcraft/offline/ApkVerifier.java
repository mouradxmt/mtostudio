package org.wordcraft.offline;

import android.content.Context;
import android.content.pm.PackageInfo;
import android.content.pm.PackageManager;
import android.content.pm.Signature;
import android.os.Build;
import java.io.ByteArrayInputStream;
import java.io.File;
import java.io.FileInputStream;
import java.security.MessageDigest;
import java.security.PublicKey;
import java.security.cert.CertificateFactory;
import java.util.Arrays;

final class ApkVerifier {
    static PackageInfo info(Context context, File archive) throws Exception {
        int flags = Build.VERSION.SDK_INT >= 28 ? PackageManager.GET_SIGNING_CERTIFICATES : PackageManager.GET_SIGNATURES;
        PackageInfo info = archive == null ? context.getPackageManager().getPackageInfo(context.getPackageName(), flags)
            : context.getPackageManager().getPackageArchiveInfo(archive.getPath(), flags);
        if (info == null) throw new SecurityException("Invalid APK");
        return info;
    }
    @SuppressWarnings("deprecation") static byte[] signer(PackageInfo info) {
        Signature[] signatures = Build.VERSION.SDK_INT >= 28 && info.signingInfo != null ? info.signingInfo.getApkContentsSigners() : info.signatures;
        if (signatures == null || signatures.length != 1) throw new SecurityException("Expected one APK signer");
        return signatures[0].toByteArray();
    }
    @SuppressWarnings("deprecation") static long code(PackageInfo info) { return Build.VERSION.SDK_INT >= 28 ? info.getLongVersionCode() : info.versionCode; }
    static PublicKey publicKey(Context context) throws Exception {
        return CertificateFactory.getInstance("X.509").generateCertificate(new ByteArrayInputStream(signer(info(context, null)))).getPublicKey();
    }
    static String hash(File file) throws Exception {
        MessageDigest digest = MessageDigest.getInstance("SHA-256"); byte[] bytes = new byte[65536]; int read;
        try (FileInputStream input = new FileInputStream(file)) { while ((read = input.read(bytes)) != -1) digest.update(bytes, 0, read); }
        StringBuilder hex = new StringBuilder(); for (byte value : digest.digest()) hex.append(String.format(java.util.Locale.ROOT, "%02x", value & 255)); return hex.toString();
    }
    static void verify(Context context, File apk, UpdateRelease release) throws Exception {
        if (apk.length() != release.size || !hash(apk).equals(release.sha256)) throw new SecurityException("APK size or digest mismatch");
        PackageInfo installed = info(context, null), candidate = info(context, apk);
        if (!context.getPackageName().equals(candidate.packageName) || code(candidate) != release.code || code(candidate) <= code(installed)
                || !release.version.equals(candidate.versionName) || !Arrays.equals(signer(installed), signer(candidate))) throw new SecurityException("APK identity, version or signer mismatch");
        // Android's package installer performs its own mandatory signature/integrity verification.
    }
}
