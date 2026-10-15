import json
import sys
from pathlib import Path

APP = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(APP))

from palworld_save_tools.gvas import GvasFile
from palworld_save_tools.palsav import decompress_sav_to_gvas
from palworld_save_tools.paltypes import PALWORLD_TYPE_HINTS

path = Path(sys.argv[1])
raw, _ = decompress_sav_to_gvas(path.read_bytes())
g = GvasFile.read(raw, PALWORLD_TYPE_HINTS, [])
chars = g.properties["worldSaveData"]["value"]["CharacterSaveParameterMap"]["value"]
print(json.dumps(chars[0], default=str)[:1500])
