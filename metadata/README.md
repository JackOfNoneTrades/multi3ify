# Published compatibility metadata

`legacy-forge.zip` preserves the 34 numbered Forge profiles published by commit
`3871656ee459b25ef7a30cbbf0d0effe40e175f7` (lwjgl3ify 3.0.0–3.0.33). Its internal
`index.json` records their original published SHA-256 hashes, checked against the
live Pages index when the archive was created.

The build serves these files at their original URLs without listing them in the
Forge picker. Do not rewrite their contents: installed instances can retain the
old hashes in Prism's metadata cache. Their existing helper is retained under
`bootstrap/releases/`. The old `latest` entry is deliberately excluded: it remains
indexed and becomes the bridge to the dedicated lwjgl3ify component.

To inspect the original JSON:

```sh
python3 -m zipfile -e metadata/legacy-forge.zip /tmp/multi3ify-legacy-forge
```

`cleanroom-lock.json` records the verified ZIP, universal jar and generated
component hashes for published Cleanroom releases. CI updates it after a
successful deployment. The builder refuses to silently replace a published
numbered release if upstream assets or its generated runtime change.
