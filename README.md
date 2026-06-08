# Lucy — The Sovereign AI Orchestrator
<img width="850" height="507" alt="lucyos3" src="https://github.com/user-attachments/assets/94177923-5820-47d5-b415-fc361e0804cf" /><img width="980" height="653" alt="oslucy2" src="https://github.com/user-attachments/assets/2353b8b2-5216-44da-88df-c763277341c1" />
<img width="974" height="585" alt="oslucy" src="https://github.com/user-attachments/assets/9b08a50a-08cc-4a09-842b-1c7800ac97f7" />

![Sovereign-Ready](https://img.shields.io/badge/Sovereign--Ready-brightgreen)
![QC-Verified](https://img.shields.io/badge/QC--Verified-blue)
![Build Status](https://img.shields.io/badge/build-passing-brightgreen)
![Coverage](https://img.shields.io/badge/coverage-⚠️-yellow)
![Mutation Score](https://img.shields.io/badge/mutation--score-100%25-green)

Tagline: Bold orchestration for sovereign AI — cryptographically-verified, zero-trust, WASM-sandboxed execution.

---

🚀 Why Lucy exists

Lucy is an opinionated, open-source AI orchestration platform purpose-built to prove safe, auditable, and resilient execution for autonomous systems. It was created because modern AI systems need more than policies — they need provable enforcement.

If you care about audit logging, zero-trust enforcement, and cryptographic verification, Lucy is for you. Lucy is different because it enforces a strict cryptographic invariant across decisions, audit logs, and execution permits. That invariant is the core of sovereignty:

**DecisionToken → AuditReceipt → ExecutionPermit → Trusted Executor**

Every action is signed, chained, and verified. No execution may proceed without the entire cryptographic lineage.

---

✨ Highlights (hook + branding)

- High-assurance AI orchestration for production-grade distributed systems
- WASM sandboxing for untrusted policies and model-driven code
- Cryptographic verification across audit, permit, and execution planes
- Mutation testing and QC-of-QC to prevent silent regressions
- Resilience engineering primitives: circuit breakers, self-tests, chaos injection

Read on for diagrams, a quick demo, technical depth, and how to contribute.

---

🌐 Quick architecture (ASCII visual)
┌─────────────────────────────┐
│         Lucy OS             │
│ Voice • UI • Workflows      │
└──────────────┬──────────────┘
               │

┌──────────────▼──────────────┐
│        E.M.M.A Kernel       │
│ Agents • Governance         │
│ Recovery • Telemetry        │
└──────────────┬──────────────┘
               │
┌──────────────▼──────────────┐
│ Sovereign Execution Plane   │
│ Decision Tokens             │
│ Audit Receipts              │
│ Execution Permits           │
└──────────────┬──────────────┘
               │
┌──────────────▼──────────────┐
│ Trusted Executor            │
│ WASM • Sandbox              │
└─────────────────────────────┘
```
				+------------------+      DecisionToken      +-------------+
 Client/Agent → |    Orchestrator  | ─────────────────────────▶ | SafeGuard   |
 (authenticated) | (auth + control) |                           +-------------+
				 |                  |                                   |
				 |  create permit    | ◀────────AuditReceipt──────────────┘
				 |                  |                                   v
				 +------------------+        ExecutionPermit        +-------------+
												  +──────────────▶ | DataVault   |
																   +-------------+
																		|
																		v
																 +----------------+
																 | Trusted        |
																 | Executor (WASM)|
																 +----------------+
```

Architecture summary: Authenticated client → Orchestrator (auth + policy) → SafeGuard (DecisionToken) → DataVault (AuditReceipt) → Orchestrator (ExecutionPermit) → Trusted Executor (WASM sandbox).

---

📣 SEO-friendly summary ([@scottymicfree x][Randy Webb @scottymicfree linkedin](https://github.com/scottymicfree))

Lucy is an open-source sovereign AI orchestration system that implements zero-trust architecture, cryptographic verification, audit logging, WASM sandboxing, and mutation-tested QC pipelines. It is built for distributed systems, resilience engineering, and secure execution pipelines.

Keywords: AI orchestration, WASM sandboxing, secure execution pipeline, distributed systems, resilience engineering, audit logging, sovereign AI, zero-trust architecture, mutation testing, cryptographic verification.

---

💡 Why Lucy matters

Lucy gives you a provable control plane. Instead of trusting runtime behavior, you can cryptographically verify that enforcement steps ran in order and that no bypass was possible. This is essential for teams who must demonstrate compliance, auditability, or safety.

Lucy transforms policy enforcement into auditable evidence, not just runtime logs.

---

🔥 What makes Lucy unique

- Canonical JSON signing to prevent canonicalization attacks
- DecisionToken → AuditReceipt → ExecutionPermit invariant enforced end-to-end
- WASM-first sandbox: run untrusted policies without language lock-in
- QC-of-QC mutation testing ensures tests detect intentional bypass attempts
- Circuit breakers and chaos endpoints for hardened resilience engineering

---

👥 Who is Lucy for?

- Security engineers building provable AI systems
- Platform teams running model-driven automation at scale
- Researchers exploring sovereign AI and auditable autonomy
- Compliance teams who require strong evidence of enforcement

If you want a system you can prove, not just hope, Lucy was designed for you.

---

🎬 Show me something cool — quick demo

1) Start the dev stack (example minimal services):

```bash
docker-compose up -d datavault safeguard trusted-executor orchestrator
```

2) Issue a guarded execution (replace <TOKEN> with a valid token):

```bash
curl -X POST \
  -H "Authorization: Bearer service:dev" \
  -H "Content-Type: application/json" \
  -d '{"wasm_module":"<BASE64_WASM>", "agent_id":"test-agent"}' \
  http://localhost:8020/execute_wasm
```

3) Observe the chain:

- SafeGuard → DecisionToken (signed)
- DataVault → AuditReceipt (signed & chained)
- Orchestrator → ExecutionPermit (signed)
- Trusted Executor → verifies lineage and runs WASM in a sandbox

Share this demo: a single curl demonstrates the full cryptographic lineage.

---

🧠 Deep technical story (control-plane invariant)

Lucy’s invariant is the backbone of the system. The chain enforces custody and prevents unauthorized execution:

- DecisionToken (SafeGuard): policy engine produces a canonical-signed token describing the decision (allow/deny), reasoning, scores, and metadata.
- AuditReceipt (DataVault): append-only store computes payload hash, prev_hash, entry_hash, and returns a signed AuditReceipt bound to the ledger.
- ExecutionPermit (Orchestrator): a signed document over DecisionToken || AuditReceipt || nonce || ttl. This is the authorization artifact for execution.
- Trusted Executor: final gate that verifies orchestrator signature, embedded DecisionToken signature, embedded AuditReceipt signature, TTL, and nonce uniqueness before permitting WASM execution.

If any piece is invalid, execution is denied (403). This creates an immutable chain between policy, audit, and execution.

---

🔒 Cryptographic boundaries & canonical JSON

Canonical JSON protects the signature surface:

- Sorting keys deterministically (sort_keys=true)
- Using compact separators (separators=(",", ":"))
- UTF-8 encoding and no extra whitespace

By enforcing canonicalization, Lucy prevents field reordering, whitespace injection, or signature wrapping attacks. Tests verify that signature verification breaks on any deviation from canonical form.

---

🧪 QC, QC‑of‑QC, and mutation testing

Lucy’s test strategy is engineered for proof:

1. P0 verification suite: end-to-end assertions for DecisionToken → AuditReceipt → ExecutionPermit → Trusted Executor.
2. QC suite: extensive negative-path tests (tampering, unreachable services, canonicalization, replay, TTL, actor propagation).
3. QC-of-QC runner: git-based mutation tester that applies deterministic mutations (patches), runs QC, and fails the CI if any mutation escapes detection.

This staged approach ensures that if developers disable a signature, the CI fails. If they remove nonce checks, replay tests fail. QC-of-QC protects enforcement fidelity.

---

⚙️ Resilience engineering & distributed systems

Lucy is designed for real distributed deployments:

- Circuit breakers guard external dependencies (DataVault, SafeGuard, Trusted Executor)
- Selftest endpoints for health and canary checks
- Chaos endpoints for controlled fault injection

The platform integrates with Kubernetes and service mesh patterns and expects to be used in enterprise distributed systems.

---

🧭 Actor identity propagation

Auth is enforced at ingress with Bearer tokens. The orchestrator extracts actor identity and propagates it via request.state.actor to SafeGuard and DataVault. Actor identity is embedded in DecisionToken, AuditReceipt, and ExecutionPermit so every signed artifact carries context for forensic review.

---

📈 Roadmap & what’s next

- Asymmetric signatures (PKI, key rotation)
- Persistent nonce store (Redis) to support horizontal Trusted Executor instances
- WASM policy marketplace (plugins and validators)
- Formal verification of canonicalization and signing routines
- Improved dashboards and compliance reporting

---

🤝 Contribute & join the movement

Star this repo ⭐ — it helps Lucy surface to teams that need provable enforcement.

Contributions:

1. Fork the repo
2. Create a feature branch
3. Run tests & QC locally
4. Open a PR and reference QC-of-QC checks

We welcome contributions that improve cryptography, resilience, testing, and usability.

---

📢 Social snippets

Tweet-ready: "Lucy: cryptographically-verified AI orchestration with WASM sandboxing and mutation-tested guarantees. DecisionToken → AuditReceipt → ExecutionPermit → Trusted Executor. Sovereign AI, provable." #SovereignAI #WASM #AuditLogging

LinkedIn-ready blurb: "Lucy provides a provable control plane for AI orchestration — cryptographic audit receipts, signed permits, and WASM sandboxing backed by mutation-tested CI. If you need auditability for autonomous systems, Lucy is built for you."

---

⚠️ Callouts

> High-assurance systems deserve mutation-resistant CI: QC-of-QC applies deterministic patches and ensures tests catch any weakening of cryptographic boundaries.

> Lucy is designed to be auditable, provable, and verifiable — not merely plausible. If your team must show evidence to auditors or regulators, Lucy gives you the artifacts.

---

LICENSE

MIT — contributions welcome.

---

Credits: Built for resilience engineers, security teams, and platform builders who demand provable guarantees.
