# Lucy AI‑DJ – Phase 1 Foundations

This repository contains the source code for the Lucy virtual‑desktop AI‑DJ radio station.

## Project Structure (Phase 1)
```
ai_dj/
├─ src/          # Application source code (TS/TSX, Python helpers)
├─ config/       # Liquidsoap, Icecast, and other config files
├─ scripts/      # Utility scripts (setup, health‑check, backup)
├─ docker/       # Docker‑compose files for services
├─ docs/         # Design docs, diagrams, compliance info
├─ assets/       # Logos, UI assets, glass‑morphic CSS
├─ security/     # Rust security fabric crate and sandbox profiles
├─ agents/       # Planner, Builder, Research, Validator agents
└─ README.md     # This file
```

## Quick‑Start
1. Install **Docker Desktop** (Windows) and ensure `docker compose` works.
2. Install **VB‑Audio Virtual Cable (A+B)** and set the default playback device to `CABLE Input`. Enable *Listen to this device* → your speakers/headphones.
3. Initialise the Git repository:
   ```bash
   cd "d:/lucy ecosystem/OS_Lucy's/ai_dj"
   git init
   git add .
   git commit -m "Initial commit – Phase 1 scaffolding"
   ```
4. Run the setup script (to be added in Phase 2) which will install dependencies.

## Next Steps
- Implement the security fabric crate and sandbox profiles (Phase 2).
- Add Docker‑compose services for Navidrome, Icecast, etc.
- Begin development of the Conversational AI layer.
