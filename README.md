# Lucy OS — Local AI Workspace (production-ready)

Purpose
-------

Lucy OS is a lightweight, local AI workspace that safely combines a sandboxed cloud browser with a trusted local mirror (Electron + Next.js) and a local toolbelt for deterministic automation, multimodal execution, and live observability. This repository focuses on a secure, local-first architecture: MirrorPanel UI, IPC bridge, toolbelt API (safe stubs + governance), structured logs, and deployment helpers.

Guiding principles
------------------

- Keep OS integrations opt-in and auditable (FEATURE_OS_INTEGRATION)
- Log every action as structured JSON with a DecisionToken
- Prefer IPC via Electron preload; HTTP fallback only for dev
- Bind production services to localhost by default

Repository layout
-----------------

- src/toolbelt — FastAPI local toolbelt (cursor, keyboard, Spotify, TE v2 stub, governance)
- src/frontend — Next.js renderer, MirrorPanel component, static fallback UI
- src/electron_app — Electron main + preload exposing window.electron.toolbeltCall
- src/logs — runtime logs (toolbelt_actions.log)
- docker-compose.ui.yml — compose for local UI + toolbelt + electron smoke run
- docs/ — integration notes and supporting docs

Environment variables
---------------------

- TOOLBELT_LOG_DIR — override toolbelt log directory (optional)
- FEATURE_OS_INTEGRATION — set to 1/true to enable native OS automation (opt-in)
- PORT — frontend port (default 3000)

Quickstart — development
-------------------------

1) Start the toolbelt (FastAPI)

   cd src/toolbelt
   python -m pip install -r requirements-dev.txt
   python server.py

   Toolbelt: <http://localhost:8001> (logs at src/logs/toolbelt_actions.log)

2) Start the Next.js renderer (dev)

   cd src/frontend
   npm install
   npm run dev

   Open <http://localhost:3000> — MirrorPanel is mounted on the root page.

3) Optional: Run Electron for IPC testing

   cd src/electron_app
   npm install
   npm start

   Electron loads the renderer and the renderer uses window.electron.toolbeltCall for IPC.

Containerized quick smoke
------------------------

docker compose -f docker-compose.ui.yml up --build

This starts toolbelt and frontend (plus an electron stub for smoke). For UI, run Electron locally.

Stable API reference
--------------------

- GET /health — service health
- GET /governance/status — feature flags / opt-in status
- POST /cursor/move — move cursor (stubbed when FEATURE_OS_INTEGRATION=0)
- POST /cursor/click — click (stubbed)
- POST /keyboard/type — type text (stubbed)
- POST /spotify/control — media control (stubbed)
- POST /te_v2/execute — TE v2 generator stub
- POST /mirror/register — register mirrored browser instance

Logging & DecisionTokens
------------------------

Toolbelt logs single-line JSON entries (JSONL) to toolbelt_actions.log. Each action includes a decision_token (UUID) for traceability. Before production, replace UUIDs with signed DecisionTokens (Ed25519/JWKS) and store keys securely.

Security & governance
---------------------

- FEATURE_OS_INTEGRATION is disabled by default; enable only after auditing native automation and obtaining user consent.
- Restrict the toolbelt API to localhost in production and prefer IPC (preload) for renderer interactions.
- Add authentication/capability checks for multi-user scenarios.

Testing & CI
------------

Run unit tests:

  pip install pytest
  pytest -q

In CI: run Python tests, JS lint/build, and inject signing keys via CI secrets (never commit private keys).

Including README images you uploaded locally
-----------------------------------------

You referenced a local JPEG at:

  C:\\Users\\Randy Webb\\Desktop\\Os_lucy\\OS_Lucy's\\os_lucy's readme jpeg.jpeg

To include it in this repository README:

1) Copy the file into the repo under docs/images with a safe filename (no spaces):

   mkdir -p docs/images
   copy "C:\\Users\\Randy Webb\\Desktop\\Os_lucy\\OS_Lucy's\\os_lucy's readme jpeg.jpeg" docs/images/os_lucys_readme.jpeg

2) Commit and push the file. The README references docs/images/os_lucys_readme.jpeg and will display it on GitHub once pushed.

Example README image (place file at docs/images/os_lucys_readme.jpeg):

