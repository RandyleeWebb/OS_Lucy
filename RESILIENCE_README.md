Resilience MVP (local Docker Compose)

Overview
 - Adds a lightweight CircuitBreaker, self-test runner, and a BattleMaster controller to perform simple chaos actions against services in a Docker Compose environment.

How to run
 - Ensure Docker and docker compose are installed and accessible via 'docker compose'.
 - From the repository root run: docker compose up --build
 - The orchestrator service exposes new endpoints:
   - GET /resilience/score -> returns a simple score based on circuit states
   - GET /resilience/selftest -> runs synthetic checks and returns a report
   - POST /resilience/chaos {action: 'kill'|'start'|'restart'|'latency', service: '<service>'}

Notes
 - The BattleMaster uses 'docker compose stop/start' to simulate service kills and restarts. It does not inject network latency; that will be added later via Toxiproxy.
 - All components are intentionally minimal for the MVP and intended to be extended and mapped to Kubernetes later.
