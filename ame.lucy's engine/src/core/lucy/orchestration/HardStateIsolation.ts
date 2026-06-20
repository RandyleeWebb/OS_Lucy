import { policyGravityLayer } from '../safety/PolicyGravityLayer';
import { worldModelService } from '../world/WorldModelService';

export type IsolatedExecutionResult<T> = {
  success: boolean;
  data?: T;
  error?: string;
  gravityPenaltyApplied?: number;
};

/**
 * HardStateIsolation Wrapper
 * 
 * Prevents external logic or untrusted swarm agents from directly mutating 
 * the core cognitive state (Belief State, Intent State, or Gravity Layer).
 * Enforces read-only context and routes all outputs through the PolicyGravityLayer.
 */
export class HardStateIsolation {
  /**
   * Wraps and executes external logic within a strict boundary.
   * 
   * @param agentId - The identifier of the external agent/logic
   * @param actionSignature - The signature of the action (e.g., "action:external_api_call")
   * @param externalLogic - The untrusted function to execute
   */
  static async execute<T>(
    agentId: string,
    actionSignature: string,
    externalLogic: (readOnlyState: any) => Promise<T>
  ): Promise<IsolatedExecutionResult<T>> {
    
    // 1. State Isolation: Create a deeply cloned, frozen snapshot of the world state
    // This ensures the external logic cannot mutate the actual WorldModel by reference.
    const rawState = worldModelService.getBeliefState();
    const readOnlyState = Object.freeze(structuredClone(rawState));

    // 2. Pre-Execution Safety Gate (Gravity Check)
    const currentGravity = policyGravityLayer.getWeight(actionSignature);
    if (currentGravity > 0.8) {
      console.warn(`[HardStateIsolation] Agent ${agentId} blocked. Gravity for ${actionSignature} is too high (${currentGravity}).`);
      return { 
        success: false, 
        error: `BLOCKED_BY_GRAVITY: Action exceeds safety threshold (${currentGravity}).` 
      };
    }

    try {
      // 3. Execution within the boundary
      // In a fully distributed system, this would run in a Web Worker or V8 Isolate.
      const result = await externalLogic(readOnlyState);

      // 4. Post-Execution Validation (Sanitization could go here)
      
      // Reward successful execution with a slight gravity decay (reinforcement)
      policyGravityLayer.increaseGravity(actionSignature, -0.05);

      return { 
        success: true, 
        data: result 
      };

    } catch (error: any) {
      // 5. Failure Handling & Immune Response
      // If the external logic crashes or throws, we penalize it by increasing gravity.
      const penalty = 0.2;
      policyGravityLayer.increaseGravity(actionSignature, penalty);
      
      console.error(`[HardStateIsolation] Agent ${agentId} failed during ${actionSignature}. Applying gravity penalty.`);
      
      return { 
        success: false, 
        error: error.message || "Unknown external logic failure",
        gravityPenaltyApplied: penalty
      };
    }
  }
}
