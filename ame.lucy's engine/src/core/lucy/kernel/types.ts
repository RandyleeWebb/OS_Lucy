import { UUID, Timestamp, Json } from "../core/types";

export interface LucyTickInput {
  sessionId: UUID;
  goal: string;
  context?: Json;
}

export interface LucyTickResult {
  success: boolean;
  output?: Json;
  error?: string;
  traceId: UUID;
  durationMs: number;
}

export interface CognitiveStep {
  id: UUID;
  description: string;
  capability: string;
  action: string;
  payload?: Json;
  expectedOutcome?: string;
  status?: "pending" | "running" | "completed" | "failed";
}

export interface CognitivePlan {
  id: UUID;
  goal: string;
  steps: CognitiveStep[];
  confidence: number;
  entropy?: number;
  traceId: UUID;
}
