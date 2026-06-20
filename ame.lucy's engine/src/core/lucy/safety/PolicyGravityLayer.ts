import { ExecutionTrace } from "../learning/types";
import { eventBus } from "../EventBus";

export interface Constraint {
  id: string;
  type: string; // e.g., "action:spawn", "plugin:NativeProcessManager"
  weight: number; // 0.0 to 1.0 (Higher = stronger avoidance gravity)
  decay: number; // Amount to reduce weight per tick
}

export class PolicyGravityLayer {
  private constraints: Map<string, Constraint> = new Map();

  constructor() {
    // Initialize some baseline constraints
    this.registerConstraint({
      id: "action:kill",
      type: "action",
      weight: 0.5, // Starts with some gravity (caution)
      decay: 0.01
    });
    this.registerConstraint({
      id: "action:spawn",
      type: "action",
      weight: 0.2,
      decay: 0.05
    });

    // Autonomous decay loop
    setInterval(() => {
      this.applyDecay();
    }, 1000);
  }

  registerConstraint(constraint: Constraint) {
    this.constraints.set(constraint.id, constraint);
  }

  getConstraints(): Map<string, number> {
    const weights = new Map<string, number>();
    this.constraints.forEach((c, id) => weights.set(id, c.weight));
    return weights;
  }

  getWeight(constraintId: string): number {
    return this.constraints.get(constraintId)?.weight || 0;
  }

  private emitGravityUpdate() {
    const weights: Record<string, number> = {};
    this.constraints.forEach((c, id) => {
      weights[id] = c.weight;
    });
    eventBus.publish({
      type: 'GRAVITY_UPDATED',
      payload: { weights }
    });
  }

  /**
   * Increases the weight of a constraint (e.g., when an action is blocked or fails).
   * This creates "gravity" that pushes the planner away from this action in the future.
   */
  increaseGravity(constraintId: string, amount: number = 0.3) {
    const c = this.constraints.get(constraintId);
    if (c) {
      c.weight = Math.min(1.0, c.weight + amount);
      console.log(`[GravityLayer] Increased gravity for ${constraintId} -> ${c.weight.toFixed(2)}`);
    } else {
      // Auto-register new constraint if we hit a novel block
      this.registerConstraint({
        id: constraintId,
        type: "dynamic",
        weight: amount,
        decay: 0.05
      });
    }
    this.emitGravityUpdate();
  }

  /**
   * Decays all constraint weights slightly.
   * This prevents permanent overfitting and allows Lucy to re-explore boundaries if the environment changes.
   */
  applyDecay() {
    let changed = false;
    this.constraints.forEach(c => {
      if (c.weight > 0) {
        c.weight = Math.max(0, c.weight - c.decay);
        changed = true;
      }
    });
    if (changed) {
      this.emitGravityUpdate();
    }
  }

  /**
   * Analyzes an execution trace and updates gravity based on failures/blocks.
   */
  updateFromTrace(trace: ExecutionTrace) {
    for (const step of trace.steps) {
      if (!step.success) {
        const planStep = trace.plan.steps.find(s => s.id === step.stepId);
        if (planStep) {
          // If blocked by safety, massive gravity increase
          if (step.error?.includes("Blocked for safety")) {
            this.increaseGravity(`action:${planStep.action}`, 0.5);
            this.increaseGravity(`capability:${planStep.capability}`, 0.2);
          } else {
            // Standard failure, minor gravity increase
            this.increaseGravity(`action:${planStep.action}`, 0.1);
          }
        }
      }
    }
  }
}

export const policyGravityLayer = new PolicyGravityLayer();
