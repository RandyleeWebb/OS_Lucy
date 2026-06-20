import { UUID, Timestamp, Json } from "../core/types";

export interface Event<T = Json> {
  id: UUID;
  type: string;
  timestamp: Timestamp;
  payload: T;
}

export interface EventBus {
  publish<T>(event: Event<T>): void;
  subscribe<T>(type: string, handler: (event: Event<T>) => void): void;
}
