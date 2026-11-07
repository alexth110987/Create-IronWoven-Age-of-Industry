# Mod catalogue automation

## Purpose

The public mod catalogue is generated from the exact CurseForge modpack manifest. It must not be assembled from screenshots, old test folders, or guessed mod names.

The catalogue reads the included project IDs and file IDs from:

`data/curseforge-manifest.json`

That file should be an exported manifest for the approved public pack version. Do not add an unfinished or private test manifest to this public repository.

## CurseForge API access

The updater uses the official CurseForge for Studios API:
- Base URL: `https://api.curseforge.com/v1`
- Minecraft game ID: `432`
- Target Minecraft version: `1.21.1`
- NeoForge loader type: `6`
- API authentication header: `x-api-key`

The API key must be stored as a GitHub Actions repository secret named `CURSEFORGE_API_KEY`. Never commit the key, print it in logs, or paste it into an issue.

CurseForge requires third-party API access to be requested and approved. See the [official API documentation](https://docs.curseforge.com/rest-api/) and [CurseForge for Studios console](https://console.curseforge.com/).

## Refresh process

The GitHub Actions workflow runs weekly, when the manifest changes, or when a maintainer starts it manually.

Only available files tagged as stable releases (release type 1) and with an API file status of Approved (4) or Released (10) are considered for the latest-stable comparison.\n\nFor each mod in the manifest, it:
1. Reads the exact installed CurseForge project ID and file ID.
2. Retrieves the installed file details from CurseForge.
3. Retrieves the latest stable files filtered to Minecraft 1.21.1 and NeoForge.
4. Compares the installed file with the latest stable compatible listing.
5. Regenerates the public `MOD_INFORMATION.md` page.

The workflow does not download, install, replace, or change any modpack files.

## How to read the status

- **Matches latest stable listing:** the manifest's file ID matches the latest stable file returned for the target game version and loader.
- **Newer stable file found — review required:** CurseForge lists a later stable file for the target. This does not prove it works with the whole pack.
- **Manual review required:** the installed file differs from the latest stable listing, but the dates do not prove that the other file is a newer stable update.
- **Installed file is a pre-release:** the included file is tagged as beta or alpha by CurseForge.

A newer upstream file is never an automatic approval. The normal compatibility review, dependency checks, side checks, testing, and maintainer approval are still required before a pack update.

## What is needed to activate it

1. Export the actual public pack manifest from the approved CurseForge profile.
2. Add it to this repository as `data/curseforge-manifest.json`.
3. Obtain approved CurseForge API access.
4. Add the key as the `CURSEFORGE_API_KEY` Actions secret.
5. Run **Update CurseForge mod information** from the Actions tab.

Until the manifest and API key are configured, the public catalogue will clearly say that it is waiting for its source data.
