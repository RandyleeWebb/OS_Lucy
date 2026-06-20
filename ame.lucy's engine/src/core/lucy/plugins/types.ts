import { Json } from "../core/types";

export interface PluginExecuteInput {
  action: string;
  payload?: Json;
  context?: Json;
}

export interface PluginExecuteResult {
  success: boolean;
  data?: Json;
  error?: string;
  metrics?: {
    executionTimeMs?: number;
    memoryUsageMb?: number;
  };
}

export interface PluginDefinition {
  name: string;
  version: string;
  provides: string[]; // capabilities
  initialize?: () => Promise<void>;
  shutdown?: () => Promise<void>;
  execute: (input: PluginExecuteInput) => Promise<PluginExecuteResult>;
}
