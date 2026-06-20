import { UUID } from "../core/types";
import { PluginExecuteResult } from "../plugins/types";

export type ResourceType =
  | "sensor"
  | "actuator"
  | "compute"
  | "memory";

export interface ResourceLimits {
  latencyMs?: number;
  bandwidth?: number;
  energyCost?: number;
}

export interface Resource {
  id: UUID;
  type: ResourceType;
  capabilities: string[];
  limits?: ResourceLimits;
  execute: (action: string, payload?: any) => Promise<PluginExecuteResult>;
}
