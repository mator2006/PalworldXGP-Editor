#!/usr/bin/env python3
"""palx - fully automatic Xbox Game Pass Palworld save editor (CLI).

Vendored core: xyuqikzz/Palworld-Save-Editor (GPL-3.0), which builds on
KrisCris/Palworld-Pal-Editor (GPL-3.0) and cheahjs/palworld-save-tools (MIT).
See LICENSE-THIRDPARTY.md.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import datetime
import os
import shutil
import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(APP_DIR))

from palworld_pal_editor.application.save_session import SaveSession  # noqa: E402
from palworld_pal_editor.application.save_writer import SaveWriter  # noqa: E402
from palworld_pal_editor.storage.discovery import XgpSourceCatalog  # noqa: E402
from palworld_pal_editor.storage.xgp import XgpWgsAdapter  # noqa: E402
from palworld_pal_editor.core.pal_objects import UUID2HexStr  # noqa: E402


def default_wgs_root() -> Path:
    return (
        Path(os.environ.get("LOCALAPPDATA", ""))
        / "Packages"
        / "PocketpairInc.Palworld_ad4psfrxyesvt"
        / "SystemAppData"
        / "wgs"
    )


def discover_sources(root: Path):
    catalog = XgpSourceCatalog(roots=(root.resolve(),))
    return catalog, [s for s in catalog.discover() if s.status == "available"]


def slot_matches(world_id: str | None, slot: str) -> bool:
    wid = world_id or ""
    if slot == "main":
        return "-Slot" not in wid
    return wid.endswith(f"-Slot{slot}")


def pick_source(sources, world: str | None, slot: str):
    candidates = []
    for s in sources:
        if world and not str(s.world_id).lower().startswith(world.lower()):
            continue
        if not slot_matches(s.world_id, slot):
            continue
        candidates.append(s)
    if not candidates:
        raise SystemExit("error: no matching XGP world/slot found (see `palx list`)")
    candidates.sort(key=lambda s: s.updated_at or datetime.datetime.min.replace(tzinfo=datetime.timezone.utc), reverse=True)
    return candidates[0]


def make_adapter(catalog, root: Path) -> XgpWgsAdapter:
    appdata = APP_DIR / "palx_wgs_workspaces"
    backups = APP_DIR / "palx_wgs_backups"
    return XgpWgsAdapter(
        catalog=catalog,
        workspace_root=appdata,
        backup_root=backups,
        stability_delay=0,
    )


def cmd_list(args) -> None:
    catalog, sources = discover_sources(Path(args.root))
    rows = []
    for s in sources:
        rows.append(
            {
                "name": s.display_name,
                "world": s.world_id,
                "updated": s.updated_at.isoformat() if s.updated_at else None,
                "status": s.status,
            }
        )
    print(json.dumps(rows, ensure_ascii=False, indent=2))


def cmd_info(args) -> None:
    """Read-only inspection: world name, players, overview, guilds."""
    root = Path(args.root)
    catalog, sources = discover_sources(root)
    source = pick_source(sources, args.world, args.slot)
    print(f"[palx] opening: {source.display_name} ({source.world_id})")
    adapter = make_adapter(catalog, root)
    session = SaveSession.open_storage(source, adapter)
    try:
        from palworld_pal_editor.application.query_service import SaveQueryService
        from palworld_save_tools.palsav import decompress_sav_to_gvas
        from palworld_save_tools.gvas import GvasFile
        from palworld_save_tools.paltypes import PALWORLD_TYPE_HINTS

        # World name lives in LevelMeta.sav inside the extracted workspace.
        world_name = None
        meta_path = Path(session._opened.workspace) / "LevelMeta.sav"
        if meta_path.is_file():
            data, _ = decompress_sav_to_gvas(meta_path.read_bytes())
            meta = GvasFile.read(data, PALWORLD_TYPE_HINTS, {})
            world_name = (
                meta.properties.get("SaveData", {})
                .get("value", {})
                .get("WorldName", {})
                .get("value")
            )

        qs = SaveQueryService(session)
        players = qs.players(sort_by="level", descending=True)
        if args.player_name:
            players = [p for p in players if p["name"] == args.player_name]
        result = {
            "world": source.world_id,
            "world_name": world_name,
            "display_name": source.display_name,
            "players": players,
            "overview": qs.overview(),
            "guilds": qs.guilds(),
        }
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    finally:
        session.close()


def apply_edit(session: SaveSession, player, field: str, mutate, target_desc: dict):
    param = getattr(player, "_player_param", None)
    save_data = getattr(player, "_player_save_data", None)
    state_src = param if param is not None else save_data
    if state_src is None:
        raise SystemExit(f"error: cannot edit {field}: no editable state for player")

    state = copy.deepcopy(state_src)

    def restore():
        if param is not None:
            player._player_param.clear()
            player._player_param.update(state)
        else:
            player._player_save_data.clear()
            player._player_save_data.update(state)

    session.apply_atomic(
        session_id=session.session_id,
        expected_revision=session.revision,
        command=f"palx:{field}",
        target=target_desc,
        snapshot=lambda: copy.deepcopy(state_src),
        restore=restore,
        before=lambda: {field: getattr(player, field, None)},
        mutate=mutate,
        validate=lambda: None,
        after=lambda: {field: getattr(player, field, None)},
        affected_records=(
            [f"player_file:{player.PlayerUId}"]
            if field == "TechnologyPoint"
            else [f"level:{player.InstanceId}"]
        ),
    )
    return getattr(player, field, None)


def cmd_edit(args) -> None:
    if args.level is not None and not (1 <= args.level <= 80):
        raise SystemExit("error: --level must be between 1 and 80 (game max level is 80)")
    root = Path(args.root)
    catalog, sources = discover_sources(root)
    source = pick_source(sources, args.world, args.slot)
    print(f"[palx] opening: {source.display_name} ({source.world_id})")
    adapter = make_adapter(catalog, root)
    session = SaveSession.open_storage(source, adapter)
    try:
        players = list(session.manager.get_players())
        if not players:
            raise SystemExit("error: no players found in this save")
        if args.player_name:
            matches = [p for p in players if p.NickName == args.player_name]
            if not matches:
                names = ", ".join(sorted({str(p.NickName) for p in players}))
                raise SystemExit(f"error: player not found. known players: {names}")
            player = matches[0]
        else:
            player = players[0]
        print(f"[palx] player: {player.NickName} ({player.PlayerUId})")

        edits = []
        if args.level is not None:
            actual = apply_edit(
                session,
                player,
                "Level",
                lambda: setattr(player, "Level", args.level),
                {"player": str(player.PlayerUId)},
            )
            edits.append(("Level", actual))
        if args.tech_points is not None:
            actual = apply_edit(
                session,
                player,
                "TechnologyPoint",
                lambda: setattr(player, "TechnologyPoint", args.tech_points),
                {"player": str(player.PlayerUId)},
            )
            edits.append(("TechnologyPoint", actual))
        if args.nickname:
            actual = apply_edit(
                session,
                player,
                "NickName",
                lambda: setattr(player, "NickName", args.nickname),
                {"player": str(player.PlayerUId)},
            )
            edits.append(("NickName", actual))

        if not edits:
            raise SystemExit("error: nothing to edit (use --level/--tech-points/--nickname)")
        requested = {
            "Level": args.level,
            "TechnologyPoint": args.tech_points,
            "NickName": args.nickname,
        }
        mismatches = [
            {"field": f, "requested": requested[f], "actual": actual}
            for f, actual in edits
            if requested[f] is not None and actual != requested[f]
        ]

        changed_files = set()
        for field, _ in edits:
            if field == "TechnologyPoint":
                changed_files.add(f"Players/{UUID2HexStr(player.PlayerUId)}.sav")
            else:
                changed_files.add("Level.sav")

        if not args.write:
            # Default: export an edited COPY of the save (original untouched).
            # Always include Level.sav so the export remains a standalone,
            # reopenable save (player-only edits would otherwise be orphaned).
            export_files = sorted(changed_files | {"Level.sav"})
            base_dir = Path(args.out) if args.out else APP_DIR / "palx_exports"
            out_dir = base_dir / (
                datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                + f"_{(source.world_id or 'world')[:8]}"
            )
            out_dir.mkdir(parents=True, exist_ok=True)
            SaveWriter()._serialize_to_staging(session, out_dir, export_files)
            manifest = {
                "created_at": datetime.datetime.now().astimezone().isoformat(),
                "source_world": source.world_id,
                "source_display": source.display_name,
                "player": str(player.PlayerUId),
                "edits": {k: v for k, v in edits},
                "files": [],
                "note": "export copy; original XGP save was NOT modified",
            }
            for rel in export_files:
                data = (out_dir / rel).read_bytes()
                manifest["files"].append(
                    {
                        "path": rel,
                        "size": len(data),
                        "sha256": hashlib.sha256(data).hexdigest(),
                        "updated_at": datetime.datetime.fromtimestamp(
                            (out_dir / rel).stat().st_mtime
                        ).isoformat(),
                    }
                )
            (out_dir / "palx_manifest.json").write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            print(
                json.dumps(
                    {
                        "ok": True,
                        "mode": "export-copy",
                        "warnings": mismatches or None,
                        "export_dir": str(out_dir),
                        "world": source.world_id,
                        "player": str(player.PlayerUId),
                        "edits": {k: v for k, v in edits},
                        "files": export_files,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
        else:
            # Direct in-place write: double confirmation required.
            if not args.yes:
                print(
                    f"WARNING: this will OVERWRITE the original XGP save: "
                    f"{source.display_name} ({source.world_id})"
                )
                print(f"Planned edits: {dict(edits)}")
                a = input("Confirm overwrite [type YES]: ").strip()
                b = input("Second confirmation [type YES]: ").strip()
                if a != "YES" or b != "YES":
                    raise SystemExit("aborted: not confirmed (original save untouched)")
            print("[palx] committing with verified backup ...")
            result = SaveWriter().save(session, None, session.revision)
            print(
                json.dumps(
                    {
                        "ok": True,
                        "mode": "in-place",
                        "warnings": mismatches or None,
                        "world": source.world_id,
                        "player": str(player.PlayerUId),
                        "edits": {k: v for k, v in edits},
                        "backup": result.backup_path,
                        "written_files": list(result.written_files),
                        "cloud_sync_verified": result.cloud_sync_verified,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
    finally:
        session.close()


def main() -> None:
    # Force UTF-8 stdout/stderr so emoji / CJK names survive any console codepage.
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")
    if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
        sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(
        prog="palx",
        description="Fully automatic Palworld XGP save editor (level / tech points / nickname)",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--root",
        default=str(default_wgs_root()),
        help="XGP wgs directory (default: auto-detect Palworld package)",
    )

    p_list = sub.add_parser("list", help="list XGP worlds and slots", parents=[common])
    p_list.set_defaults(func=cmd_list)

    p_info = sub.add_parser(
        "info",
        help="read-only details of a world (players / overview / guilds)",
        parents=[common],
    )
    p_info.add_argument("--world", help="world id prefix (first hex chars), default: latest")
    p_info.add_argument("--slot", choices=["main", "1", "2", "3"], default="main")
    p_info.add_argument("--player-name", help="filter to a single player nickname")
    p_info.set_defaults(func=cmd_info)

    p_edit = sub.add_parser("edit", help="edit a save automatically", parents=[common])
    p_edit.add_argument("--world", help="world id prefix (first hex chars), default: latest")
    p_edit.add_argument("--slot", choices=["main", "1", "2", "3"], default="main")
    p_edit.add_argument("--player-name", help="player nickname (default: first player)")
    p_edit.add_argument("--level", type=int, help="set player level (1-80)")
    p_edit.add_argument("--tech-points", type=int, help="set technology points")
    p_edit.add_argument("--nickname", help="set player nickname")
    p_edit.add_argument(
        "--write",
        action="store_true",
        help="write changes into the ORIGINAL XGP save (requires double confirmation)",
    )
    p_edit.add_argument(
        "--yes",
        action="store_true",
        help="skip interactive double confirmation for --write (automation)",
    )
    p_edit.add_argument(
        "--out",
        help="export directory for copy mode (default: ./palx_exports/<timestamp>)",
    )
    p_edit.set_defaults(func=cmd_edit)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
