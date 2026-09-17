# multi3ify

A GitHub Pages metadata server for Prism Launcher and compatible forks. It mirrors
the complete official catalog and adds **Minecraft `1.7.10-lwjgl3ify`**, with Forge
`10.13.4.1614` and your choice of stable lwjgl3ify 3.x releases.

**No scripts, patch files, or manual lwjgl3ify downloads for players. Install
UniMixins once; the launcher profile handles the rest.**

## Use it

1. In **Settings → APIs → Services → Metadata Server**, enter:

   ```text
   https://jackofnonetrades.github.io/multi3ify/v1/
   ```

2. Create an instance with Minecraft **`1.7.10-lwjgl3ify`**. Its custom Forge
   component is installed automatically.
3. Put the [UniMixins combined jar](https://github.com/LegacyModdingMC/UniMixins/releases)
   (0.1.23 or newer, not the `dev` jar) in the instance's `mods` folder.
4. Launch. Leave Prism's **automatic Java selection and download** enabled.
   Upstream's supported Java versions and JVM arguments are included in the profile.
   A manually forced Java 8 installation must be cleared in the instance settings.

The default Forge version, **`10.13.4.1614-lwjgl3ify-latest`**, follows new stable
releases when Prism refreshes its metadata. Restart Prism to refresh a cached
version list. For a fixed version, select **Edit Instance → Version → Forge →
Change version**, then choose e.g. `10.13.4.1614-lwjgl3ify-3.0.33`. Use the same
menu to downgrade or return to `latest`.

The helper installs the selected mod before Forge starts. It verifies SHA-256,
updates a single managed jar, and needs no network when that jar is already current.
Existing manual lwjgl3ify copies in `mods` or `mods/1.7.10` are identified by their
manifest and backed up under `.minecraft/.multi3ify-backups/` (or the equivalent
game directory). Previous managed versions are backed up there too. UniMixins and
other mods are untouched.

For an existing ordinary Forge instance, back it up, remove its Forge component,
and change Minecraft to `1.7.10-lwjgl3ify`. The new Forge dependency installs on
launch. Instances with old local lwjgl3ify patches need those custom components
reverted/removed first; local patches override server metadata.

Prism's integrated mod browser automatically searches for **Minecraft 1.7.10**.
The selected profile remains `1.7.10-lwjgl3ify`, but its component reports the real
game version. Existing instances created before this fix should restart Prism,
launch once to refresh metadata, and reopen the mod browser. No instance rebuild
or local JSON edits are needed.

Forks must support custom metadata URLs, component dependencies, `+jvmArgs`, and
modern Java. The launcher settings and mod compatibility of arbitrary forks
cannot be fixed by a metadata server.

## Host your own

1. Fork this repository and enable Actions.
2. Under **Settings → Pages**, select **GitHub Actions** as the source.
3. Optionally set repository variables under **Settings → Secrets and variables →
   Actions → Variables**:

   | Variable | Default | Purpose |
   | --- | --- | --- |
   | `PRISM_META_REPOSITORY` | `PrismLauncher/meta-launcher` | Repository containing the official, already-generated Prism metadata |
   | `PRISM_META_REF` | Repository's default branch | Optional branch/tag/commit to mirror |
   | `LWJGL3IFY_MIN_VERSION` | `3.0.0` | Oldest stable release to publish; must be 3.0.0 or newer |

4. Run **Update and publish metadata**. Use the URL shown on your Pages site,
   ending in `/v1/`, in your launcher.

The workflow runs on pushes, manual dispatch, and every six hours. It reads all
GitHub release pages, excludes drafts and prerelease tags, caches verified release
profiles, and publishes one complete Pages artifact. No personal access token is
needed: the normal `GITHUB_TOKEN` reads releases and records a small
`sync-state.json` commit when upstream changes. These commits also keep the public
repository active so GitHub does not disable its schedule after 60 days of
inactivity. Protected branches must allow that bot commit, or you must maintain
repository activity yourself. A failed build leaves the previously published site
in place.

## How it works

The generator copies every indexed official metadata document byte for byte and
checks the complete SHA-256 chain. Only the Minecraft/Forge indexes and the root
index gain new entries/checksums. Ordinary Minecraft, Forge, Fabric, Quilt,
NeoForge, LWJGL, and Java versions remain available.

Each custom Forge entry is assembled from that release's official `-multimc.zip`.
Its Minecraft libraries, LWJGL natives, early Forge patches, Forge libraries,
Java requirements, JVM arguments, and macOS first-thread entry point are retained
in upstream order. The embedded `forgePatches` jar is converted into a verified
remote download. All large game/mod/library artifacts remain upstream-hosted.
The Pages site hosts JSON, a landing page, and the small Java helper compiled in CI.
Successfully published helper jars are retained in `bootstrap/releases/` so cached
metadata can still download older helper versions after a deployment.

The helper downloads the selected mod into the instance and then calls the
upstream entry point on the same thread. It is needed because Prism's parsed
`mods` metadata field is not downloaded by its library installer. Putting the mod
on the classpath alone does not reproduce Forge's coremod discovery.

A separate Minecraft entry is necessary to remove vanilla 1.7.10's LWJGL 2 and
Java 8 requirements. Prism **appends** Java compatibility lists; a Forge patch
cannot subtract Java 8. The custom Minecraft entry delegates runtime requirements
to the chosen custom Forge version, so both automatic dependency order and manual
Forge selection work. It still downloads the original Mojang 1.7.10 client and
assets. Its dependency suggests the `latest` Forge alias without forcing pinned
instances back onto it.

The catalog ID and filename are `1.7.10-lwjgl3ify`, while the Minecraft document's
`version` is `1.7.10`. Prism retains the catalog ID for metadata downloads, then
caches the document's version for mod searches, Forge version filtering, dependency
checks, and game arguments. Custom Forge requirements therefore use `1.7.10` too.
The generator explicitly validates this single alias; all other document identities
must match their catalog entries. Vanilla `net.minecraft/1.7.10.json` remains
unchanged. Choose the special profile at instance creation to get the modern
runtime even though the loaded component displays the normal game version.

The generator verifies that the upstream patches target the latest official
1.7.10 Forge build (currently `10.13.4.1614`). A changed patch layout, missing asset,
checksum mismatch, or incompatible Forge target fails publication instead of
silently emitting an incomplete profile. lwjgl3ify 1.x/2.x profiles are outside
this generator's supported layout.

## Develop and verify

Requires Python 3.11+ and JDK 17+; no third-party Python packages.

```sh
python3 -m unittest discover -s tests -v
git clone --depth 1 https://github.com/PrismLauncher/meta-launcher.git .upstream
python3 scripts/build_metadata.py --upstream .upstream --output public \
  --site-url https://YOUR-ACCOUNT.github.io/multi3ify
python3 -m scripts.verify_metadata public/v1
python3 -m http.server --directory public 8000
```

The output directory must be fresh for each build. To check only the current
release quickly, add `--minimum 3.0.33`. The full build publishes all stable 3.x+
releases. Tests cover byte-preserving mirroring, checksum failure, release
pagination/filtering, mod-search version reporting, dependency resolution, classpath order, Java compatibility,
and real Java helper installation, migration, upgrade, rollback, and offline reuse.
Before publishing, Linux CI also downloads the real game libraries and assets and
launches the latest generated profile under Xvfb in an isolated offline instance
with only UniMixins preinstalled. Publication requires Forge to finish mod
initialization. Run this check locally on Linux with
`xvfb-run -a python3 -m scripts.smoke_launch public`.

Upstream references: [Prism metadata](https://github.com/PrismLauncher/meta-launcher),
[Prism API settings](https://prismlauncher.org/wiki/help-pages/apis/),
[lwjgl3ify setup](https://github.com/GTNewHorizons/lwjgl3ify/blob/master/README.MD),
[Prism library installer](https://github.com/PrismLauncher/PrismLauncher/blob/develop/launcher/minecraft/update/LibrariesTask.cpp),
[Prism Java compatibility merging](https://github.com/PrismLauncher/PrismLauncher/blob/develop/launcher/minecraft/LaunchProfile.cpp),
[Prism component version caching](https://github.com/PrismLauncher/PrismLauncher/blob/develop/launcher/minecraft/Component.cpp),
[Prism mod search filters](https://github.com/PrismLauncher/PrismLauncher/blob/develop/launcher/ui/widgets/ModFilterWidget.cpp).
