import { UUID, Timestamp, Json } from "../core/types";

export interface MemoryEntry {
  id: UUID;
  createdAt: Timestamp;
  type: "episodic" | "semantic" | "procedural";
  content: Json;
  tags?: string[];
  relevanceScore?: number;
  meta?: {
    source?: string;
    success?: boolean;
    usageCount?: number;
  };
}

export interface MetaRule {
  id: UUID;
  description: string;
  triggers: string[];
  constraints?: string[];
  failureModes?: string[];
  successRate?: number;
  usageCount?: number;
}
