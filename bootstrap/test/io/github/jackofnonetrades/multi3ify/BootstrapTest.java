package io.github.jackofnonetrades.multi3ify;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Arrays;
import java.util.jar.Attributes;
import java.util.jar.JarEntry;
import java.util.jar.JarOutputStream;
import java.util.jar.Manifest;

public final class BootstrapTest {
    private static Path mod(Path path, String version, boolean lwjgl) throws Exception {
        Manifest manifest = new Manifest();
        manifest.getMainAttributes().put(Attributes.Name.MANIFEST_VERSION, "1.0");
        if (lwjgl) manifest.getMainAttributes().putValue("FMLCorePlugin", "me.eigenraven.lwjgl3ify.core.Lwjgl3ifyCoremod");
        try (JarOutputStream jar = new JarOutputStream(Files.newOutputStream(path), manifest)) {
            jar.putNextEntry(new JarEntry("version.txt"));
            jar.write(version.getBytes("UTF-8"));
            jar.closeEntry();
        }
        return path;
    }

    private static void check(boolean condition, String message) {
        if (!condition) throw new AssertionError(message);
    }

    public static void main(String[] args) throws Exception {
        Path root = java.nio.file.Paths.get(args[0]);
        Path game = root.resolve("instance with spaces");
        Path mods = Files.createDirectories(game.resolve("mods"));
        Path versioned = Files.createDirectories(mods.resolve("1.7.10"));
        Path manual = mod(mods.resolve("renamed-existing-mod.jar"), "old", true);
        Path duplicate = mod(versioned.resolve("lwjgl3ify-old.jar"), "older", true);
        Path unimixins = mod(mods.resolve("unimixins.jar"), "keep", false);
        byte[] unimixinsBefore = Files.readAllBytes(unimixins);
        Path first = mod(root.resolve("first.jar"), "first", true);
        String firstHash = Bootstrap.sha256(first);
        Bootstrap.install(game, first, firstHash);
        Path installed = mods.resolve(Bootstrap.MANAGED);
        check(Bootstrap.sha256(installed).equals(firstHash), "fresh install");
        check(!Files.exists(manual) && !Files.exists(duplicate), "manual duplicates backed up");
        try (java.util.stream.Stream<Path> backups = Files.list(game.resolve(".multi3ify-backups"))) {
            check(backups.count() == 2, "both original jars retained");
        }
        Bootstrap.install(game, installed, firstHash);
        check(Bootstrap.sha256(installed).equals(firstHash), "repeat install is idempotent");
        Path invalid = mod(root.resolve("invalid.jar"), "bad", true);
        try {
            Bootstrap.install(game, invalid, firstHash);
            throw new AssertionError("checksum mismatch must fail");
        } catch (java.io.IOException expected) {}
        check(Bootstrap.sha256(installed).equals(firstHash), "bad download preserves active version");
        Path impostor = mod(root.resolve("impostor.jar"), "not lwjgl3ify", false);
        try {
            Bootstrap.install(game, impostor, Bootstrap.sha256(impostor));
            throw new AssertionError("wrong mod must fail even with a matching hash");
        } catch (java.io.IOException expected) {}
        Path second = mod(root.resolve("second.tmp"), "second", true);
        String secondHash = Bootstrap.sha256(second);
        Bootstrap.install(game, second, secondHash);
        check(Bootstrap.sha256(installed).equals(secondHash), "upgrade");
        Path rollback = mod(root.resolve("rollback.jar"), "first", true);
        String rollbackHash = Bootstrap.sha256(rollback);
        Bootstrap.install(game, rollback, rollbackHash);
        check(Bootstrap.sha256(installed).equals(rollbackHash), "downgrade");
        check(Arrays.equals(unimixinsBefore, Files.readAllBytes(unimixins)), "unrelated mods untouched");

        // No network is needed when the selected mod is already installed.
        System.setProperty("multi3ify.modSha256", rollbackHash);
        System.setProperty("multi3ify.modUrl", "https://invalid.invalid/should-never-be-requested");
        System.setProperty("multi3ify.delegate", "com.gtnewhorizons.retrofuturabootstrap.TestDelegate");
        String[] forwarded = {"--gameDir", game.toString(), "--username", "test"};
        try { Bootstrap.main(forwarded); } catch (Throwable e) { throw new AssertionError(e); }
        check(Arrays.equals(forwarded, com.gtnewhorizons.retrofuturabootstrap.TestDelegate.arguments), "game arguments forwarded");
        check(Thread.currentThread() == com.gtnewhorizons.retrofuturabootstrap.TestDelegate.thread, "macOS main thread preserved");
        System.out.println("Bootstrap install, upgrade, rollback, migration, verification, and offline launch passed");
    }
}
