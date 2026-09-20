import copy
import hashlib
import io
import json
from itertools import permutations
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from scripts import build_metadata as meta, cleanroom
from scripts.verify_metadata import verify
from scripts.smoke_cleanroom import library_tasks
from test_metadata import profile as lwjgl3ify_profile, upstream


UNIVERSAL = b"test universal jar"


def artifact(data=b"test library", url="https://example.org/library.jar"):
    return {"url": url, "sha1": hashlib.sha1(data).hexdigest(), "size": len(data)}


def profile(version=cleanroom.MINIMUM):
    library = {"name": "org.lwjgl:lwjgl:3.4.1-unsafe", "downloads": {"artifact": artifact()}}
    narrator = {"name": "com.mojang:text2speech:1.10.3", "downloads": {"artifact": artifact()},
                "rules": [{"action": "allow"}, {"action": "disallow", "os": {"name": "osx-arm64"}}]}
    native_narrator = copy.deepcopy(narrator)
    native_narrator["downloads"]["classifiers"] = {"natives-linux": artifact(url="https://example.org/natives.jar")}
    native_narrator["natives"] = {"linux": "natives-linux"}
    native_narrator["extract"] = {"exclude": ["META-INF/"]}
    return {"version": version, "releaseTime": "2026-09-12T13:25:19Z",
            "archiveSha256": "a" * 64, "universalSha256": meta.sha256(UNIVERSAL), "patches": [
        {"formatVersion": 1, "uid": "org.lwjgl3", "version": "3.4.1", "libraries": [library]},
        {"formatVersion": 1, "uid": "net.minecraft", "version": "1.12.2", "name": "Minecraft",
         "mainClass": "net.minecraft.client.main.Main", "compatibleJavaMajors": [25, 26],
         "requires": [{"uid": "org.lwjgl3", "suggests": "3.3.1"}], "libraries": [narrator, native_narrator],
         "mainJar": {"name": "com.mojang:minecraft:1.12.2:client", "downloads": {"artifact": artifact()}},
         "assetIndex": {"id": "1.12", **artifact()}, "minecraftArguments": "--version ${version_name}"},
        {"formatVersion": 1, "uid": "net.minecraftforge", "version": version, "name": "Cleanroom",
         "mainClass": cleanroom.MAIN_CLASS, "+tweakers": ["net.minecraftforge.fml.common.launcher.FMLTweaker"],
         "+jvmArgs": ["-Dfile.encoding=UTF-8"], "requires": [{"uid": "net.minecraft", "equals": "1.12.2"}],
         "libraries": [{"name": f"com.cleanroommc:cleanroom:{version}", "downloads": {"artifact": artifact(UNIVERSAL)}}]},
    ]}


def source(path):
    upstream(path)
    meta.add_versions(path, "net.minecraft", [{"formatVersion": 1, "uid": "net.minecraft", "version": "1.12.2"}])
    meta.add_versions(path, "net.minecraft.java", [{"formatVersion": 1, "uid": "net.minecraft.java", "version": "java25",
                      "runtimes": [{"name": "java-runtime-epsilon", "version": {"major": 25}, "runtimeOS": "linux-x64"}]}], name="Java")


def release_assets(p, mutate=None):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for document in p["patches"]:
            archive.writestr(f"patches/{document['uid']}.json", meta.encoded(document))
        archive.writestr("mmc-pack.json", meta.encoded({"components": [
            {"uid": d["uid"], "version": d["version"]} for d in p["patches"]]}))
        if mutate:
            mutate(archive)
    data = [buffer.getvalue(), UNIVERSAL]
    assets = [{"name": f"cleanroom-{p['version']}{suffix}", "size": len(b), "digest": "sha256:" + meta.sha256(b),
               "browser_download_url": "https://example.org/" + suffix} for b, suffix in zip(data, (".zip", "-universal.jar"))]
    return {"tag_name": p["version"], "published_at": p["releaseTime"], "assets": assets}, data


