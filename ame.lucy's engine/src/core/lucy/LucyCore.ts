import { LucyPlugin, LucyContext, LucyResult, MemoryEntry } from './types';
import { eventBus } from './EventBus';
import { policyGravityLayer } from './safety/PolicyGravityLayer';

class LucyCognitiveCore {
  private plugins: Map<string, LucyPlugin> = new Map();
  private activePlugins: Set<string> = new Set();
  private longTermMemory: MemoryEntry[] = [];

  // --- Plugin Management ---

  discoverPlugin(plugin: LucyPlugin) {
    if (!this.plugins.has(plugin.id)) {
      this.plugins.set(plugin.id, plugin);
      eventBus.publish({
        type: 'PLUGIN_DISCOVERED',
        payload: { pluginId: plugin.id, name: plugin.name, category: plugin.category }
      });
    }
  }

  loadPlugin(pluginId: string) {
    if (this.plugins.has(pluginId) && !this.activePlugins.has(pluginId)) {
      this.activePlugins.add(pluginId);
      eventBus.publish({ type: 'PLUGIN_LOADED', payload: { pluginId } });
    }
  }

  unloadPlugin(pluginId: string) {
    if (this.activePlugins.has(pluginId)) {
      this.activePlugins.delete(pluginId);
      eventBus.publish({ type: 'PLUGIN_UNLOADED', payload: { pluginId } });
    }
  }

  getPlugins() {
    return Array.from(this.plugins.values()).map(p => ({
      ...p,
      status: this.activePlugins.has(p.id) ? 'loaded' : 'unloaded'
    }));
  }

  // --- 🧠 THE LUCY KERNEL (CONTROL LOOP) ---

  async tick(input: string, sessionId: string = 'default'): Promise<LucyResult | null> {
    eventBus.publish({ type: 'KERNEL_TICK_START', payload: { intent: input, sessionId } });

    // 1. Perception (Intent Parsing)
    const intent = input; // In a full system, this runs through an NLP/LLM parser

    // 2. Context Building
    const contextSnapshot = JSON.stringify({ 
      sessionId, 
      recentEvents: this.longTermMemory.slice(-5) 
    });

    // 3. Memory Reinjection (MetaRules)
    const metaRules = this.queryMemory(intent);

    // 4. Reasoning (ARC / Pattern Engine)
    // Here we decide WHAT needs to be done based on rules and intent
    const plan = {
      actionPayload: intent,
      requiresFileAccess: intent.includes('file') || intent.includes('save'),
      isPerformanceIssue: intent.includes('optimize') || intent.includes('performance')
    };

    // 5. Tool / Plugin Selection
    const selectedPluginId = this.selectPlugin(plan, metaRules);
    
    if (!selectedPluginId) {
      eventBus.publish({
        type: 'INTENT_EVALUATED',
        payload: { intent, selectedPluginId: 'none', reason: 'Safety/Logic Gate: No suitable plugin found or action blocked.' }
      });
      eventBus.publish({ type: 'KERNEL_TICK_END', payload: { intent, success: false } });
      return null;
    }

    const plugin = this.plugins.get(selectedPluginId)!;
    eventBus.publish({
      type: 'INTENT_EVALUATED',
      payload: { 
        intent, 
        selectedPluginId, 
        reason: `MetaRule matched: Plan aligns with ${plugin.category} capabilities of ${plugin.name}.` 
      }
    });

    // 6. Execution (The Node Bridge Boundary)
    const context: LucyContext = {
      apiVersion: 1, // Matches LUCY_PLUGIN_API_VERSION
      input: plan.actionPayload,
      memorySnapshot: contextSnapshot,
      intentId: Math.random().toString(36).substr(2, 9)
    };

    eventBus.publish({ type: 'PLUGIN_EXECUTION_STARTED', payload: { pluginId: selectedPluginId, context } });
    
    let result: LucyResult;
    try {
      // In production, this calls the Node.js bridge which uses ffi-napi to call the C++ DLL
      result = await plugin.execute(context);
      eventBus.publish({ type: 'PLUGIN_EXECUTION_COMPLETED', payload: { pluginId: selectedPluginId, result } });
    } catch (error: any) {
      result = {
        success: false,
        output: '',
        confidence: 0,
        executionTimeMs: 0,
        errors: error.message
      };
      eventBus.publish({ type: 'PLUGIN_EXECUTION_FAILED', payload: { pluginId: selectedPluginId, error: error.message } });
    }

    // 7. Evaluation & 8. Learning (ArcMemoryFusionEngine)
    this.processOutcome(intent, selectedPluginId, result);

    // Update gravity based on outcome
    if (!result.success) {
      policyGravityLayer.increaseGravity(`action:${plan.actionPayload.split(' ')[0] || 'unknown'}`, 0.2);
    } else {
      // Small bump to simulate activity
      policyGravityLayer.increaseGravity(`action:${plan.actionPayload.split(' ')[0] || 'unknown'}`, 0.05);
    }

    eventBus.publish({ type: 'KERNEL_TICK_END', payload: { intent, success: result.success } });
    return result;
  }

  // --- Internal Cognitive Subsystems ---

  private queryMemory(intent: string): string[] {
    // Simulate querying long-term memory for MetaRules
    const rules = [];
    if (intent.toLowerCase().includes('performance')) rules.push('performance issue');
    if (intent.toLowerCase().includes('file')) rules.push('file access required');
    return rules;
  }

  private selectPlugin(plan: any, metaRules: string[]): string | null {
    const active = Array.from(this.activePlugins).map(id => this.plugins.get(id)!);
    
    // MetaRule-driven selection
    if (metaRules.includes('performance issue') || plan.isPerformanceIssue) {
      return active.find(p => p.category === 'Analysis')?.id || null;
    }
    if (metaRules.includes('file access required') || plan.requiresFileAccess) {
      return active.find(p => p.name.includes('File') || p.category === 'Action')?.id || null;
    }
    if (plan.actionPayload.toLowerCase().includes('solve') || plan.actionPayload.toLowerCase().includes('path')) {
      return active.find(p => p.category === 'CognitiveAssist')?.id || null;
    }
    if (plan.actionPayload.toLowerCase().includes('asset') || plan.actionPayload.toLowerCase().includes('generate')) {
      return active.find(p => p.name.includes('Asset') || p.id.includes('asset'))?.id || null;
    }
    
    // Fallback
    return active.find(p => p.category === 'Action')?.id || null;
  }

  private processOutcome(intent: string, pluginId: string, result: LucyResult) {
    // Store in memory so Lucy learns: "this plugin works best for this type of problem"
    const entry: MemoryEntry = {
      type: 'execution_record',
      timestamp: Date.now(),
      data: { 
        intent, 
        pluginId, 
        success: result.success, 
        confidence: result.confidence, 
        executionTimeMs: result.executionTimeMs,
        errors: result.errors
      }
    };
    
    this.longTermMemory.push(entry);
    eventBus.publish({ type: 'MEMORY_UPDATED', payload: { key: 'longTermMemory', value: entry } });
  }
}

export const lucyCore = new LucyCognitiveCore();
