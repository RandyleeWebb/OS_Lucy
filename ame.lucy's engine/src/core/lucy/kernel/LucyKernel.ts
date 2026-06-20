import { LucyTickInput, LucyTickResult, CognitivePlan, CognitiveStep } from "./types";
import { CapabilityResolver } from "../capabilities/types";
import { LearningEngine, ExecutionTrace, StepResult } from "../learning/types";
import { worldModelService } from "../world/WorldModelService";
import { policyGravityLayer } from "../safety/PolicyGravityLayer";
import { PlanningPruner } from "../reasoning/PlanningPruner";

export class LucyKernel {
  private pruner: PlanningPruner;

  constructor(
    private resolver: CapabilityResolver,
    private learning: LearningEngine
  ) {
    this.pruner = new PlanningPruner(policyGravityLayer);
  }

  async tick(input: LucyTickInput): Promise<LucyTickResult> {
    const start = Date.now();

    // 1. Perception & World Consolidation
    // Sync constraints into belief space so the planner has full context
    worldModelService.syncConstraints(policyGravityLayer.getConstraints());
    const belief = worldModelService.getBeliefState();

    // 2. Generate Raw Plan
    let rawPlan: CognitivePlan = await this.generateRawPlan(input, belief);
    
    // 3. Planning Space Pruning (Pre-execution safety & gravity check)
    let plan = this.pruner.prune(rawPlan, belief);

    // 4. Execution
    const trace = await this.executePlan(plan);

    // 5. World State Update & Consolidation
    worldModelService.consolidateTrace(trace);

    // 6. Policy Gravity Update (Soft avoidance learning)
    policyGravityLayer.updateFromTrace(trace);
    policyGravityLayer.applyDecay(); // Decay weights over time to prevent permanent overfitting

    // 7. Deep Learning & Memory Fusion
    await this.learning.process(trace);

    return {
      success: trace.success,
      output: trace.steps.at(-1)?.output,
      traceId: trace.traceId,
      durationMs: Date.now() - start
    };
  }

  private async generateRawPlan(input: LucyTickInput, belief: any): Promise<CognitivePlan> {
    // Hook into ARC / reasoning engine. Uses WorldBelief to inform generation.
    // Mocking a plan for demonstration
    return {
      id: Math.random().toString(36).substr(2, 9),
      goal: input.goal,
      steps: [
        {
          id: "step_1",
          description: "Execute requested action",
          capability: input.goal.includes("kill") ? "process_management" : 
                     (input.goal.includes("monitor") ? "process_management" : 
                     (input.goal.includes("asset") || input.goal.includes("generate") ? "asset_generation" : "file_system")),
          action: input.goal.includes("kill") ? "kill" : 
                  (input.goal.includes("monitor") ? "monitor" : 
                  (input.goal.includes("asset") || input.goal.includes("generate") ? "generate" : "spawn")),
          payload: input.context
        }
      ],
      confidence: 0.9,
      traceId: Math.random().toString(36).substr(2, 9)
    };
  }

  private async executePlan(plan: CognitivePlan): Promise<ExecutionTrace> {
    const steps: StepResult[] = [];
    let success = true;

    for (const step of plan.steps) {
      const start = Date.now();
      try {
        // 1. Resolve capability to a specific Resource (Plugin)
        const resource = await this.resolver.resolve({ capability: step.capability });
        
        // 2. Execute the resource (This hits the ResourceAdapter -> PermissionManager -> Plugin)
        const result = await resource.execute(step.action, step.payload);
        
        steps.push({
          stepId: step.id,
          success: result.success,
          output: result.data,
          error: result.error,
          durationMs: Date.now() - start
        });

        if (!result.success) {
          success = false;
          break; // Halt plan execution on failure
        }
      } catch (err: any) {
        success = false;
        steps.push({
          stepId: step.id,
          success: false,
          error: err.message,
          durationMs: Date.now() - start
        });
        break;
      }
    }

    return {
      traceId: plan.traceId,
      plan,
      steps,
      startedAt: Date.now(),
      completedAt: Date.now(),
      success
    };
  }
}
