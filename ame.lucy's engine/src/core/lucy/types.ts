export type PluginCategory = 'Analysis' | 'Action' | 'CognitiveAssist';

// Mirrors the C++ LucyContext struct
export interface LucyContext {
  apiVersion: number;
  input: string;
  memorySnapshot: string;
  intentId: string;
}

// Mirrors the C++ LucyResult struct
export interface LucyResult {
  success: boolean;
  output: string;
  confidence: number;
  executionTimeMs: number;
  errors?: string;
}

// Represents the Node Bridge interface to the C++ Plugin
export interface LucyPlugin {
  id: string;
  name: string;
  category: PluginCategory;
  description: string;
  version: string;
  execute: (ctx: LucyContext) => Promise<LucyResult>;
}

export type LucyEvent =
  | { type: 'PLUGIN_DISCOVERED'; payload: { pluginId: string; name: string; category: PluginCategory } }
  | { type: 'PLUGIN_LOADED'; payload: { pluginId: string } }
  | { type: 'PLUGIN_UNLOADED'; payload: { pluginId: string } }
  | { type: 'PLUGIN_EXECUTION_STARTED'; payload: { pluginId: string; context: LucyContext } }
  | { type: 'PLUGIN_EXECUTION_COMPLETED'; payload: { pluginId: string; result: LucyResult } }
  | { type: 'PLUGIN_EXECUTION_FAILED'; payload: { pluginId: string; error: string } }
  | { type: 'INTENT_EVALUATED'; payload: { intent: string; selectedPluginId: string; reason: string } }
  | { type: 'MEMORY_UPDATED'; payload: { key: string; value: any } }
  | { type: 'KERNEL_TICK_START'; payload: { intent: string; sessionId: string } }
  | { type: 'KERNEL_TICK_END'; payload: { intent: string; success: boolean } }
  | { type: 'GRAVITY_UPDATED'; payload: { weights: Record<string, number> } };

export interface MemoryEntry {
  timestamp: number;
  type: 'execution_record' | 'rule' | 'observation';
  data: any;
}
