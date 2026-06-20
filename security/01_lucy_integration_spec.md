# Aegis-Pandora Integration Specification (v1.0)

## 1. Overview

This specification defines the integration architecture for the Aegis-Pandora security fabric within both the bare-metal **LucyOS** microkernel environment and the **LucyVerse** virtual desktop environment (running on Windows/Linux host OS).

The architecture unifies the eBPF network interception, microVM containment, and generative deception features into a singular Security Subsystem, orchestrated by the Agent Ecosystem (Emma, Sentinel, Lucy).

---

## 2. Security Layers

### 2.1 Host OS / Hypervisor Layer

- **In LucyOS (Bare Metal):** The LucyKernel (MMU, IPC) serves as the hypervisor boundary. The eBPF equivalent (Parallel Door) attaches directly to the LucyOS Network Stack.
- **In LucyVerse (Virtual Desktop):** The underlying Windows or Linux Host OS provides the hardware abstraction.

### 2.2 Aegis-Pandora Security Fabric

This layer operates as the deeply integrated active defense mechanism:

- **Parallel Door (eBPF):** XDP/tc hooks that intercept inbound network traffic, cloning or redirecting suspicious flows seamlessly before they hit actual production servers.
- **Pandora's Box (MicroVMs):** Firecracker-based (or Hyper-V/KVM) jails to execute untrusted agents, plugins, external scripts, and quarantined sessions.
- **PhantomFS-v2:** A split-view, copy-on-write deceptive file system mounted within the microVMs. It presents fake directories and honeyfiles to attackers while alerting the system of their actions.
- **Infinite Maze:** The transport-layer (TCP Zero-Window) and protocol-layer (Endlessh, recursive folders) tarpits that trap and exhaust adversarial actors.

### 2.3 LucyOS / LucyVerse Runtime

- **Capability Manager:** A strict authorization broker positioned between the Agent Bus and the Security Fabric. It enforces Identity + Role + Capability mappings. It ensures that agents can only invoke Security APIs they are explicitly authorized for.
- **Security Fabric Service (Rust Daemon):** A background service acting as the centralized Security Subsystem API. It orchestrates the eBPF maps, spawns microVM instances, and handles the PhantomFS overlays.
- **Agent Bus:** The central message bus for all inter-agent and system communication, passing structured events and telemetry.

### 2.4 Agent Ecosystem & Capability Matrix

- **Emma (Governance):**
  - **Allowed:** Approve policy changes, escalate security posture.
  - **Task:** Owns policy decisions (allow, sandbox, tarpit, observe).
- **Sentinel (Security):**
  - **Allowed:** Report events, request containment.
  - **Not Allowed:** Change governance rules.
  - **Task:** Analyzes telemetry from the Security Fabric, scores threat risks, and requests actions from Emma.
- **Lucy (User-Facing):**
  - **Allowed:** `QueryStatus`, request overview decisions.
  - **Not Allowed:** Spawn Pandora VMs, modify policies.
  - **Task:** Receives high-level human-readable summaries (e.g., "A malicious scanner was trapped.") but does not directly control raw security internals.

---

## 3. Data Flows

### 3.1 Inbound Network Traffic

1. **Interceptor:** Traffic hits the Parallel Door (eBPF).
2. **Evaluation:** Traffic is evaluated against known Sentinel policies and behavioral heuristics.
3. **Routing:**
   - _Legitimate:_ Passes to normal LucyOS/LucyVerse network stack.
   - _Hostile/Suspicious:_ Redirected into a Pandora microVM (Deceptive Environment).

### 3.2 Untrusted Code Execution

1. Whenever a new, unverified plugin, script, or external AI agent requests execution.
2. The Security Subsystem intercepts the request.
3. The process is spawned inside a hardened **Pandora microVM** with **PhantomFS** mounted.
4. If it misbehaves, it only affects the deceptive environment.

### 3.3 Hostile Behavior & Containment

1. If a session inside Pandora's Box attempts horizontal pivoting or massive scanning.
2. Sentinel detects the behavior via PhantomFS telemetry.
3. Emma authorizes containment.
4. The connection is switched to the **Infinite Maze** (TCP zero-window tarpit, endless SSH banners, or recursive folder mazes).

### 3.4 Telemetry & Observability

1. **Harvester** collects events from PhantomFS, Parallel Door, and the Generative Deception Engine.
2. Events flow through the **Agent Bus** to **Sentinel** and **Emma**.
3. **Lucy** subscribes to summary events to update the human user seamlessly via the UX.

---

## 4. APIs

The Security Fabric exposes a unified API strictly accessible via the Agent Bus and enforced by the Capability Manager. No agent talks directly to Aegis-Pandora bypassing this layer.

### 4.1 `Security.Decide(action)`

Called by the system or explicitly authorized agents to evaluate an orchestration request (e.g., an inbound connection, untrusted code execution, or policy escalation). Evaluates capability and identity context, and Emma provides the final verdict.

- **Inputs:** `agent_id/session_id`, `source_ip/intent`, `payload_fingerprint`, `requested_resource_or_action`
- **Output:**
  - `allow`: Proceed normally.
  - `quarantine`: Route to a Pandora microVM.
  - `maze`: Route immediately to an Infinite Maze tarpit.
  - `deny`: Action is unauthorized based on Capability mappings.

### 4.2 `Security.Report(event)`

Called by the Aegis-Pandora fabric to emit structured telemetry into the Agent Bus.

- **Inputs:** `event_type` (e.g., `FS_VIOLATION`, `NETWORK_SCAN`), `timestamp`, `session_id`, `raw_data`
- **Action:** Sentinel consumes these events for correlation and alerting.

### 4.3 `Security.QueryStatus()`

Called by Lucy or the Desktop Shell to provide the human user with a dashboard view of the system's security posture.

- **Inputs:** `time_range`, `threat_level`
- **Output:** Human-readable state summaries (e.g., active quarantined microVMs, number of trapped connections).

---

## 5. LucyOS Binding (Bare Metal)

Attach points in the existing LucyOS spec:

- **Security & Isolation Subsystem:** Aegis-Pandora becomes the active defense engine behind this subsystem.
  _The Security Subsystem integrates the Aegis-Pandora fabric as its active defense engine, using eBPF-style interception, microVM containment, and deceptive filesystems to isolate and study untrusted actors._
- **Networking User-Space Server:** Parallel Door hooks into the LucyOS TCP/IP stack as the first stage for inbound flows.
- **AI Integration Layer:** Sentinel and Emma run as privileged agents with direct access to Security APIs via the Agent Bus.
- **LFS / Filesystem:** PhantomFS-style deceptive FS is only mounted inside Pandora microVMs, never in the main LFS path.

---

## 6. LucyVerse Binding (Virtual Desktop)

For LucyVerse on top of Windows/Linux:

- **Security Fabric Service (Rust daemon):**
  - Runs Aegis-Pandora as a local system service.
  - Exposes the same `Security.*` APIs over a local IPC channel (gRPC/WebSocket).
- **LucyVerse Runtime:**
  - Treats the Security Fabric as its "Security Subsystem."
  - All untrusted tools, external AI agents, and remote sessions go through `Security.Decide` before execution.
  - _In LucyVerse, the Aegis-Pandora Security Fabric runs as a privileged host-level service, while LucyVerse itself consumes its APIs as a client, preserving the same logical architecture as LucyOS but without owning the kernel._
- **Agent Bus:**
  - Same pattern: Aegis-Pandora only talks to agents via `Security.Report` events.
