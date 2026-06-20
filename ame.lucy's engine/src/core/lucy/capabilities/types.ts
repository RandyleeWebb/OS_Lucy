import { Resource } from "../resources/types";

export interface CapabilityRequest {
  capability: string;
  constraints?: {
    maxLatency?: number;
    minReliability?: number;
  };
}

export interface CapabilityResolver {
  resolve(request: CapabilityRequest): Promise<Resource>;
}
