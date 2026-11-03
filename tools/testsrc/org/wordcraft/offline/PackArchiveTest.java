package org.wordcraft.offline;

import java.io.File;
import java.io.FileOutputStream;
import java.nio.file.Files;
import java.util.zip.ZipEntry;
import java.util.zip.ZipOutputStream;

public final class PackArchiveTest {
    private static int passed;
    private static void require(boolean value, String message) { if (!value) throw new AssertionError(message); }
    private static File archive(File parent, String... names) throws Exception {
        File archive = File.createTempFile("test-", ".zip", parent);
        try (ZipOutputStream zip = new ZipOutputStream(new FileOutputStream(archive))) {
            for (String name : names) {
                zip.putNextEntry(new ZipEntry(name)); zip.write(("contents of " + name).getBytes()); zip.closeEntry();
            }
        }
        return archive;
    }
    private static void reject(File archive, String digest, File parent, String name) throws Exception {
        boolean rejected = false;
        try { PackArchive.install(archive, digest, parent, name); }
        catch (Exception expected) { rejected = true; }
        require(rejected, "Unsafe package was accepted: " + name);
        require(!new File(parent, name).exists(), "Failed install became visible");
        File[] leftovers = parent.listFiles((dir, file) -> file.startsWith(".staging-"));
        require(leftovers == null || leftovers.length == 0, "Failed install left staging data");
        passed++;
    }

    public static void main(String[] args) throws Exception {
        File root = Files.createTempDirectory("artcraft-package-tests-").toFile();
        try {
            require(PackArchive.newer("0.20.0", "0.9.0"), "Numeric version comparison");
            require(!PackArchive.newer("0.9.0", "0.20.0"), "No downgrade");
            require(!PackArchive.newer("1.2.3", "1.2.3"), "No same-version update");
            require(!PackArchive.newer("1.3.0-rc1", "1.2.3"), "No prereleases");
            passed++;
            File old = new File(root, "previous"); old.mkdir();
            Files.writeString(new File(old, "index.html").toPath(), "previous still works");
            File good = archive(root, "app-1/index.html", "app-1/engine.wasm", "app-1/NOTICE");
            reject(good, "0".repeat(64), root, "bad-hash");
            File traversal = archive(root, "app/index.html", "app/../escape");
            reject(traversal, PackArchive.sha256(traversal), root, "traversal");
            File absolute = archive(root, "app/index.html", "/escape");
            reject(absolute, PackArchive.sha256(absolute), root, "absolute");
            File noIndex = archive(root, "app/file.txt");
            reject(noIndex, PackArchive.sha256(noIndex), root, "missing-index");
            File ambiguous = archive(root, "one/index.html", "two/index.html");
            reject(ambiguous, PackArchive.sha256(ambiguous), root, "ambiguous-index");
            File outside = archive(root, "app/index.html", "other/engine.wasm");
            reject(outside, PackArchive.sha256(outside), root, "outside-root");
            File installed = PackArchive.install(good, PackArchive.sha256(good), root, "new-version");
            require(new File(installed, "engine.wasm").isFile(), "Missing WASM");
            require(new File(installed, "NOTICE").isFile(), "Missing notices");
            require(Files.readString(new File(old, "index.html").toPath()).equals("previous still works"), "Previous version changed");
            passed++;
            for (String path : args) {
                File release = new File(path);
                File folder = PackArchive.install(release, PackArchive.sha256(release), root, "release-" + passed);
                require(new File(folder, "index.html").isFile(), "Release has no index");
                PackArchive.deleteTree(folder);
                passed++;
            }
            System.out.println("Passed " + passed + " archive/version checks (including " + args.length + " official packages).");
        } finally { PackArchive.deleteTree(root); }
    }
}
