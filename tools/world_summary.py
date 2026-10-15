"""One-line-per-world summary of every local XGP world (read-only)."""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

APP = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(APP))

from palx import discover_sources, make_adapter, default_wgs_root  # noqa: E402
from palworld_pal_editor.application.save_session import SaveSession  # noqa: E402
from palworld_pal_editor.application.query_service import SaveQueryService  # noqa: E402
from palworld_save_tools.palsav import decompress_sav_to_gvas  # noqa: E402
from palworld_save_tools.gvas import GvasFile  # noqa: E402
from palworld_save_tools.paltypes import PALWORLD_TYPE_HINTS  # noqa: E402


def main() -> None:
    logging.disable(logging.INFO)
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")
    root = default_wgs_root()
    catalog, sources = discover_sources(root)
    adapter = make_adapter(catalog, root)
    seen: set[str] = set()
    rows: list[tuple[object, str]] = []
    for s in sources:
        wid = (s.world_id or "").split("-Slot")[0]
        if wid in seen:
            continue
        seen.add(wid)
        session = SaveSession.open_storage(s, adapter)
        try:
            meta = Path(session._opened.workspace) / "LevelMeta.sav"
            data, _ = decompress_sav_to_gvas(meta.read_bytes())
            gvas = GvasFile.read(data, PALWORLD_TYPE_HINTS, {})
            world_name = (
                gvas.properties["SaveData"]["value"]["WorldName"]["value"]
            )
            qs = SaveQueryService(session)
            ov = qs.overview()
            players = qs.players(sort_by="level", descending=True)
            totals = ov["totals"]
            traits = ov["traits"]
            ps = ", ".join(
                f"{p['name']}(Lv{p['level']}, pals {p['pal_count']})"
                for p in players
            )
            ts = gvas.properties.get("Timestamp", {}).get("value")
            rows.append((ts, f"{wid[:8]} [{world_name}] players: {ps}"
                f" | pals {totals['pals']} / species {totals['species']}"
                f" / boss {traits['boss_pals']} / rare {traits['rare_pals']}"
                f" / bases {totals['bases']} / workers {totals['base_workers']}"))
        finally:
            session.close()
    rows.sort(key=lambda r: r[0] or 0, reverse=True)
    for _ts, line in rows:
        print(line)


if __name__ == "__main__":
    main()