![Lucy OS screenshot](docs/images/os_lucys_readme.jpeg)

Roadmap & next steps
--------------------

- Implement signed DecisionTokens (Ed25519 + JWKS) and integrate trust registry
- Replace TE v2 stub with gated multimodal generator and ResultReceipt signing
- Add optional OS integrations (pyautogui) behind explicit opt-in and consent UI
- Add production log rotation and secure storage for audit logs

Production upgrades implemented
------------------------------

This repository now includes a focused production upgrade:

1) Signed DecisionTokens (Ed25519 + JWKS scaffold)
   - Dev Ed25519 keys auto-generated under src/toolbelt/keys (dev only). In production mount keys via TOOLBELT_PRIV_KEY/TOOLBELT_PUB_RAW or inject via CI secrets.
   - JWKS endpoint: GET /.well-known/jwks.json returns a minimal OKP/Ed25519 JWK for the public key.
   - Each toolbelt call returns decision_token and decision_signature (base64). The server also logs the decision_token and signed flag.

2) Consent UI + FEATURE_OS_INTEGRATION flow
   - Renderer includes a consent modal (src/frontend/components/ConsentModal.jsx). Consent is stored via Electron in a JSON file (~/.lucy_consent.json by default) and written by the Electron main process.
   - Toolbelt checks both FEATURE_OS_INTEGRATION env var and the consent file (path via LUCY_CONSENT_PATH) before allowing native integrations.

3) Production-ready frontend Docker
   - New multi-stage Dockerfile: src/frontend/Dockerfile.prod builds Next.js and produces a production image. docker-compose.ui.yml updated to use this Dockerfile for frontend service.

4) CI (GitHub Actions)
   - .github/workflows/ci.yml runs toolbelt pytest, Next.js build, and a lightweight electron check on push/PR to main.

5) Consistent decision_token type
   - All decision_tokens are UUID4 strings. Update integrations to generate parseable tokens. Toolbelt enforces UUID format and rejects malformed tokens.

6) Enhanced health check
   - GET /health now returns { up: true, version, id } fields. Includes simple DB and JWKS availability checks.

7) UI performance improvements
   - React memoization and useCallback optimizations in the renderer. Reduced re-renders and improved input latency.

8) README images
   - Local image references were removed. Add images to the docs/images directory and reference them as needed.

How to use the JWKS and keys
---------------------------

- For local dev the server auto-generates a dev keypair and serves a minimal JWKS at <http://localhost:8001/.well-known/jwks.json>
- For production:
  - Generate and store an Ed25519 private key (PEM PKCS8) externally.
  - Set TOOLBELT_PRIV_KEY to the absolute path of the private key on the deployment host.
  - Set TOOLBELT_PUB_RAW to the raw public key bytes path (or keep the generated one and expose via JWKS).

Consent storage
---------------

- Default consent file path is the user's home folder: ~/.lucy_consent.json
- Override path via LUCY_CONSENT_PATH environment variable (used by toolbelt to check consent).

Signature verification endpoint
-----------------------------

- POST /verify accepts JSON { decision_token, decision_signature } and returns { valid: true/false } for debugging and governance tooling. Use this to validate JWT/JWS signatures emitted by the toolbelt.

JWT DecisionTokens
-------------------

- DecisionTokens are now wrapped in a compact JWS (EdDSA) using the Ed25519 keypair. For backward compatibility the raw base64 signature is appended after a '::' separator. Verifiers should first attempt to verify the JWS and fall back to the raw signature if needed.

System Status panel
-------------------

- The renderer now includes a System Status panel showing toolbelt health, JWKS key count, consent status, FEATURE_OS_INTEGRATION status, and the last 5 log entries. It's at the right side of the MirrorPanel page.

Log rotation
------------

- Toolbelt log files are rotated via RotatingFileHandler: 5MB per file, 5 backups. Adjust LOG_DIR or handler parameters via environment in production.

Unified config loader
---------------------

- A shared config module (src/shared/config.py) exposes env, consent path, and helpers. Electron and the toolbelt use this module for consistent configuration.

CI caching
----------

- GitHub Actions now cache Python pip and Node/npm dependencies to speed CI runs. See .github/workflows/ci.yml for details.

License & support
-----------------

Add your LICENSE file. For issues, open an issue or contact the maintainer.