class CleanroomTests(unittest.TestCase):
    def setUp(self):
        # CI fills the real lock after deployment. Synthetic releases must not
        # depend on which upstream artifacts this checkout has published.
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        lock = root / "cleanroom-lock.json"
        lock.write_text("{}\n")
        self.enterContext(patch.object(cleanroom, "LOCK_PATH", lock))

    def test_release_filter_accepts_published_alpha_and_orders_numerically(self):
        def release(tag, **kw):
            return {"tag_name": tag, "draft": False, "prerelease": False, **kw}
        first = [release("0.6.9-alpha")] * 96 + [release("0.6.14-alpha"), release("0.6.14"),
                   release("0.6.15-alpha", prerelease=True), release("0.6.16-alpha", draft=True)]
        second = [release("v0.6.13-alpha"), release("0.7.0-beta"), release("nightly")]
        with patch.object(cleanroom, "fetch", side_effect=[meta.encoded(first), meta.encoded(second)]):
            self.assertEqual([r["tag_name"] for r in cleanroom.releases(cleanroom.MINIMUM)],
                             ["0.6.14", "0.6.14-alpha", "v0.6.13-alpha"])

    def test_archive_verification_and_cache(self):
        release, data = release_assets(profile())
        with tempfile.TemporaryDirectory() as tmp, patch.object(meta, "fetch", side_effect=data) as fetch:
            result = cleanroom.release_profile(release, Path(tmp))
            self.assertEqual(result["patches"], profile()["patches"])
            self.assertEqual(result, cleanroom.release_profile(release, Path(tmp)))
            self.assertEqual(fetch.call_count, 2)
        bad = copy.deepcopy(release)
        bad["assets"][0]["digest"] = "sha256:" + "0" * 64
        with tempfile.TemporaryDirectory() as tmp, patch.object(meta, "fetch", return_value=data[0]):
            with self.assertRaisesRegex(ValueError, "checksum mismatch"):
                cleanroom.release_profile(bad, Path(tmp))

    def test_missing_assets_changed_layout_and_wrong_universal_are_rejected(self):
        release, data = release_assets(profile(), lambda z: z.writestr("patches/new.json", "{}"))
        with tempfile.TemporaryDirectory() as tmp, patch.object(meta, "fetch", side_effect=data):
            with self.assertRaisesRegex(ValueError, "archive layout"):
                cleanroom.release_profile(release, Path(tmp))
        release["assets"].pop()
        with self.assertRaisesRegex(ValueError, "missing required assets"):
            cleanroom.release_profile(release, Path("unused"))
        p = profile()
        p["patches"][-1]["libraries"][0]["downloads"]["artifact"]["sha1"] = "0" * 40
        release, data = release_assets(p)
        with tempfile.TemporaryDirectory() as tmp, patch.object(meta, "fetch", side_effect=data):
            with self.assertRaisesRegex(ValueError, "universal jar and profile disagree"):
                cleanroom.release_profile(release, Path(tmp))

    def test_unrecognized_runtime_changes_fail_closed(self):
        for change in (
            lambda p: p["patches"][-1].update(mainClass="new.Launcher"),
            lambda p: p["patches"][1].update(compatibleJavaMajors=[8, 25]),
            lambda p: p["patches"][1].update(compatibleJavaMajors=[27]),
            lambda p: p["patches"][0].update(newLaunchMechanism=True),
            lambda p: p["patches"][0]["libraries"][0].update({"MMC-hint": "local"}),
            lambda p: p["patches"][0].update(version="3.5.0"),
        ):
            with self.subTest(change=change):
                p = profile()
                change(p)
                with self.assertRaises(ValueError):
                    cleanroom.validate_profile(p)

    def test_runtime_preserves_rules_natives_and_owns_all_launch_settings(self):
        p = profile()
        with tempfile.TemporaryDirectory() as tmp:
            source(Path(tmp))
            minecraft, bridge, runtime = cleanroom.documents(p, Path(tmp))
        self.assertEqual(p, profile())
        self.assertEqual(runtime["libraries"], [lib for patch in p["patches"] for lib in patch["libraries"]])
        self.assertEqual(minecraft["mainJar"], p["patches"][1]["mainJar"])
        self.assertEqual(minecraft["assetIndex"], p["patches"][1]["assetIndex"])
        self.assertEqual(minecraft["requires"], [{"uid": "net.minecraftforge", "equals": cleanroom.BRIDGE_VERSION}])
        self.assertNotEqual(bridge["name"], runtime["name"], "the release picker must be distinguishable from the bridge")
        for components in permutations([minecraft, bridge, runtime]):
            settings = {key: value for c in components for key, value in c.items()
                        if key in ("mainClass", "compatibleJavaMajors", "compatibleJavaName")}
            self.assertEqual(settings, {"mainClass": cleanroom.MAIN_CLASS, "compatibleJavaMajors": [25, 26],
                                        "compatibleJavaName": "java-runtime-epsilon"})
        self.assertEqual(runtime["requires"], [{"uid": "net.minecraft", "equals": "1.12.2"}])
        self.assertNotIn("mods", runtime)
        self.assertNotIn("multi3ify.", str(runtime))

    def test_java_download_runtime_must_exist_in_mirrored_feed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source(root)
            meta.write_json(root / "net.minecraft.java/java25.json", {"runtimes": []})
            with self.assertRaisesRegex(ValueError, "no matching Java runtime"):
                cleanroom.documents(profile(), root)

    def test_smoke_classpath_keeps_narrator_and_extracts_its_native(self):
        libraries = profile()["patches"][1]["libraries"]
        tasks, classpath, natives = library_tasks(libraries + libraries, Path("test"))
        self.assertEqual(len(tasks), 2)
        self.assertEqual(len(classpath), 1)
        self.assertEqual(len(natives), 1)
        self.assertEqual(classpath[0].name, "library.jar")
        self.assertEqual(natives[0].name, "natives.jar")

    def test_combined_feed_preserves_existing_integration_and_pins(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source(root / "upstream")
            with patch.object(meta, "build_bootstrap", return_value={"name": "test:bootstrap:1"}):
                meta.build(root / "upstream", root / "old", "https://example.org", [lwjgl3ify_profile()])
                meta.build(root / "upstream", root / "before", "https://example.org", [lwjgl3ify_profile()], [profile()])
                meta.build(root / "upstream", root / "after", "https://example.org", [lwjgl3ify_profile()],
                           [profile("0.6.14-alpha"), profile()])
            for original in (root / "old/v1").rglob("*.json"):
                if original.name != "index.json":
                    self.assertEqual(original.read_bytes(), (root / "after/v1" / original.relative_to(root / "old/v1")).read_bytes())
            runtime_path = f"v1/{meta.CLEANROOM_UID}/{cleanroom.MINIMUM}.json"
            self.assertEqual((root / "before" / runtime_path).read_bytes(), (root / "after" / runtime_path).read_bytes())
            verify(root / "after/v1", require_cleanroom=True)
            mc = json.loads((root / "after/v1/net.minecraft/1.12.2-cleanroom.json").read_bytes())
            self.assertEqual(mc["version"], "1.12.2")
            index = json.loads((root / "after/v1" / meta.CLEANROOM_UID / "index.json").read_bytes())
            self.assertEqual([v["version"] for v in index["versions"] if v["recommended"]], ["latest"])
            with self.assertRaisesRegex(ValueError, "Missing custom Minecraft/Cleanroom"):
                verify(root / "old/v1", require_cleanroom=True)

    def test_published_release_cannot_be_replaced(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source(root / "v1")
            cleanroom.publish(root / "v1", [profile()])
            source(root / "second")
            p = profile()
            p["archiveSha256"] = "b" * 64
            with patch.object(cleanroom, "LOCK_PATH", root / "cleanroom-lock.json"):
                with self.assertRaisesRegex(ValueError, "Refusing to change published"):
                    cleanroom.publish(root / "second", [p])


if __name__ == "__main__":
    unittest.main()
