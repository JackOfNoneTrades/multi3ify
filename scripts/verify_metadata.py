#!/usr/bin/env python3
"""Verify the complete served checksum chain and custom component dependencies."""
import argparse
import json
from pathlib import Path
import zipfile

from scripts.build_metadata import MC_VERSION, GAME_VERSION, LWJGL3IFY_UID, ROOT, read_verified, reported_version, segment


def verify(root):
    packages = json.loads((root / "index.json").read_bytes())["packages"]
    versions = {}
    generated = []
    count = 0
    for package in packages:
        uid = segment(package["uid"])
        _, index = read_verified(root / uid / "index.json", package["sha256"])
        versions[uid] = {v["version"] for v in index["versions"]}
        for entry in index["versions"]:
            version = segment(entry["version"])
            _, document = read_verified(root / uid / f"{version}.json", entry["sha256"])
            if document["uid"] != uid or document["version"] != reported_version(uid, version):
                raise ValueError(f"Incorrect identity in {uid}/{version}")
            if "lwjgl3ify" in version or uid == LWJGL3IFY_UID:
                if entry.get("requires") != document.get("requires"):
                    raise ValueError("Index and version requirements disagree")
                generated.append(document)
            count += 1
    for document in generated:
        if document["uid"] == "net.minecraft" and document["version"] != GAME_VERSION:
            raise ValueError("Custom Minecraft must report the real game version for mod searches")
        for requirement in document.get("requires", []):
            version = requirement.get("equals", requirement.get("suggests"))
            if version not in versions[requirement["uid"]]:
                raise ValueError(f"Unresolved dependency: {requirement}")
        if document["uid"] == "net.minecraftforge":
            if {"uid": "net.minecraft", "equals": GAME_VERSION} not in document["requires"]:
                raise ValueError("Forge must depend on Minecraft's reported game version")
            if {"uid": LWJGL3IFY_UID, "suggests": "latest"} not in document["requires"]:
                raise ValueError("Forge must install the independent lwjgl3ify component")
            if "libraries" in document or "mainClass" in document or "+jvmArgs" in document:
                raise ValueError("Forge bridge must not override the selected lwjgl3ify runtime")
        if document["uid"] == LWJGL3IFY_UID:
            names = [lib["name"] for lib in document["libraries"]]
            if any(n.startswith(("org.lwjgl.lwjgl:", "net.minecraft:launchwrapper:", "org.ow2.asm:asm-all:")) for n in names):
                raise ValueError("Obsolete runtime library in lwjgl3ify")
            if 8 in document["compatibleJavaMajors"]:
                raise ValueError("Java 8 in lwjgl3ify")
            patches = next(i for i, n in enumerate(names) if n.endswith(":forgePatches"))
            forge = next(i for i, n in enumerate(names) if n.startswith("net.minecraftforge:forge:"))
            if patches >= forge:
                raise ValueError("Forge patches must precede Forge on the classpath")
    if MC_VERSION not in versions["net.minecraft"] or "latest" not in versions.get(LWJGL3IFY_UID, set()):
        raise ValueError("Missing custom Minecraft/lwjgl3ify entries")
    if len([d for d in generated if d["uid"] == "net.minecraftforge"]) != 1:
        raise ValueError("Forge picker must contain only one additional entry")
    with zipfile.ZipFile(ROOT / "metadata/legacy-forge.zip") as archive:
        for entry in json.loads(archive.read("index.json"))["versions"]:
            if entry["version"] in versions["net.minecraftforge"]:
                raise ValueError("Legacy releases must not clutter the Forge picker")
            read_verified(root / "net.minecraftforge" / (segment(entry["version"]) + ".json"), entry["sha256"])
    print(f"Verified {count} versions, {len(generated)} custom entries, and every SHA-256 link")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    verify(parser.parse_args().root)
