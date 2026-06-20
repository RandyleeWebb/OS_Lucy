import { PluginDefinition } from "./types";
import { Resource } from "../resources/types";
import { permissionManager } from "../safety/PermissionManager";

export function createResourceFromPlugin(
  plugin: PluginDefinition,
  capability: string
): Resource {
  return {
    id: `${plugin.name}:${capability}`,
    type: "actuator",
    capabilities: [capability],

    execute: async (action, payload) => {
      // --- 🛡️ SAFETY GATE (ZERO TRUST BOUNDARY) ---
      const permission = permissionManager.evaluate({
        pluginName: plugin.name,
        capability,
        action,
        payload
      });

      if (!permission.granted) {
        console.warn(`[SAFETY GATE] Blocked execution: ${plugin.name} -> ${action}. Reason: ${permission.reason}`);
        return {
          success: false,
          error: `Blocked for safety: ${permission.reason}`,
          metrics: { executionTimeMs: 0 }
        };
      }
      // --------------------------------------------

      return plugin.execute({ action, payload });
    }
  };
}
