package org.wordcraft.offline;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.Enumeration;
import java.util.List;
import java.util.UUID;
import java.util.zip.ZipEntry;
import java.util.zip.ZipFile;

/** Extract a verified package in isolation. The caller activates it only after this succeeds. */
final class PackArchive {
    static final long MAX_EXPANDED = 2L * 1024 * 1024 * 1024;

    static String sha256(File file) throws Exception {
        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        try (InputStream input = new FileInputStream(file)) {
            byte[] bytes = new byte[65536];
            int count;
            while ((count = input.read(bytes)) != -1) digest.update(bytes, 0, count);
        }
        StringBuilder hex = new StringBuilder();
        for (byte b : digest.digest()) hex.append(String.format(java.util.Locale.ROOT, "%02x", b & 255));
        return hex.toString();
    }

    static File install(File archive, String expectedSha, File parent, String directory) throws Exception {
        if (!expectedSha.matches("[0-9a-f]{64}") || !sha256(archive).equals(expectedSha)) {
            throw new IOException("Package checksum did not match GitHub");
        }
        if (!directory.matches("[a-zA-Z0-9._-]+") || directory.startsWith(".")) throw new IOException("Invalid package version");
        if (!parent.isDirectory() && !parent.mkdirs()) throw new IOException("Cannot create package folder");
        File target = new File(parent, directory);
        if (target.exists()) throw new IOException("Package folder already exists");
        File staging = new File(parent, ".staging-" + UUID.randomUUID());
        if (!staging.mkdir()) throw new IOException("Cannot stage package");
        try (ZipFile zip = new ZipFile(archive)) {
            List<ZipEntry> entries = new ArrayList<>();
            String index = null;
            int depth = Integer.MAX_VALUE;
            boolean ambiguous = false;
            long declared = 0;
            Enumeration<? extends ZipEntry> enumeration = zip.entries();
            while (enumeration.hasMoreElements()) {
                ZipEntry entry = enumeration.nextElement();
                String name = entry.getName();
                if (name.startsWith("/") || name.contains("\\") || name.indexOf('\0') >= 0) throw new IOException("Unsafe package path");
                for (String segment : name.split("/")) if (segment.equals("..") || segment.equals(".")) throw new IOException("Unsafe package path");
                entries.add(entry);
                if (entries.size() > 20000) throw new IOException("Too many package files");
                declared += Math.max(0, entry.getSize());
                if (declared > MAX_EXPANDED) throw new IOException("Expanded package exceeds 2 GB");
                if (!entry.isDirectory() && (name.equals("index.html") || name.endsWith("/index.html"))) {
                    int candidateDepth = name.split("/").length;
                    if (candidateDepth < depth) { index = name; depth = candidateDepth; ambiguous = false; }
                    else if (candidateDepth == depth) ambiguous = true;
                }
            }
            if (index == null || ambiguous) throw new IOException("Package has no unique application index");
            String prefix = index.substring(0, index.length() - "index.html".length());
            long expanded = 0;
            byte[] bytes = new byte[65536];
            for (ZipEntry entry : entries) {
                if (entry.isDirectory()) continue;
                if (!entry.getName().startsWith(prefix)) throw new IOException("File is outside application root");
                File file = new File(staging, entry.getName().substring(prefix.length()));
                if (!file.getCanonicalPath().startsWith(staging.getCanonicalPath() + File.separator)) throw new IOException("Unsafe package path");
                File folder = file.getParentFile();
                if (!folder.isDirectory() && !folder.mkdirs()) throw new IOException("Cannot create package directory");
                if (file.exists()) throw new IOException("Duplicate package file");
                try (InputStream input = zip.getInputStream(entry); FileOutputStream output = new FileOutputStream(file)) {
                    int count;
                    while ((count = input.read(bytes)) != -1) {
                        expanded += count;
                        if (expanded > MAX_EXPANDED) throw new IOException("Expanded package exceeds 2 GB");
                        output.write(bytes, 0, count);
                    }
                    output.getFD().sync();
                }
            }
            if (!new File(staging, "index.html").isFile()) throw new IOException("Missing application index");
            if (!staging.renameTo(target)) throw new IOException("Cannot commit package");
            return target;
        } finally { deleteTree(staging); }
    }

    static void deleteTree(File file) {
        File[] children = file.listFiles();
        if (children != null) for (File child : children) deleteTree(child);
        if (file.exists()) file.delete();
    }

    static boolean newer(String candidate, String installed) {
        if (!candidate.matches("[0-9]+(\\.[0-9]+){2,3}") || !installed.matches("[0-9]+(\\.[0-9]+){2,3}")) return false;
        String[] left = candidate.split("\\."), right = installed.split("\\.");
        for (int i = 0; i < Math.max(left.length, right.length); i++) {
            java.math.BigInteger a = new java.math.BigInteger(i < left.length ? left[i] : "0");
            java.math.BigInteger b = new java.math.BigInteger(i < right.length ? right[i] : "0");
            int order = a.compareTo(b);
            if (order != 0) return order > 0;
        }
        return false;
    }
}
