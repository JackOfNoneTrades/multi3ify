# multi3ify

Prism metadata with automatic lwjgl3ify installation for Minecraft 1.7.10.
All regular versions remain available. UniMixins is the only mod you install manually.

## Setup

1. Set **Settings → APIs → Services → Metadata Server** to:

   ```text
   https://jackofnonetrades.github.io/multi3ify/v1/
   ```

2. Create **`1.7.10-lwjgl3ify`**, leaving **Mod Loader → None**. Forge installs automatically.
3. Add the [UniMixins combined jar](https://github.com/LegacyModdingMC/UniMixins/releases)
   (0.1.23+) to the instance’s `mods` folder.
4. Enable automatic Java selection/download, clear any forced Java 8 override, and launch.

## Existing instances

Select **Edit Instance → Version → Minecraft → Change version → `1.7.10-lwjgl3ify`**.
Changing Minecraft removes the old LWJGL 2 dependency; changing only Forge leaves it installed.
Revert any old local Minecraft/Forge or lwjgl3ify component patches first.
Worlds, mods, and configuration stay in place.

## Choose a release

After creating the instance: **Edit Instance → Version → lwjgl3ify → Change version**.

- **`latest`** follows stable releases, checked every six hours.
- **Numbered versions** stay pinned. Switching also supports downgrades.

The next launch installs your selection. Restart the launcher if its version list is stale.

## Self-host

Fork, enable Actions, set **Settings → Pages → Source → GitHub Actions**, then run
**Update and publish metadata**. Use your Pages URL ending in `/v1/`.

Optional repository Actions variables:

| Variable | Default |
| --- | --- |
| `PRISM_META_REPOSITORY` | `PrismLauncher/meta-launcher` |
| `PRISM_META_REF` | Upstream default branch |
| `LWJGL3IFY_MIN_VERSION` | `3.0.0` |
