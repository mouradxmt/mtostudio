import java.nio.file.*;
import java.util.*;
import java.io.*;
import java.security.*;

/** Sign public release metadata with the same key that signs the Huawei APK. Never prints keys. */
class SignUpdate {
    public static void main(String[] args) throws Exception {
        if (args.length != 3) throw new IllegalArgumentException("Usage: SignUpdate upload.properties payload.json signature.txt");
        Properties properties = new Properties();
        try (InputStream input = Files.newInputStream(Path.of(args[0]))) { properties.load(input); }
        char[] password = properties.getProperty("storePassword").toCharArray();
        KeyStore store = KeyStore.getInstance("PKCS12");
        try (InputStream input = Files.newInputStream(Path.of(properties.getProperty("storeFile")))) { store.load(input, password); }
        char[] keyPassword = properties.getProperty("keyPassword").toCharArray();
        PrivateKey key = (PrivateKey) store.getKey(properties.getProperty("keyAlias"), keyPassword);
        if (!key.getAlgorithm().equals("RSA")) throw new IllegalArgumentException("Update descriptor protocol requires the existing RSA signing key");
        Signature signer = Signature.getInstance("SHA256withRSA"); signer.initSign(key); signer.update(Files.readAllBytes(Path.of(args[1])));
        byte[] signature = signer.sign();
        Signature verifier = Signature.getInstance("SHA256withRSA"); verifier.initVerify(store.getCertificate(properties.getProperty("keyAlias"))); verifier.update(Files.readAllBytes(Path.of(args[1])));
        if (!verifier.verify(signature)) throw new SecurityException("Signing key does not match its certificate");
        Files.writeString(Path.of(args[2]), Base64.getEncoder().encodeToString(signature));
        Arrays.fill(password, '\0'); Arrays.fill(keyPassword, '\0');
    }
}
