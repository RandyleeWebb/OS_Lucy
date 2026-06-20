import React, { useEffect, useState } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend
} from 'recharts';
import { eventBus } from '../core/lucy/EventBus';
import { policyGravityLayer } from '../core/lucy/safety/PolicyGravityLayer';

interface WeightHistoryPoint {
  time: string;
  [constraintId: string]: number | string;
}

const COLORS = ['#3b82f6', '#f59e0b', '#10b981', '#ef4444', '#8b5cf6', '#ec4899'];

export const ConstraintDecayChart: React.FC = () => {
  const [history, setHistory] = useState<WeightHistoryPoint[]>([]);
  const [activeConstraints, setActiveConstraints] = useState<string[]>([]);

  useEffect(() => {
    // Initialize with current weights
    const initialWeights = policyGravityLayer.getConstraints();
    const initialPoint: WeightHistoryPoint = {
      time: new Date().toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })
    };
    const constraints: string[] = [];
    initialWeights.forEach((weight, id) => {
      initialPoint[id] = weight;
      constraints.push(id);
    });
    setHistory([initialPoint]);
    setActiveConstraints(constraints);

    const unsubscribe = eventBus.subscribe((event) => {
      if (event.type === 'GRAVITY_UPDATED') {
        const time = new Date().toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
        const newPoint: WeightHistoryPoint = { time };
        
        Object.entries(event.payload.weights).forEach(([id, weight]) => {
          newPoint[id] = weight;
        });

        setActiveConstraints(prev => {
          const updated = new Set(prev);
          Object.keys(event.payload.weights).forEach(id => updated.add(id));
          return Array.from(updated);
        });

        setHistory(prev => {
          const newHistory = [...prev, newPoint];
          // Keep last 20 data points to avoid crowding
          if (newHistory.length > 20) {
            return newHistory.slice(newHistory.length - 20);
          }
          return newHistory;
        });
      }
    });

    return () => unsubscribe();
  }, []);

  if (history.length === 0) return null;

  return (
    <div className="w-full h-48 bg-editor-bg border border-editor-border rounded-lg p-3 flex flex-col">
      <div className="text-[10px] font-bold uppercase tracking-wider text-editor-text-muted mb-2">
        Constraint Weight Decay
      </div>
      <div className="flex-1 min-h-0">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={history} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#333" vertical={false} />
            <XAxis 
              dataKey="time" 
              stroke="#666" 
              fontSize={9} 
              tickMargin={5}
              tick={{ fill: '#666' }}
            />
            <YAxis 
              stroke="#666" 
              fontSize={9} 
              domain={[0, 1]} 
              tickFormatter={(val) => val.toFixed(1)}
              tick={{ fill: '#666' }}
            />
            <Tooltip 
              contentStyle={{ backgroundColor: '#1a1a1a', border: '1px solid #333', fontSize: '10px', color: '#ccc' }}
              itemStyle={{ fontSize: '10px' }}
              labelStyle={{ color: '#888', marginBottom: '4px' }}
            />
            <Legend 
              wrapperStyle={{ fontSize: '9px', paddingTop: '4px' }} 
              iconType="circle" 
              iconSize={6}
            />
            {activeConstraints.map((id, index) => (
              <Line
                key={id}
                type="monotone"
                dataKey={id}
                stroke={COLORS[index % COLORS.length]}
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 4 }}
                isAnimationActive={false}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};
