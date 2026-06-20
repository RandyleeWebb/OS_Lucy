import { UUID } from "../core/types";
import { CognitivePlan, CognitiveStep } from "../kernel/types";

export interface StepResult {
  stepId: UUID;
  success: boolean;
  output?: any;
  error?: string;
  durationMs?: number;
}

export interface ExecutionTrace {
  traceId: UUID;
  plan: CognitivePlan;
  steps: StepResult[];
  startedAt: number;
  completedAt?: number;
  success: boolean;
}

export interface LearningEngine {
  process(trace: ExecutionTrace): Promise<void>;
}
