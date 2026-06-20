import { LucyEvent } from './types';

type EventHandler = (event: LucyEvent) => void;

class LucyEventBus {
  private listeners: Set<EventHandler> = new Set();
  private history: LucyEvent[] = [];

  subscribe(handler: EventHandler) {
    this.listeners.add(handler);
    return () => this.listeners.delete(handler);
  }

  publish(event: LucyEvent) {
    this.history.push(event);
    // Keep history manageable
    if (this.history.length > 1000) {
      this.history.shift();
    }
    this.listeners.forEach(listener => listener(event));
  }

  getHistory() {
    return [...this.history];
  }
}

export const eventBus = new LucyEventBus();
