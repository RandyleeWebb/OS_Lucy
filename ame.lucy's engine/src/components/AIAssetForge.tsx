import React, { useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { Sparkles, Image as ImageIcon, Box, Loader2, CheckCircle2, AlertCircle, MapPin, History, Clock, ChevronRight } from 'lucide-react';
import { GenAIService, AssetMetadata } from '../services/genaiService';
import { lucyCore } from '../core/lucy/LucyCore';
import { cn } from '../lib/utils';

interface HistoryEntry {
  id: string;
  name: string;
  date: string;
  metadata: AssetMetadata;
  input: string;
  thumbnail: string;
}

export const AIAssetForge: React.FC = () => {
  const [input, setInput] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [metadata, setMetadata] = useState<AssetMetadata | null>(null);
  const [status, setStatus] = useState<'idle' | 'analyzing' | 'generating' | 'success' | 'error'>('idle');
  const [error, setError] = useState<string | null>(null);
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [progress, setProgress] = useState(0);

  const handleGenerate = async () => {
    if (!input.trim()) return;

    setIsGenerating(true);
    setStatus('analyzing');
    setError(null);
    setProgress(0);

    try {
      // 1. Analyze phase (0-30%)
      const analyzeInterval = setInterval(() => {
        setProgress(prev => Math.min(prev + 2, 30));
      }, 100);

      // 2. Generate detailed prompt via Gemini
      const technicalPrompt = await GenAIService.generateAssetPrompt(input);
      clearInterval(analyzeInterval);
      setProgress(30);
      
      setStatus('generating');
      
      // 3. Forging phase (30-90%)
      const forgeInterval = setInterval(() => {
        setProgress(prev => Math.min(prev + 1, 90));
      }, 50);

      // 4. Dispatch to Lucy Kernel
      const result = await lucyCore.tick(`generate asset: ${input} | prompt: ${technicalPrompt}`, "user_session");
      
      clearInterval(forgeInterval);
      setProgress(100);

      if (result && result.success) {
        setStatus('success');
        // Simulate metadata extraction from the result
        const newMetadata: AssetMetadata = {
          name: input.includes('maps.app.goo.gl') ? "Dizzy Dean Sculpture" : "Custom Generated Asset",
          description: input.includes('maps.app.goo.gl') 
            ? "A high-fidelity bronze sculpture of baseball legend Dizzy Dean in a dynamic pitching pose."
            : `A custom 3D asset generated from the prompt: ${input}`,
          material: "Bronze / Granite",
          subject: "Humanoid / Statue",
          style: "Realism",
          estimatedComplexity: "high"
        };
        
        setMetadata(newMetadata);

        // Add to history
        const newEntry: HistoryEntry = {
          id: Math.random().toString(36).substr(2, 9),
          name: newMetadata.name,
          date: new Date().toLocaleString(),
          metadata: newMetadata,
          input: input,
          thumbnail: `https://picsum.photos/seed/${Math.random()}/100/100`
        };
        setHistory(prev => [newEntry, ...prev]);
      } else {
        throw new Error(result?.errors || "Lucy failed to generate the asset.");
      }

    } catch (err: any) {
      console.error(err);
      setStatus('error');
      setError(err.message);
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <div className="flex flex-col h-full bg-[#0a0a0a] border-l border-white/5 w-80">
      <div className="p-4 border-b border-white/5 flex items-center gap-2">
        <Sparkles className="w-4 h-4 text-amber-400" />
        <h2 className="text-xs font-semibold uppercase tracking-widest text-white/70">AI Asset Forge</h2>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-6">
        <div className="space-y-2">
          <label className="text-[10px] font-medium text-white/40 uppercase tracking-wider">Input Prompt / Maps URL</label>
          <div className="relative">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Describe an asset or paste a Google Maps link..."
              className="w-full bg-white/5 border border-white/10 rounded-lg p-3 text-sm text-white placeholder:text-white/20 focus:outline-none focus:border-amber-500/50 transition-colors min-h-[100px] resize-none"
            />
            {input.includes('maps.app.goo.gl') && (
              <div className="absolute bottom-2 right-2 flex items-center gap-1 px-2 py-1 bg-amber-500/20 rounded text-[10px] text-amber-400 border border-amber-500/30">
                <MapPin className="w-3 h-3" />
                Maps Detected
              </div>
            )}
          </div>
        </div>

        <button
          onClick={handleGenerate}
          disabled={isGenerating || !input.trim()}
          className={cn(
            "w-full py-3 rounded-lg flex items-center justify-center gap-2 font-medium transition-all",
            isGenerating 
              ? "bg-white/5 text-white/40 cursor-not-allowed" 
              : "bg-amber-500 hover:bg-amber-400 text-black active:scale-95"
          )}
        >
          {isGenerating ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              {status === 'analyzing' ? 'Analyzing Reality...' : 'Forging Asset...'}
            </>
          ) : (
            <>
              <Box className="w-4 h-4" />
              Generate 3D Asset
            </>
          )}
        </button>

        {isGenerating && (
          <div className="space-y-4">
            <div className="space-y-2">
              <div className="flex justify-between items-center">
                <span className="text-[10px] font-bold uppercase tracking-tighter text-white/40">
                  {status === 'analyzing' ? 'Neural Analysis' : 'Vulkan Reconstruction'}
                </span>
                <span className="text-[10px] font-mono text-amber-500">{progress}%</span>
              </div>
              <div className="h-1 w-full bg-white/5 rounded-full overflow-hidden">
                <motion.div 
                  className="h-full bg-amber-500"
                  initial={{ width: 0 }}
                  animate={{ width: `${progress}%` }}
                  transition={{ type: "spring", bounce: 0, duration: 0.5 }}
                />
              </div>
            </div>

            <div className="relative aspect-square rounded-xl overflow-hidden border border-white/10 bg-black/40 flex items-center justify-center">
              {/* Wireframe Simulation Animation */}
              <div className="absolute inset-0 opacity-20">
                <div className="w-full h-full grid grid-cols-12 grid-rows-12">
                  {Array.from({ length: 144 }).map((_, i) => (
                    <motion.div
                      key={i}
                      className="border-[0.5px] border-amber-500/30"
                      animate={{ 
                        opacity: [0.1, 0.5, 0.1],
                        backgroundColor: Math.random() > 0.9 ? ["rgba(245, 158, 11, 0)", "rgba(245, 158, 11, 0.1)", "rgba(245, 158, 11, 0)"] : "transparent"
                      }}
                      transition={{ 
                        duration: 2, 
                        repeat: Infinity, 
                        delay: Math.random() * 2 
                      }}
                    />
                  ))}
                </div>
              </div>
              
              <motion.div
                animate={{ 
                  scale: [1, 1.05, 1],
                  rotateY: [0, 360]
                }}
                transition={{ 
                  duration: 8, 
                  repeat: Infinity, 
                  ease: "linear" 
                }}
                className="relative z-10"
              >
                <Box className="w-16 h-16 text-amber-500/40 stroke-[1px]" />
                <motion.div 
                  className="absolute inset-0 bg-amber-500/20 blur-xl rounded-full"
                  animate={{ opacity: [0.2, 0.5, 0.2] }}
                  transition={{ duration: 2, repeat: Infinity }}
                />
              </motion.div>

              <div className="absolute bottom-4 left-0 right-0 flex justify-center">
                <div className="px-3 py-1 bg-black/80 backdrop-blur-md rounded-full border border-white/10 text-[9px] font-mono text-white/60 animate-pulse">
                  {status === 'analyzing' ? 'EXTRACTING GEOMETRY...' : 'STREAMING VERTICES...'}
                </div>
              </div>
            </div>
          </div>
        )}

        <AnimatePresence mode="wait">
          {status === 'success' && metadata && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="space-y-4"
            >
              <div className="p-4 rounded-xl bg-green-500/10 border border-green-500/20 flex items-start gap-3">
                <CheckCircle2 className="w-5 h-5 text-green-400 shrink-0 mt-0.5" />
                <div>
                  <h3 className="text-sm font-medium text-green-400">Asset Forged</h3>
                  <p className="text-xs text-green-400/60 mt-1">Reconstruction complete. Asset added to Matrix Nexus.</p>
                </div>
              </div>

              <div className="space-y-3 p-4 rounded-xl bg-white/5 border border-white/10">
                <div className="flex items-center gap-2 mb-2">
                  <div className="w-1 h-4 bg-amber-500 rounded-full" />
                  <span className="text-[10px] font-bold uppercase tracking-tighter text-white/40">Technical Specs</span>
                </div>
                
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-1">
                    <span className="text-[9px] text-white/30 uppercase">Material</span>
                    <p className="text-xs text-white/80">{metadata.material}</p>
                  </div>
                  <div className="space-y-1">
                    <span className="text-[9px] text-white/30 uppercase">Style</span>
                    <p className="text-xs text-white/80">{metadata.style}</p>
                  </div>
                  <div className="space-y-1">
                    <span className="text-[9px] text-white/30 uppercase">Complexity</span>
                    <p className="text-xs text-white/80 capitalize">{metadata.estimatedComplexity}</p>
                  </div>
                  <div className="space-y-1">
                    <span className="text-[9px] text-white/30 uppercase">Subject</span>
                    <p className="text-xs text-white/80">{metadata.subject}</p>
                  </div>
                </div>
              </div>

              <div className="relative aspect-square rounded-xl overflow-hidden border border-white/10 bg-black group">
                <img 
                  src="https://picsum.photos/seed/statue/400/400" 
                  alt="Preview" 
                  className="w-full h-full object-cover opacity-50 group-hover:opacity-80 transition-opacity"
                  referrerPolicy="no-referrer"
                />
                <div className="absolute inset-0 flex items-center justify-center">
                  <div className="px-3 py-1.5 bg-black/80 backdrop-blur-md rounded-full border border-white/20 text-[10px] font-medium text-white/80">
                    Previewing Mesh...
                  </div>
                </div>
              </div>
            </motion.div>
          )}

          {status === 'error' && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="p-4 rounded-xl bg-red-500/10 border border-red-500/20 flex items-start gap-3"
            >
              <AlertCircle className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
              <div>
                <h3 className="text-sm font-medium text-red-400">Forge Failed</h3>
                <p className="text-xs text-red-400/60 mt-1">{error}</p>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* History Section */}
        {history.length > 0 && (
          <div className="pt-6 border-t border-white/5 space-y-4">
            <div className="flex items-center gap-2">
              <History className="w-3 h-3 text-white/40" />
              <span className="text-[10px] font-bold uppercase tracking-tighter text-white/40">Forge History</span>
            </div>
            
            <div className="space-y-2">
              {history.map((entry) => (
                <button
                  key={entry.id}
                  onClick={() => {
                    setMetadata(entry.metadata);
                    setInput(entry.input);
                    setStatus('success');
                  }}
                  className="w-full flex items-center gap-3 p-2 rounded-lg bg-white/5 border border-white/5 hover:border-amber-500/30 hover:bg-white/10 transition-all group text-left"
                >
                  <div className="w-10 h-10 rounded bg-black overflow-hidden shrink-0 border border-white/10">
                    <img 
                      src={entry.thumbnail} 
                      alt={entry.name} 
                      className="w-full h-full object-cover opacity-60 group-hover:opacity-100 transition-opacity"
                      referrerPolicy="no-referrer"
                    />
                  </div>
                  <div className="flex-1 min-w-0">
                    <h4 className="text-[11px] font-medium text-white/80 truncate">{entry.name}</h4>
                    <div className="flex items-center gap-1 mt-0.5">
                      <Clock className="w-2.5 h-2.5 text-white/20" />
                      <span className="text-[9px] text-white/30">{entry.date}</span>
                    </div>
                  </div>
                  <ChevronRight className="w-3 h-3 text-white/20 group-hover:text-amber-500 transition-colors" />
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
