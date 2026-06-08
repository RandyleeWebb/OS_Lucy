// src/security/sandbox_profiles.ts
// Wasmtime sandbox profile definitions for Lucy AI‑DJ agents

export type SandboxProfile = {
  name: string;
  allowFs: boolean;
  allowNetwork: boolean;
  readOnly: boolean;
  description: string;
};

export const Profiles: Record<string, SandboxProfile> = {
  default: {
    name: "default",
    allowFs: true,
    allowNetwork: true,
    readOnly: false,
    description: "Full access – used for trusted internal tools",
  },
  no_fs: {
    name: "no_fs",
    allowFs: false,
    allowNetwork: true,
    readOnly: false,
    description: "Block all filesystem access – useful for pure computation",
  },
  no_network: {
    name: "no_network",
    allowFs: true,
    allowNetwork: false,
    readOnly: false,
    description: "Disable outbound network – safe for local data processing",
  },
  read_only: {
    name: "read_only",
    allowFs: true,
    allowNetwork: false,
    readOnly: true,
    description: "Filesystem read‑only – agents can read but not write",
  },
  full_sandbox: {
    name: "full_sandbox",
    allowFs: false,
    allowNetwork: false,
    readOnly: true,
    description: "Maximum isolation – no FS or network, read‑only mode",
  },
};
