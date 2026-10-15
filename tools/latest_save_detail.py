"""Detailed read-only report for one XGP world: python tools/latest_save_detail.py <wid-prefix>"""
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


def main() -> None:
    logging.disable(logging.INFO)
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")
    prefix = sys.argv[1] if len(sys.argv) > 1 else ""
    root = default_wgs_root()
    catalog, sources = discover_sources(root)
    adapter = make_adapter(catalog, root)
    for s in sources:
        wid = (s.world_id or "").split("-Slot")[0]
        if "-Slot" in (s.world_id or ""):
            continue  # only main slots
        if prefix and not wid.lower().startswith(prefix.lower()):
            continue
        session = SaveSession.open_storage(s, adapter)
        try:
            qs = SaveQueryService(session)
            ov = qs.overview()
            print(
                json.dumps(
                    {
                        "world": wid,
                        "totals": ov["totals"],
                        "traits": ov["traits"],
                        "condition": ov["condition"],
                        "expeditions": ov["expeditions"],
                        "top_species": ov["top_species"],
                        "players": ov["players"],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            for pal in qs.pals(sort_by="level", descending=True)[:20]:
                print(
                    json.dumps(
                        {
                            k: pal[k]
                            for k in (
                                "name",
                                "internal_id",
                                "level",
                                "gender",
                                "boss",
                                "rare",
                                "passive_skills",
                                "owner_player_id",
                                "container_state",
                            )
                            if k in pal
                        },
                        ensure_ascii=False,
                    )
                )
        finally:
            session.close()


if __name__ == "__main__":
    main()
