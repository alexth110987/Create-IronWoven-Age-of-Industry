#!/usr/bin/env python3
"""Generate a public CurseForge mod catalogue from an approved pack manifest."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

API_BASE = "https://api.curseforge.com/v1"
NEOFORGE_LOADER_TYPE = 6
PAGE_SIZE = 50


class CurseForgeError(RuntimeError):
    """Raised when CurseForge data cannot be retrieved safely."""


def api_request(api_key: str, path: str, *, method: str = "GET",
                payload: dict[str, Any] | None = None) -> dict[str, Any]:
    url = API_BASE + path
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Accept": "application/json", "x-api-key": api_key}
    if data is not None:
        headers["Content-Type"] = "application/json"

    for attempt in range(4):
        request = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                body = json.loads(response.read().decode("utf-8"))
                if not isinstance(body, dict) or "data" not in body:
                    raise CurseForgeError("CurseForge returned an unexpected response.")
                return body
        except urllib.error.HTTPError as exc:
            if exc.code in (429, 500, 502, 503, 504) and attempt < 3:
                time.sleep(2 ** attempt)
                continue
            raise CurseForgeError(
                f"CurseForge API request failed with HTTP {exc.code} for {path}."
            ) from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            if attempt < 3:
                time.sleep(2 ** attempt)
                continue
            raise CurseForgeError(f"CurseForge API request failed for {path}.") from exc
        except json.JSONDecodeError as exc:
            raise CurseForgeError("CurseForge returned invalid JSON.") from exc
    raise CurseForgeError("CurseForge API request did not complete.")


def chunks(values: list[int], size: int) -> list[list[int]]:
    return [values[index:index + size] for index in range(0, len(values), size)]


def load_manifest(path: Path) -> tuple[str, list[dict[str, int]]]:
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise CurseForgeError(f"Manifest not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise CurseForgeError("The CurseForge manifest is not valid JSON.") from exc

    if not isinstance(manifest, dict):
        raise CurseForgeError("The CurseForge manifest root must be a JSON object.")
    if manifest.get("manifestType") != "minecraftModpack":
        raise CurseForgeError("The manifest is not a CurseForge Minecraft modpack manifest.")

    minecraft = manifest.get("minecraft") or {}
    if not isinstance(minecraft, dict):
        raise CurseForgeError("Manifest minecraft section is invalid.")
    game_version = minecraft.get("version")
    loaders = minecraft.get("modLoaders") or []
    if not isinstance(game_version, str) or not game_version:
        raise CurseForgeError("Manifest is missing minecraft.version.")
    if not any(
        str(item.get("id", "")).lower().startswith("neoforge-")
        for item in loaders if isinstance(item, dict)
    ):
        raise CurseForgeError("Manifest does not identify a NeoForge loader.")

    entries: list[dict[str, int]] = []
    seen_projects: dict[int, int] = {}
    for item in manifest.get("files") or []:
        if not isinstance(item, dict) or item.get("required", True) is False:
            continue
        project_id = item.get("projectID")
        file_id = item.get("fileID")
        if not isinstance(project_id, int) or not isinstance(file_id, int):
            raise CurseForgeError("Manifest contains a file without numeric projectID/fileID.")
        if project_id in seen_projects and seen_projects[project_id] != file_id:
            raise CurseForgeError(
                f"Manifest lists more than one required file for project {project_id}."
            )
        if project_id not in seen_projects:
            entries.append({"projectID": project_id, "fileID": file_id})
            seen_projects[project_id] = file_id

    if not entries:
        raise CurseForgeError("Manifest contains no required CurseForge mod files.")
    return game_version, entries


def parse_date(value: str | None) -> dt.datetime | None:
    if not value:
        return None
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=dt.timezone.utc)
        return parsed
    except ValueError:
        return None


def classify_status(installed: dict[str, Any],
                    latest_stable: dict[str, Any] | None) -> str:
    release_type = installed.get("releaseType")
    if release_type in (2, 3):
        installed_kind = "beta" if release_type == 2 else "alpha"
        if latest_stable and latest_stable.get("id") != installed.get("id"):
            return f"Installed file is a {installed_kind} pre-release; review required"
        return f"Installed file is a {installed_kind} pre-release"

    if not latest_stable:
        return "No stable file found for the target version and loader"

    if installed.get("id") == latest_stable.get("id"):
        return "Matches latest stable listing"

    installed_date = parse_date(installed.get("fileDate"))
    latest_date = parse_date(latest_stable.get("fileDate"))
    if installed_date and latest_date and latest_date > installed_date:
        return "Newer stable file found — review required"
    return "Manual review required — installed file differs from latest stable listing"


def fetch_installed_files(api_key: str, file_ids: list[int]) -> dict[int, dict[str, Any]]:
    result: dict[int, dict[str, Any]] = {}
    for group in chunks(file_ids, 50):
        body = api_request(api_key, "/mods/files", method="POST", payload={"fileIds": group})
        for item in body.get("data") or []:
            if isinstance(item, dict) and isinstance(item.get("id"), int):
                result[item["id"]] = item
    missing = sorted(set(file_ids) - set(result))
    if missing:
        raise CurseForgeError(
            "CurseForge did not return metadata for manifest file ID(s): "
            + ", ".join(map(str, missing))
        )
    return result


def fetch_mod_details(api_key: str, project_ids: list[int]) -> dict[int, dict[str, Any]]:
    result: dict[int, dict[str, Any]] = {}
    for group in chunks(project_ids, 10):
        body = api_request(api_key, "/mods", method="POST", payload={"modIds": group})
        for item in body.get("data") or []:
            if isinstance(item, dict) and isinstance(item.get("id"), int):
                result[item["id"]] = item
    missing = sorted(set(project_ids) - set(result))
    if missing:
        raise CurseForgeError(
            "CurseForge did not return metadata for project ID(s): "
            + ", ".join(map(str, missing))
        )
    return result


def fetch_latest_stable(api_key: str, project_id: int,
                        game_version: str) -> dict[str, Any] | None:
    files: list[dict[str, Any]] = []
    index = 0
    while True:
        query = urllib.parse.urlencode({
            "gameVersion": game_version,
            "modLoaderType": str(NEOFORGE_LOADER_TYPE),
            "index": str(index),
            "pageSize": str(PAGE_SIZE),
        })
        body = api_request(api_key, f"/mods/{project_id}/files?{query}")
        page = body.get("data") or []
        files.extend(item for item in page if isinstance(item, dict))
        pagination = body.get("pagination") or {}
        total = pagination.get("totalCount")
        if not page or len(page) < PAGE_SIZE or (
            total is not None and index + len(page) >= total
        ):
            break
        index += len(page)
        if index >= 10000:
            break

    stable = [
        item for item in files
        if item.get("isAvailable", True)
        and item.get("releaseType") == 1
        and item.get("fileStatus") in (4, 10)
        and game_version in (item.get("gameVersions") or [])
    ]
    if not stable:
        return None

    earliest = dt.datetime.min.replace(tzinfo=dt.timezone.utc)
    return max(stable, key=lambda item: parse_date(item.get("fileDate")) or earliest)


def markdown_cell(value: Any) -> str:
    return str(value or "—").replace("|", "\\|").replace("\n", " ")


def render_markdown(game_version: str, entries: list[dict[str, Any]]) -> str:
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    matching = sum(row["status"] == "Matches latest stable listing" for row in entries)
    review = len(entries) - matching
    lines = [
        "# Mod information",
        "",
        f"**Last checked:** {now}  ",
        f"**Pack target:** Minecraft {game_version} · NeoForge  ",
        f"**Mods listed:** {len(entries)} · **Match latest stable listing:** {matching} · **Review needed:** {review}",
        "",
        "> **Important:** this is an upstream file-information check, not a compatibility approval. A newer file is never installed automatically. Every proposed pack change still needs a separate compatibility review and maintainer approval.",
        "",
        "| Mod | File included in pack | Latest stable file for target | Status | CurseForge |",
        "|---|---|---|---|---|",
    ]
    for row in sorted(entries, key=lambda item: item["name"].casefold()):
        lines.append(
            f"| {markdown_cell(row['name'])} | {markdown_cell(row['installed_file'])} "
            f"| {markdown_cell(row['latest_file'])} | {markdown_cell(row['status'])} "
            f"| [Project page]({row['url']}) |"
        )
    lines.extend([
        "",
        "This page is generated from the approved CurseForge pack manifest and CurseForge API metadata. "
        "It does not change the pack or download mod files.",
        "",
        "See [Mod catalogue automation](docs/MOD_CATALOGUE_AUTOMATION.md) for the source and review rules.",
        "",
    ])
    return "\n".join(lines)


def build_catalogue(manifest_path: Path, api_key: str) -> str:
    game_version, manifest_entries = load_manifest(manifest_path)
    if game_version != "1.21.1":
        raise CurseForgeError(
            f"Manifest targets Minecraft {game_version}; expected the approved project target 1.21.1."
        )

    project_ids = [item["projectID"] for item in manifest_entries]
    file_ids = [item["fileID"] for item in manifest_entries]
    installed_files = fetch_installed_files(api_key, file_ids)
    mods = fetch_mod_details(api_key, project_ids)

    output: list[dict[str, Any]] = []
    for entry in manifest_entries:
        project_id = entry["projectID"]
        file_id = entry["fileID"]
        installed = installed_files[file_id]
        mod = mods[project_id]
        if installed.get("modId") != project_id:
            raise CurseForgeError(
                f"Manifest project/file mismatch for project ID {project_id}, file ID {file_id}."
            )

        latest = fetch_latest_stable(api_key, project_id, game_version)
        links = mod.get("links") or {}
        slug = mod.get("slug")
        url = links.get("websiteUrl") or (
            f"https://www.curseforge.com/minecraft/mc-mods/{slug}" if slug else
            f"https://www.curseforge.com/minecraft/search?page=1&search={project_id}"
        )
        output.append({
            "name": mod.get("name") or installed.get("displayName") or f"CurseForge project {project_id}",
            "installed_file": installed.get("displayName") or installed.get("fileName") or str(file_id),
            "latest_file": (
                latest.get("displayName") or latest.get("fileName") or str(latest.get("id"))
                if latest else "No stable file found"
            ),
            "status": classify_status(installed, latest),
            "url": url,
        })
    return render_markdown(game_version, output)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=Path("data/curseforge-manifest.json"))
    parser.add_argument("--output", type=Path, default=Path("MOD_INFORMATION.md"))
    parser.add_argument("--api-key", default=os.environ.get("CURSEFORGE_API_KEY"))
    args = parser.parse_args()

    if not args.api_key:
        print("ERROR: CURSEFORGE_API_KEY is not set. Store it as a GitHub Actions secret.", file=sys.stderr)
        return 2

    try:
        rendered = build_catalogue(args.manifest, args.api_key)
    except CurseForgeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    args.output.write_text(rendered, encoding="utf-8")
    print(f"Updated {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
