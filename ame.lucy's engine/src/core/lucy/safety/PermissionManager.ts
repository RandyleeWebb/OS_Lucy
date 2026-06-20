import { PermissionContext, PermissionResult, SafetyPolicy } from "./types";
import { policyGravityLayer } from "./PolicyGravityLayer";

const GRAVITY_DENY_THRESHOLD = 0.85;

export class PermissionManager {
  private policies: SafetyPolicy[] = [];

  constructor() {
    this.loadDefaultPolicies();
  }

  private loadDefaultPolicies() {
    // 1. Block destructive process kills
    this.policies.push({
      id: "block_system_kill",
      description: "Prevents killing critical system processes",
      targetPlugin: "NativeProcessManager",
      targetAction: "kill",
      evaluate: (ctx) => {
        const payloadStr = JSON.stringify(ctx.payload || "");
        // Naive check for init/system pids or wildcard kills
        if (payloadStr.includes("PID 0") || payloadStr.includes("PID 1") || payloadStr.includes("*")) {
          return { granted: false, action: "deny", reason: "Cannot target system-critical PIDs or use wildcards." };
        }
        return null;
      }
    });

    // 2. Restrict spawn commands (No destructive file ops)
    this.policies.push({
      id: "restrict_destructive_spawn",
      description: "Blocks destructive shell commands",
      targetPlugin: "NativeProcessManager",
      targetAction: "spawn",
      evaluate: (ctx) => {
        const payloadStr = JSON.stringify(ctx.payload || "").toLowerCase();
        if (payloadStr.includes("rm -rf") || payloadStr.includes("del /f") || payloadStr.includes("format")) {
          return { granted: false, action: "deny", reason: "Destructive file operations are strictly prohibited." };
        }
        // Require explicit allow for spawns, so we don't return 'allow' here, just pass if not destructive
        return null; 
      }
    });

    // 3. Allow safe monitoring
    this.policies.push({
      id: "allow_monitoring",
      description: "Allows read-only system monitoring",
      targetAction: "monitor",
      evaluate: (ctx) => ({ granted: true, action: "allow" })
    });

    // 4. Allow safe file reads
    this.policies.push({
      id: "allow_file_read",
      description: "Allows reading files",
      targetAction: "read",
      evaluate: (ctx) => ({ granted: true, action: "allow" })
    });
  }

  addPolicy(policy: SafetyPolicy) {
    this.policies.push(policy);
  }

  evaluate(ctx: PermissionContext): PermissionResult {
    // --- 1. DYNAMIC GRAVITY CHECK (Policy Gravity Layer) ---
    const actionGravity = policyGravityLayer.getWeight(`action:${ctx.action}`);
    const pluginGravity = policyGravityLayer.getWeight(`plugin:${ctx.pluginName}`);
    const capabilityGravity = policyGravityLayer.getWeight(`capability:${ctx.capability}`);
    
    const totalGravity = actionGravity + pluginGravity + capabilityGravity;

    // If the accumulated gravity is too high, block execution at the boundary
    if (totalGravity >= GRAVITY_DENY_THRESHOLD) {
      return {
        granted: false,
        action: "deny",
        reason: `Blocked by Policy Gravity Layer. Accumulated gravity (${totalGravity.toFixed(2)}) exceeds execution threshold (${GRAVITY_DENY_THRESHOLD}).`
      };
    }

    // --- 2. STATIC POLICY CHECK ---
    let explicitlyAllowed = false;

    for (const policy of this.policies) {
      // Quick filter
      if (policy.targetPlugin && policy.targetPlugin !== ctx.pluginName) continue;
      if (policy.targetAction && policy.targetAction !== ctx.action) continue;

      const result = policy.evaluate(ctx);
      if (result) {
        // If ANY policy explicitly denies, immediately block (Hard Deny)
        if (!result.granted) {
          return result;
        }
        // Track if we got an explicit allow
        if (result.action === "allow") {
          explicitlyAllowed = true;
        }
      }
    }

    // --- 3. ZERO TRUST DEFAULT ---
    if (!explicitlyAllowed) {
      return {
        granted: false,
        action: "deny",
        reason: `No safety policy explicitly allowed action '${ctx.action}' on plugin '${ctx.pluginName}' (Zero Trust Default).`
      };
    }

    return { granted: true, action: "allow" };
  }
}

export const permissionManager = new PermissionManager();
