# PalworldXGP-Editor

[中文](#中文) | [English](#english)

---

## 中文

全自动的《幻兽帕鲁》Xbox Game Pass（XGP）存档命令行修改器（Python）。

### 功能

- 自动定位本机 XGP 存档（WGS 容器），无需手动找路径
- `list`：列出全部世界与存档槽位
- `info`：只读查看世界详情（游戏内世界名称、玩家、总览、公会）
- `edit`：修改玩家等级（1-80）、科技点、昵称
- 支持 Palworld 1.0 存档格式（含 Oodle `PlM` 与 zlib `PlZ` 压缩）

### 安全设计

- **默认导出副本**：修改写入 `palx_exports\<时间戳>_<世界ID>\`，原档不动；副本含
  `palx_manifest.json`（导出时间、来源、编辑项、文件 sha256）
- **`--write` 直写原档**：需连续两次输入 `YES` 确认；写回前自动创建已验证备份
  （`palx_wgs_backups\`），事务式写回 + 重开校验
- 游戏运行中拒绝写入，防止存档损坏
- 等级强制 1-80（游戏满级 80）
- **降级保护**：游戏机制限制，玩家等级无法直接降低（点数不足会被拒绝）。
  输出中的 `warnings` 字段会标明"请求值"与"实际生效值"不一致的情况

### 用法

```cmd
:: 列出世界
palx list

:: 只读查看最新世界的详细信息（世界名 / 玩家 / 公会 / 帕鲁总览）
palx info
palx info --world DBDEFB6B --slot main

:: 导出修改副本（安全，默认）
palx edit --level 80 --tech-points 9999
palx edit --world DBDEFB6B --slot 1 --nickname 新名字 --out D:\exports

:: 直写原档（双确认）
palx edit --level 80 --tech-points 9999 --write

:: 自动化跳过交互确认
palx edit --level 80 --write --yes

:: 给玩家放物品（默认导出副本）
palx item --item AIcore --count 999 --world AFACF0A3
```

参数说明：

- `--world <前缀>`：世界 ID 前 8 位十六进制即可
- `--slot main|1|2|3`：存档槽位（默认 main）
- `--player-name <昵称>`：多玩家时指定目标（默认第一个玩家）
- `--level / --tech-points / --nickname`：要修改的字段，可同时使用
- `--item <物品ID>`、`--count <数量>`、`--container-slot <槽位>`：`item` 子命令参数，
  用于向玩家通用仓库放物品（默认第一个空槽，数量 1-999999）
- `--root <路径>`：手动指定 wgs 目录（默认自动检测）

### 输出说明

- 全部 JSON 输出强制 UTF-8，含中文/Emoji 的昵称不会乱码
- 导出副本始终包含 `Level.sav` + 玩家存档，可直接被游戏/工具重新打开
- 导出副本附 `palx_manifest.json`（编辑项、文件 sha256），可用
  `python tools/verify_export.py <导出目录>` 校验

### 目录结构

```
PalworldXGP-Editor/
├── palx.py              主程序
├── start.cmd            Windows 入口
├── ooz.pyd              Oodle 解压依赖
├── palworld_pal_editor/ 内核（GPL-3.0，见 LICENSE-THIRDPARTY.md）
├── palworld_save_tools/
├── tools/                 辅助工具（汇总、最新存档详情、导出校验）
├── palx_exports/           默认导出副本目录
├── palx_wgs_backups/       直写前的自动备份
└── palx_wgs_workspaces/    临时工作区（可删）
```

### 运行要求

- Windows 10/11 + Python 3.10+（CLI 无需额外 pip 依赖）
- 修改前请完全关闭游戏
- Xbox 云同步：`--write` 写回后建议启动游戏确认云同步状态

### 第三方版权

内核改自 xyuqikzz/Palworld-Save-Editor 与 KrisCris/Palworld-Pal-Editor（GPL-3.0）、
cheahjs/palworld-save-tools（MIT），详见 `LICENSE-THIRDPARTY.md`。本程序按 GPL-3.0 分发。

---

## English

A fully automatic command-line save editor for Palworld on Xbox Game Pass (XGP), written in Python.

### Features

- Automatically locates your local XGP saves (WGS containers) — no manual path hunting
- `list`: list all worlds and save slots
- `info`: read-only world details (in-game world name, players, overview, guilds)
- `edit`: modify player level (1-80), technology points, and nickname
- Supports the Palworld 1.0 save format (Oodle `PlM` and zlib `PlZ` compression)

### Safety design

- **Export-copy by default**: edits are written to `palx_exports\<timestamp>_<worldID>\`
  and the original save is never touched; each copy includes a `palx_manifest.json`
  (timestamp, source, edits, file sha256)
- **`--write` for in-place edits**: requires typing `YES` twice; a verified backup is
  created first (`palx_wgs_backups\`), followed by transactional write-back and re-open
  validation
- Refuses to write while the game is running (prevents save corruption)
- Level is clamped to 1-80 (game max level is 80)
- **Downgrade protection**: due to game mechanics, player level cannot be lowered
  directly (insufficient tech points will be rejected). The `warnings` field in the
  output flags any mismatch between requested and effective values

### Usage

```cmd
:: List worlds
palx list

:: Read-only details of the latest world (name / players / guilds / pal overview)
palx info
palx info --world DBDEFB6B --slot main

:: Export an edited copy (safe, default)
palx edit --level 80 --tech-points 9999
palx edit --world DBDEFB6B --slot 1 --nickname NewName --out D:\exports

:: In-place write (double confirmation)
palx edit --level 80 --tech-points 9999 --write

:: Skip interactive confirmation for automation
palx edit --level 80 --write --yes

:: Give items to a player's common container (default: export copy)
palx item --item AIcore --count 999 --world AFACF0A3
```

Options:

- `--world <prefix>`: first 8 hex chars of the world ID are enough
- `--slot main|1|2|3`: save slot (default: main)
- `--player-name <name>`: target a specific player (default: first player)
- `--level / --tech-points / --nickname`: fields to edit, can be combined
- `--item <id>`, `--count <n>`, `--container-slot <slot>`: `item` subcommand
  options for placing items into a player's common container (first free slot
  by default, count 1-999999)
- `--root <path>`: manual wgs directory (auto-detected by default)

### Output notes

- All JSON output is forced to UTF-8, so nicknames with CJK characters or emoji
  never break
- Exported copies always include `Level.sav` + player saves and can be reopened
  directly by the game or other tools
- Each export includes `palx_manifest.json` (edits, file sha256); verify it with
  `python tools/verify_export.py <export-dir>`

### Project layout

```
PalworldXGP-Editor/
├── palx.py              main CLI
├── start.cmd            Windows entry point
├── ooz.pyd              Oodle decompression dependency
├── palworld_pal_editor/ core library (GPL-3.0, see LICENSE-THIRDPARTY.md)
├── palworld_save_tools/
├── tools/                 helper tools (summary, latest save details, verification)
├── palx_exports/           default export-copy directory
├── palx_wgs_backups/       automatic backups before in-place writes
└── palx_wgs_workspaces/    temp workspaces (safe to delete)
```

### Requirements

- Windows 10/11 + Python 3.10+ (CLI needs no extra pip dependencies)
- Fully close the game before editing
- Xbox cloud sync: after `--write`, launch the game once to confirm cloud sync status

### Third-party licenses

The core is adapted from xyuqikzz/Palworld-Save-Editor and KrisCris/Palworld-Pal-Editor
(GPL-3.0) and cheahjs/palworld-save-tools (MIT). See `LICENSE-THIRDPARTY.md`.
This program is distributed under GPL-3.0.
