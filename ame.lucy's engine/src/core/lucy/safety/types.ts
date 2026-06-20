import { Json } from "../core/types";

export type PolicyAction = "allow" | "deny" | "ask";

export interface PermissionContext {
  pluginName: string;
  capability: string;
  action: string;
  payload?: Json;
}

export interface PermissionResult {
  granted: boolean;
  action: PolicyAction;
  reason?: string;
}

export interface SafetyPolicy {
  id: string;
  description: string;
  targetPlugin?: string; // Optional: only apply to specific plugin
  targetAction?: string; // Optional: only apply to specific action
  evaluate: (ctx: PermissionContext) => PermissionResult | null; // Returns null if policy doesn't apply
}
