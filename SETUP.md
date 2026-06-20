# Civil Unrest — Production Setup Guide
**Lucy-Core-A.I. | Standalone Gang Framework for FiveM**

---

## Quick Start

### 1. License Key
Open `Lucy's server/server.cfg` and replace the `sv_licenseKey` value with your own key from:
**https://keymaster.fivem.net**

### 2. Folder Layout
Place the files so your server looks like this:

```
FXServer/
├── FXServer.exe              ← original binary from your zip
├── citizen/                  ← original from your zip
├── components.json           ← original from your zip
├── [all DLLs]                ← original from your zip
└── Lucy's server/
    ├── server.cfg            ← FIXED (from this build)
    └── resources/
        └── civil_unrest/     ← FIXED + NEW (from this build)
            ├── fxmanifest.lua
            ├── shared/config.lua
            ├── client/
            ├── server/
            └── ui/
```

The `civil_unrest` folder goes directly inside `resources/` — **not** inside a subfolder like `[test]`.

### 3. Start the Server (Windows)
```
FXServer.exe +exec "Lucy's server/server.cfg"
```

---

## Optional: AI NPC Dialogue (Gemini)

The server works fully without this — it uses built-in fallback dialogue automatically.

To enable live AI-generated NPC speech:
1. Get a free key at **https://aistudio.google.com/app/apikey**
2. In `server.cfg`, change:
   ```
   set gemini_api_key ""
   ```
   to:
   ```
   set gemini_api_key "YOUR_KEY_HERE"
   ```

---

## Admin Setup

To give yourself admin access, add your FiveM ID to `server.cfg`:

```
add_principal identifier.fivem:YOUR_FIVEM_ID group.admin
```

Find your FiveM ID at **https://forum.cfx.re** (shown in your profile URL).

Admin commands in-game:
- `setepoch <MODE>` — force switch the epoch (TOTAL_WAR, ASYLUM, NEON_NIGHTS, SYNDICATE, CHRONO_LOCK)
- `agi_override` — trigger an AGI-OS system event

---

## Gameplay Reference

### Controls
| Key | Action |
|-----|--------|
| `E` | Interact with nearby NPC or vehicle |
| `F1` | Open Civil Unrest interaction menu |
| `Escape` | Close any open menu |

### Street Credit Tiers
| Tier | Required Credit |
|------|----------------|
| Novice | 0 |
| Hustler | 1,500 |
| Kingpin | 10,000 |

### Epochs (Auto-Scheduled by Day)
| Day | Epoch |
|-----|-------|
| Sunday | ASYLUM (zombie outbreak, toxic smog) |
| Monday | SYNDICATE (corporate RP, stock takeovers) |
| Tuesday | TOTAL_WAR (gang territory control) |
| Wednesday | SYNDICATE |
| Thursday | NEON_NIGHTS (2077 cyberware, night mode) |
| Friday | CHRONO_LOCK (time fissure events) |
| Saturday | TOTAL_WAR |

### Gang Factions (15 total)
Ballas · Families · Vagos · Lost MC · Marabunta Grande · Armenian Mob · Triads · Aztecas · Korean Mob · Madrazo Cartel · The Professionals · O'Neil Brothers · Altruist Cult · Merryweather · Hood Queen

---

## What Was Fixed (Production Changelog)

| File | Issue | Fix |
|------|-------|-----|
| `server.cfg` | Junk text `fluffy stuff` on line 61 caused parse crash | Removed |
| `server.cfg` | `loadingscreen_killer` missing `ensure` keyword | Fixed |
| `server.cfg` | 40+ `[test]` prototype resources loaded alongside finished `civil_unrest` resource | Removed; only `civil_unrest` loaded |
| `server/epoch.lua` | `setepoch` admin command used `streetCredit > 0` as permission check — any player could invoke it | Fixed to `IsPlayerAceAllowed()` |
| `shared/config.lua` | `RiotDayOfWeek = 6` comment said "Saturday" but Lua `os.date` wday 6 = Friday | Fixed to `7` (Saturday) |
| `shared/config.lua` | `DebugMode = true` left on from dev — floods server console | Set to `false` |
| `client/main.lua` | Never fired `civilUnrest:playerConnected` to server — all players had no data record, breaking credit, loyalty, economy | Added `onClientResourceStart` handler |
| `client/epoch_client.lua` | Duplicate `requestEpochSync` call (now handled in main.lua init) | Removed duplicate |
| `ui/index.html` | File missing entirely — resource would fail to load NUI | Created from scratch |
| `ui/style.css` | File missing entirely | Created from scratch |
| `ui/script.js` | File missing entirely — all NUI messages from Lua had no handler | Created with correct message types matching Lua code |
