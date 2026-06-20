import { Json, Timestamp, UUID } from "../core/types";

export interface WorldEntity {
  id: string;
  type: string;
  state: Json;
  lastObserved: Timestamp;
  confidence: number;
}

export interface WorldBelief {
  entities: Map<string, WorldEntity>;
  constraints: Map<string, number>; // Constraint ID -> Current Weight
  stableRules: Set<string>;
  volatileObservations: Json[];
}
