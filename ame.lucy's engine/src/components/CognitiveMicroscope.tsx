import React, { useEffect, useState, useRef } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { Brain, Zap, Database, Activity, ChevronRight, Terminal } from 'lucide-react';
import { eventBus } from '../core/lucy/EventBus';
import { LucyEvent } from '../core/lucy/types';
import { cn } from '../lib/utils';
import { lucyCore } from '../core/lucy/LucyCore';
import { ConstraintDecayChart } from './ConstraintDecayChart';

export const CognitiveMicroscope: React.FC = () => {
  const [events, setEvents] = useState<LucyEvent[]>([]);
  const [inputIntent, setInputIntent] = useState('');
  const endOfMessagesRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Load initial history
    setEvents(eventBus.getHistory());

    // Subscribe to new events
    const unsubscribe = eventBus.subscribe((event) => {
      setEvents(prev => [...prev, event]);
    });

    return () => unsubscribe();
  }, []);

  useEffect(() => {
    endOfMessagesRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [events]);

  const handleSimulateIntent = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputIntent.trim()) return;
    
    const intent = inputIntent;
    setInputIntent('');
    
    await lucyCore.tick(intent, 'session_' + Math.random().toString(36).substr(2, 5));
  };

  const renderEventPayload = (event: LucyEvent) => {
    switch (event.type) {
      case 'KERNEL_TICK_START':
        return (
          <div className="mt-1 text-[10px] font-mono text-blue-400">
            [Kernel] Tick started for session: {event.payload.sessionId}
          </div>
        );
      case 'INTENT_EVALUATED':
        return (
          <div className="mt-1 p-2 bg-editor-bg rounded border border-editor-border text-[10px] font-mono">
            <div className="text-editor-accent mb-1">Intent: "{event.payload.intent}"</div>
            <div className="text-editor-text-muted">Selected Plugin: {event.payload.selectedPluginId}</div>
            <div className="text-green-400/80 mt-1">Reasoning: {event.payload.reason}</div>
          </div>
        );
      case 'PLUGIN_EXECUTION_STARTED':
        return (
          <div className="mt-1 p-2 bg-editor-bg rounded border border-editor-border text-[10px] font-mono">
            <div className="text-yellow-500/80">Executing: {event.payload.pluginId}</div>
            <div className="text-editor-text-muted truncate">Context: {JSON.stringify(event.payload.context)}</div>
          </div>
        );
      case 'PLUGIN_EXECUTION_COMPLETED':
        return (
          <div className="mt-1 p-2 bg-editor-bg rounded border border-editor-border text-[10px] font-mono">
            <div className="text-green-500">Success (Conf: {event.payload.result.confidence})</div>
            <div className="text-editor-text mt-1">{event.payload.result.output}</div>
            <div className="text-editor-text-muted mt-1">Time: {event.payload.result.executionTimeMs.toFixed(2)}ms</div>
          </div>
        );
      case 'PLUGIN_EXECUTION_FAILED':
        return (
          <div className="mt-1 p-2 bg-red-500/10 rounded border border-red-500/20 text-[10px] font-mono text-red-400">
            Failed: {event.payload.error}
          </div>
        );
      default:
        return null;
    }
  };

  const getEventIcon = (type: string) => {
    if (type.includes('INTENT')) return <Brain size={12} className="text-purple-400" />;
    if (type.includes('STARTED')) return <Activity size={12} className="text-yellow-400" />;
    if (type.includes('COMPLETED')) return <Zap size={12} className="text-green-400" />;
    if (type.includes('MEMORY')) return <Database size={12} className="text-blue-400" />;
    return <Terminal size={12} className="text-editor-text-muted" />;
  };

  return (
    <div className="flex flex-col h-full bg-editor-panel">
      <div className="p-3 border-b border-editor-border bg-editor-bg">
        <ConstraintDecayChart />
      </div>
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {events.length === 0 && (
          <div className="text-xs text-editor-text-muted italic flex items-center justify-center h-full">
            Awaiting cognitive activity...
          </div>
        )}
        <AnimatePresence initial={false}>
          {events.map((event, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex gap-3"
            >
              <div className="mt-0.5">{getEventIcon(event.type)}</div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-[10px] font-bold text-editor-text">{event.type}</span>
                  <span className="text-[9px] text-editor-text-muted">{new Date().toLocaleTimeString()}</span>
                </div>
                {renderEventPayload(event)}
              </div>
            </motion.div>
          ))}
        </AnimatePresence>
        <div ref={endOfMessagesRef} />
      </div>
      
      <div className="p-3 border-t border-editor-border bg-editor-bg">
        <form onSubmit={handleSimulateIntent} className="flex gap-2">
          <div className="flex-1 relative">
            <Brain size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-editor-text-muted" />
            <input
              type="text"
              value={inputIntent}
              onChange={(e) => setInputIntent(e.target.value)}
              placeholder="Simulate Intent (e.g., 'optimize server performance')"
              className="w-full bg-editor-panel border border-editor-border rounded pl-9 pr-3 py-1.5 text-xs text-editor-text outline-none focus:border-editor-accent transition-colors"
            />
          </div>
          <button 
            type="submit"
            disabled={!inputIntent.trim()}
            className="px-4 py-1.5 bg-editor-accent hover:bg-editor-accent-hover disabled:opacity-50 disabled:hover:bg-editor-accent text-white text-xs font-bold rounded transition-colors"
          >
            Inject
          </button>
        </form>
      </div>
    </div>
  );
};
