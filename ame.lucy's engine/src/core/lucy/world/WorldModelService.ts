import { WorldBelief, WorldEntity } from "./types";
import { ExecutionTrace } from "../learning/types";
import { Json } from "../core/types";

export class WorldModelService {
  private belief: WorldBelief = {
    entities: new Map(),
    constraints: new Map(),
    stableRules: new Set(),
    volatileObservations: []
  };

  /**
   * Returns a snapshot of the current world belief for the Kernel to use in perception/planning.
   */
  getBeliefState(): WorldBelief {
    return this.belief;
  }

  /**
   * Consolidates reality changes from an execution trace into the single belief space.
   */
  consolidateTrace(trace: ExecutionTrace) {
    const now = Date.now();

    // 1. Process volatile observations from step outputs
    for (const step of trace.steps) {
      if (step.success && step.output) {
        this.belief.volatileObservations.push({
          stepId: step.stepId,
          action: trace.plan.steps.find(s => s.id === step.stepId)?.action,
          output: step.output,
          timestamp: now
        });

        // Example Entity Extraction: If a process was spawned, track it as an entity
        if (typeof step.output === 'object' && step.output !== null) {
          const out = step.output as any;
          if (out.status === 'process_spawned' || out.status === 'simulated_native_success') {
            const entityId = `process_${Math.random().toString(36).substr(2, 5)}`;
            this.belief.entities.set(entityId, {
              id: entityId,
              type: 'process',
              state: out,
              lastObserved: now,
              confidence: 1.0
            });
          }
        }
      }
    }

    // Keep volatile observations bounded
    if (this.belief.volatileObservations.length > 50) {
      this.belief.volatileObservations.shift();
    }

    // 2. Extract stable rules from repeated successes (Simplified for MVP)
    if (trace.success && trace.steps.length > 0) {
      const primaryAction = trace.plan.steps[0].action;
      this.belief.stableRules.add(`Action '${primaryAction}' is generally stable in current context.`);
    }
  }

  /**
   * Syncs constraint weights from the Policy Gravity Layer into the World Belief.
   */
  syncConstraints(constraints: Map<string, number>) {
    this.belief.constraints = new Map(constraints);
  }
}

export const worldModelService = new WorldModelService();
