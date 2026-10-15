"""Verify exported save files by reopening them with the app's SaveManager.

Usage: verify_export.py <export-dir> ...
Each export dir should contain Level.sav and/or Players/*.sav.
"""
import shutil
import sys
import tempfile
from pathlib import Path

APP = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(APP))


def main() -> None:
    for arg in sys.argv[1:]:
        src = Path(arg)
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            for f in src.rglob("*"):
                if f.is_file() and f.name != "palx_manifest.json":
                    rel = f.relative_to(src)
                    dst = tmp / rel
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(f, dst)
            from palworld_pal_editor.core.save_manager import SaveManager

            mgr = SaveManager()
            if mgr.open(str(tmp)) is None:
                print(f"{src}: FAILED to open")
                continue
            for p in mgr.get_players():
                print(
                    f"{src.name}: player={p.NickName} Level={p.Level} "
                    f"TechnologyPoint={p.TechnologyPoint}"
                )


if __name__ == "__main__":
    main()
