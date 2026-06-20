import { CognitivePlan, CognitiveStep } from "../kernel/types";
import { PolicyGravityLayer } from "../safety/PolicyGravityLayer";
import { WorldBelief } from "../world/types";

export class PlanningPruner {
  constructor(private gravityLayer: PolicyGravityLayer) {}

  /**
   * Evaluates a raw plan against the Policy Gravity Layer and World Belief.
   * Prunes or adapts invalid branches BEFORE execution.
   */
  prune(rawPlan: CognitivePlan, belief: WorldBelief): CognitivePlan {
    const prunedSteps: CognitiveStep[] = [];
    let planConfidence = rawPlan.confidence;

    for (const step of rawPlan.steps) {
      const actionGravity = this.gravityLayer.getWeight(`action:${step.action}`);
      const capabilityGravity = this.gravityLayer.getWeight(`capability:${step.capability}`);
      
      const totalGravity = actionGravity + capabilityGravity;

      // If gravity is too high (e.g., > 0.7), the action is deemed too risky/invalid
      if (totalGravity > 0.7) {
        console.log(`[PlanningPruner] Pruning step '${step.action}' due to high constraint gravity (${totalGravity.toFixed(2)}).`);
        
        // Internalize constraint: Adapt the step instead of just failing
        if (step.action === "spawn" || step.action === "kill") {
          prunedSteps.push({
            ...step,
            action: "monitor",
            description: `[Adapted] Original action '${step.action}' pruned. Defaulting to safe monitoring.`
          });
          planConfidence *= 0.8; // Reduce confidence due to adaptation
        } else {
          // Drop the step entirely if no safe adaptation exists
          planConfidence *= 0.5;
        }
      } else {
        // Step is safe enough to proceed
        prunedSteps.push(step);
      }
    }

    return {
      ...rawPlan,
      steps: prunedSteps,
      confidence: planConfidence
    };
  }
}
