package org.wordcraft.offline;

import android.app.Instrumentation;
import android.os.Bundle;
import android.os.ParcelFileDescriptor;
import android.util.Base64;
import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.security.KeyPair;
import java.security.KeyPairGenerator;
import java.security.Signature;
import org.json.JSONObject;

/** Exercise actual Android crypto, PackageManager parsing and provider boundaries. */
public final class UpdateChannelChecks {
    private static int count;
    private interface Check { void run() throws Exception; }
    private static void require(boolean ok, String message) { if (!ok) throw new AssertionError(message); count++; }
    private static void reject(Check check) throws Exception {
        try { check.run(); } catch (SecurityException expected) { count++; return; }
        throw new AssertionError("Unsafe update was accepted");
    }
    private static byte[] signed(JSONObject payload, KeyPair keys) throws Exception {
        byte[] bytes = payload.toString().getBytes(StandardCharsets.UTF_8);
        Signature signature = Signature.getInstance("SHA256withRSA"); signature.initSign(keys.getPrivate()); signature.update(bytes);
        return new JSONObject().put("format", 1).put("algorithm", "SHA256withRSA")
            .put("payload", Base64.encodeToString(bytes, Base64.NO_WRAP))
            .put("signature", Base64.encodeToString(signature.sign(), Base64.NO_WRAP)).toString().getBytes(StandardCharsets.UTF_8);
    }
    public static int run(Instrumentation test, Bundle arguments) throws Exception {
        count = 0;
        KeyPairGenerator generator = KeyPairGenerator.getInstance("RSA"); generator.initialize(2048); KeyPair keys = generator.generateKeyPair();
        String pkg = test.getTargetContext().getPackageName(), repo = BuildConfig.RELEASE_REPOSITORY;
        long installed = ApkVerifier.code(ApkVerifier.info(test.getTargetContext(), null));
        JSONObject payload = new JSONObject().put("format", 1).put("channel", "huawei").put("applicationId", pkg)
            .put("versionCode", installed+1).put("versionName", "0.6.1").put("apk", new JSONObject()
                .put("url", "https://github.com/"+repo+"/releases/download/v0.6.1/Mtouaa-Studio-0.6.1-huawei.apk")
                .put("size", 100).put("sha256", "a".repeat(64)));
        byte[] valid = signed(payload, keys);
        require(UpdateRelease.read(valid, keys.getPublic(), pkg, installed, repo).code == installed+1, "New signed release rejected");
        require(UpdateRelease.read(valid, keys.getPublic(), pkg, installed+1, repo) == null, "Same version offered");
        require(UpdateRelease.read(valid, keys.getPublic(), pkg, installed+2, repo) == null, "Downgrade offered");
        reject(() -> UpdateRelease.read(valid, generator.generateKeyPair().getPublic(), pkg, installed, repo));
        reject(() -> UpdateRelease.read(valid, keys.getPublic(), "another.app", installed, repo));
        JSONObject tampered = new JSONObject(new String(valid, StandardCharsets.UTF_8));
        tampered.put("payload", Base64.encodeToString(payload.put("versionCode", installed+99).toString().getBytes(StandardCharsets.UTF_8), Base64.NO_WRAP));
        reject(() -> UpdateRelease.read(tampered.toString().getBytes(StandardCharsets.UTF_8), keys.getPublic(), pkg, installed, repo));
        payload.put("versionCode", installed+1).put("channel", "play");
        reject(() -> UpdateRelease.read(signed(payload, keys), keys.getPublic(), pkg, installed, repo));
        payload.put("channel", "huawei"); payload.getJSONObject("apk").put("url", "https://github.com/attacker/repo/app.apk");
        reject(() -> UpdateRelease.read(signed(payload, keys), keys.getPublic(), pkg, installed, repo));
        payload.getJSONObject("apk").put("url", "https://github.com/"+repo+"/releases/download/v0.6.1/Mtouaa-Studio-0.6.1-huawei.apk").put("size", UpdateRelease.MAX_APK_BYTES+1);
        reject(() -> UpdateRelease.read(signed(payload, keys), keys.getPublic(), pkg, installed, repo));
        for (String url : new String[]{"http://github.com/file", "https://github.com.evil.test/file", "https://user@github.com/file", "https://github.com:444/file", "file:///data/app.apk"})
            require(!UpdateRelease.trustedTransport(new URL(url)), "Unsafe URL accepted: "+url);
        require(UpdateRelease.trustedTransport(new URL("https://release-assets.githubusercontent.com/file")), "GitHub CDN rejected");
        require(ApkVerifier.publicKey(test.getTargetContext()).getAlgorithm().equals("RSA"), "Installed signing identity unavailable");
        require(test.getTargetContext().getPackageManager().getPackageInfo(pkg, android.content.pm.PackageManager.GET_PERMISSIONS).requestedPermissions != null, "No permissions");
        android.content.pm.ProviderInfo provider = test.getTargetContext().getPackageManager().resolveContentProvider(pkg+".updates", 0);
        require(provider != null && !provider.exported && provider.grantUriPermissions, "APK provider is publicly exported or missing");
        if (arguments.getString("fixtureApk") != null) {
            File directory = new File(test.getTargetContext().getCacheDir(), "updates"); directory.mkdirs();
            File fixture = new File(directory, "test-fixture.apk");
            String path = arguments.getString("fixtureApk");
            if (!path.matches("/data/local/tmp/[a-zA-Z0-9._-]+\\.apk")) throw new IllegalArgumentException("Invalid fixture path");
            try (ParcelFileDescriptor descriptor = test.getUiAutomation().executeShellCommand("cat "+path);
                 InputStream input = new ParcelFileDescriptor.AutoCloseInputStream(descriptor); FileOutputStream output = new FileOutputStream(fixture)) { byte[] bytes = new byte[65536]; int n; while ((n=input.read(bytes))!=-1) output.write(bytes,0,n); }
            payload.getJSONObject("apk").put("size", fixture.length()).put("sha256", ApkVerifier.hash(fixture));
            UpdateRelease release = UpdateRelease.read(signed(payload, keys), keys.getPublic(), pkg, installed, repo);
            ApkVerifier.verify(test.getTargetContext(), fixture, release); count++;
            if ("true".equals(arguments.getString("installer"))) {
                android.app.Activity activity = test.startActivitySync(new android.content.Intent(test.getTargetContext(), MainActivity.class).addFlags(android.content.Intent.FLAG_ACTIVITY_NEW_TASK));
                require(activity.getPackageManager().canRequestPackageInstalls(), "Allow test app installation permission first");
                java.util.concurrent.atomic.AtomicBoolean safe = new java.util.concurrent.atomic.AtomicBoolean(false);
                AppUpdates[] controls = new AppUpdates[1];
                test.runOnMainSync(() -> controls[0] = new AppUpdates(activity, safe::get));
                for (String name : new String[]{"release", "ready"}) {
                    java.lang.reflect.Field field = AppUpdates.class.getDeclaredField(name); field.setAccessible(true); field.set(controls[0], name.equals("ready") ? fixture : release);
                }
                java.lang.reflect.Field field = AppUpdates.class.getDeclaredField("installPrompt"); field.setAccessible(true);
                test.runOnMainSync(() -> controls[0].clicked());
                require(field.get(controls[0]) == null, "Installer offered while editor active");
                test.runOnMainSync(() -> { safe.set(true); controls[0].clicked(); }); test.waitForIdleSync();
                android.app.AlertDialog prompt = (android.app.AlertDialog)field.get(controls[0]);
                test.runOnMainSync(() -> prompt.getButton(android.app.AlertDialog.BUTTON_NEGATIVE).performClick()); test.waitForIdleSync();
                test.runOnMainSync(() -> controls[0].clicked()); test.waitForIdleSync();
                final android.app.AlertDialog confirmed = (android.app.AlertDialog)field.get(controls[0]);
                test.runOnMainSync(() -> confirmed.getButton(android.app.AlertDialog.BUTTON_POSITIVE).performClick());
                boolean installer = false;
                for (int i=0; i<50; i++) {
                    android.os.SystemClock.sleep(200);
                    android.view.accessibility.AccessibilityNodeInfo root = test.getUiAutomation().getRootInActiveWindow();
                    if (root != null && root.getPackageName() != null && root.getPackageName().toString().contains("packageinstaller")) { installer = true; break; }
                }
                require(installer, "Verified APK did not reach Android's package installer");
                test.sendKeyDownUpSync(android.view.KeyEvent.KEYCODE_BACK); test.waitForIdleSync();
                require(ApkVerifier.code(ApkVerifier.info(test.getTargetContext(), null)) == installed, "Cancelling installer changed app version");
                test.runOnMainSync(() -> controls[0].close());
            }
            try (java.io.RandomAccessFile corrupt = new java.io.RandomAccessFile(fixture, "rw")) { corrupt.seek(0); corrupt.write(0); }
            reject(() -> ApkVerifier.verify(test.getTargetContext(), fixture, release));
            fixture.delete();
        }
        android.util.Log.i("SuiteSmoke", "HUAWEI UPDATE PASS "+count+" signature, downgrade, origin, APK and provider checks");
        return count;
    }
}
