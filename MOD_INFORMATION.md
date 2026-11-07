# Mod information

## Current status

The public mod catalogue is **not populated yet**. The pack is still in development and there is no downloadable public release or published pack manifest to use as the source of truth.

We will publish the mod list once it can be generated from the exact approved CurseForge pack manifest. This avoids guessing from screenshots, old test folders, or mod counts.

## What this page will show

For each mod included in the published pack, the catalogue is designed to show:

| Information | Meaning |
|---|---|
| Mod name | Name reported by CurseForge |
| Current pack file | Exact file included in the published pack manifest |
| Latest stable file for Minecraft 1.21.1 + NeoForge | Latest stable file returned by CurseForge for the target version and loader |
| Update status | Whether the included file matches that latest stable listing, or needs maintainer review |
| CurseForge page | Link to the mod's official CurseForge project page |

## Important: update notices are not approvals

A newer CurseForge file is **not automatically safe or compatible** with the modpack.

The catalogue will only report that a newer file exists. The maintainer must still review its dependencies, loader support, client/server requirements, conflicts, and compatibility with the rest of the pack. No mod will be installed or updated automatically by this catalogue.

## Refresh schedule

Once the official pack manifest and CurseForge API access are configured, this page will refresh automatically every week. A maintainer can also run the refresh manually.

For the technical details, see [Mod catalogue automation](docs/MOD_CATALOGUE_AUTOMATION.md).

## Source and safeguards

The catalogue is read-only. It checks the manifest's exact CurseForge file IDs and reports metadata; it never installs or updates a mod. See [the automation notes](docs/MOD_CATALOGUE_AUTOMATION.md).
