/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect } from 'react';
import { 
  Play, 
  Pause, 
  Layers, 
  Box, 
  Image as ImageIcon, 
  Sun, 
  Cpu, 
  Code2, 
  FolderTree, 
  Settings2, 
  ChevronRight, 
  Search,
  Maximize2,
  Terminal,
  Activity,
  Database,
  Zap,
  Plug,
  X,
  Upload,
  CheckCircle2,
  AlertCircle,
  Brain,
  Sparkles
} from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import { Viewport } from './components/Viewport';
import { CognitiveMicroscope } from './components/CognitiveMicroscope';
import { AIAssetForge } from './components/AIAssetForge';
import { cn } from './lib/utils';
import { lucyCore } from './core/lucy/LucyCore';
import { PerformanceAnalyzerPlugin, WorldEditorPlugin, PathfindingSolverPlugin, AssetGeneratorPlugin } from './core/lucy/plugins/CorePlugins';

type LayerType = 'geometry' | 'albedo' | 'normal' | 'wireframe' | 'lighting';
type BottomPanelTab = 'content' | 'log' | 'cognitive';
type RightSidebarTab = 'details' | 'forge';

export default function App() {
  const [activeLayer, setActiveLayer] = useState<LayerType>('albedo');
  const [isPlaying, setIsPlaying] = useState(false);
  const [stats, setStats] = useState({ fps: 0, drawCalls: 0, triangles: 0 });
  const [selectedEntity, setSelectedEntity] = useState<string | null>('TorusKnot_01');
  const [showPluginManager, setShowPluginManager] = useState(false);
  const [activeBottomTab, setActiveBottomTab] = useState<BottomPanelTab>('cognitive');
  const [activeRightTab, setActiveRightTab] = useState<RightSidebarTab>('details');
  const [rayTracingEnabled, setRayTracingEnabled] = useState(false);
  
  // Initialize Lucy Core Plugins
  useEffect(() => {
    lucyCore.discoverPlugin(PerformanceAnalyzerPlugin);
    lucyCore.discoverPlugin(WorldEditorPlugin);
    lucyCore.discoverPlugin(PathfindingSolverPlugin);
    lucyCore.discoverPlugin(AssetGeneratorPlugin);
    
    // Auto-load them for the demo
    lucyCore.loadPlugin(PerformanceAnalyzerPlugin.id);
    lucyCore.loadPlugin(WorldEditorPlugin.id);
    lucyCore.loadPlugin(PathfindingSolverPlugin.id);
    lucyCore.loadPlugin(AssetGeneratorPlugin.id);
  }, []);

  // Sync plugins state for the UI manager
  const [uiPlugins, setUiPlugins] = useState(lucyCore.getPlugins());
  
  useEffect(() => {
    if (showPluginManager) {
      // Refresh list when modal opens
      setUiPlugins(lucyCore.getPlugins());
    }
  }, [showPluginManager]);

  const togglePlugin = (id: string) => {
    const plugin = uiPlugins.find(p => p.id === id);
    if (plugin) {
      if (plugin.status === 'loaded') {
        lucyCore.unloadPlugin(id);
      } else {
        lucyCore.loadPlugin(id);
      }
      setUiPlugins(lucyCore.getPlugins());
    }
  };

  const layers: { id: LayerType; icon: any; label: string }[] = [
    { id: 'geometry', icon: Box, label: 'Geometry' },
    { id: 'albedo', icon: ImageIcon, label: 'Albedo' },
    { id: 'normal', icon: Activity, label: 'Normals' },
    { id: 'wireframe', icon: Layers, label: 'Wireframe' },
    { id: 'lighting', icon: Sun, label: 'Lighting' },
  ];

  const entities = [
    { id: 'World_Root', type: 'Folder', children: [
      { id: 'Global_Illumination', type: 'Lumen' },
      { id: 'Virtualized_Geometry', type: 'Nanite' },
      { id: 'TorusKnot_01', type: 'StaticMesh' },
      { id: 'PointLight_01', type: 'Light' },
      { id: 'Atmosphere_Fog', type: 'Volume' },
    ]}
  ];

  return (
    <div className="h-screen w-screen flex flex-col bg-editor-bg text-editor-text font-sans select-none overflow-hidden">
      {/* Top Toolbar */}
      <header className="h-12 border-b border-editor-border flex items-center justify-between px-4 bg-editor-panel z-50">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 bg-editor-accent rounded flex items-center justify-center">
              <span className="font-display font-bold text-xs">A</span>
            </div>
            <span className="font-display font-semibold tracking-tight text-sm">ALPHA MATRIX <span className="text-editor-accent">ENGINE</span></span>
          </div>
          <div className="h-4 w-[1px] bg-editor-border mx-2" />
          <nav className="flex items-center gap-4 text-xs font-medium text-editor-text-muted">
            <button className="hover:text-editor-text transition-colors">File</button>
            <button className="hover:text-editor-text transition-colors">Edit</button>
            <button className="hover:text-editor-text transition-colors">Window</button>
            <button 
              onClick={() => setShowPluginManager(true)}
              className="hover:text-editor-text transition-colors flex items-center gap-1"
            >
              <Plug size={12} />
              Plugins
            </button>
            <button className="hover:text-editor-text transition-colors">Build</button>
            <button className="hover:text-editor-text transition-colors text-editor-accent">Marketplace</button>
          </nav>
        </div>

        <div className="flex items-center gap-2">
          <button 
            onClick={() => setIsPlaying(!isPlaying)}
            className={cn(
              "flex items-center gap-2 px-4 py-1.5 rounded text-xs font-bold transition-all",
              isPlaying ? "bg-red-500/10 text-red-500 border border-red-500/20" : "bg-editor-accent/10 text-editor-accent border border-editor-accent/20 hover:bg-editor-accent/20"
            )}
          >
            {isPlaying ? <Pause size={14} fill="currentColor" /> : <Play size={14} fill="currentColor" />}
            {isPlaying ? "STOP" : "PLAY"}
          </button>
        </div>

        <div className="flex items-center gap-4">
          <div className="flex items-center gap-3 text-xs font-mono text-editor-text-muted">
            <div className="flex items-center gap-1">
              <Activity size={12} />
              <span>{stats.fps} FPS</span>
            </div>
            <div className="flex items-center gap-1">
              <Database size={12} />
              <span>{stats.triangles.toLocaleString()} TRIS</span>
            </div>
          </div>
          <div className="h-4 w-[1px] bg-editor-border mx-2" />
          <Settings2 size={16} className="text-editor-text-muted hover:text-editor-text cursor-pointer" />
        </div>
      </header>

      <main className="flex-1 flex overflow-hidden">
        {/* Left Sidebar: Outliner */}
        <aside className="w-64 border-r border-editor-border bg-editor-panel flex flex-col">
          <div className="p-3 border-b border-editor-border flex items-center justify-between">
            <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-editor-text-muted">
              <FolderTree size={14} />
              Outliner
            </div>
            <Search size={14} className="text-editor-text-muted" />
          </div>
          <div className="flex-1 overflow-y-auto p-2">
            {entities.map(group => (
              <div key={group.id} className="space-y-1">
                <div className="flex items-center gap-1 p-1 text-xs font-medium text-editor-text-muted">
                  <ChevronRight size={14} />
                  <span>{group.id}</span>
                </div>
                <div className="pl-4 space-y-0.5">
                  {group.children.map(child => (
                    <div 
                      key={child.id}
                      onClick={() => setSelectedEntity(child.id)}
                      className={cn(
                        "flex items-center justify-between p-1.5 rounded text-xs cursor-pointer transition-colors",
                        selectedEntity === child.id ? "bg-editor-accent/20 text-editor-accent" : "hover:bg-white/5"
                      )}
                    >
                      <div className="flex items-center gap-2">
                        <Box size={12} />
                        <span>{child.id}</span>
                      </div>
                      <span className="text-[10px] opacity-50">{child.type}</span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </aside>

        {/* Center: Viewport & Content Browser */}
        <div className="flex-1 flex flex-col overflow-hidden relative">
          {/* Main Viewport */}
          <div className="flex-1 relative">
            <Viewport 
              activeLayer={activeLayer} 
              onStatsUpdate={setStats} 
              rayTracingEnabled={rayTracingEnabled}
            />
            
            {/* Viewport Overlays */}
            <div className="absolute top-4 right-4 flex flex-col gap-2">
              {layers.map(layer => (
                <button
                  key={layer.id}
                  onClick={() => setActiveLayer(layer.id)}
                  className={cn(
                    "w-10 h-10 rounded-lg flex items-center justify-center transition-all backdrop-blur-md border",
                    activeLayer === layer.id 
                      ? "bg-editor-accent text-white border-editor-accent shadow-lg shadow-editor-accent/20" 
                      : "bg-black/40 text-editor-text-muted border-editor-border hover:bg-black/60 hover:text-editor-text"
                  )}
                  title={layer.label}
                >
                  <layer.icon size={18} />
                </button>
              ))}
            </div>

            <div className="absolute bottom-4 left-4 flex gap-2">
              <div className="bg-black/60 backdrop-blur-md border border-editor-border px-3 py-1.5 rounded text-[10px] font-mono flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                VULKAN 1.3 | SPIR-V | 8K_NATIVE
              </div>
            </div>
          </div>

          {/* Bottom Panel: Content Browser / Console / Cognitive */}
          <div className="h-72 border-t border-editor-border bg-editor-panel flex flex-col">
            <div className="flex items-center border-b border-editor-border px-2">
              <button 
                onClick={() => setActiveBottomTab('content')}
                className={cn("px-4 py-2 text-xs font-bold border-b-2 transition-colors", activeBottomTab === 'content' ? "border-editor-accent text-editor-text" : "border-transparent text-editor-text-muted hover:text-editor-text")}
              >
                Content Browser
              </button>
              <button 
                onClick={() => setActiveBottomTab('log')}
                className={cn("px-4 py-2 text-xs font-bold border-b-2 transition-colors", activeBottomTab === 'log' ? "border-editor-accent text-editor-text" : "border-transparent text-editor-text-muted hover:text-editor-text")}
              >
                Output Log
              </button>
              <button 
                onClick={() => setActiveBottomTab('cognitive')}
                className={cn("px-4 py-2 text-xs font-bold border-b-2 transition-colors flex items-center gap-1.5", activeBottomTab === 'cognitive' ? "border-purple-500 text-purple-400" : "border-transparent text-editor-text-muted hover:text-editor-text")}
              >
                <Brain size={12} />
                Cognitive Microscope
              </button>
            </div>
            
            <div className="flex-1 overflow-hidden">
              {activeBottomTab === 'content' && (
                <div className="h-full p-4 grid grid-cols-6 gap-4 overflow-y-auto">
                  {[1,2,3,4,5,6,7,8].map(i => (
                    <div key={i} className="group cursor-pointer">
                      <div className="aspect-square bg-editor-bg border border-editor-border rounded-lg flex flex-col items-center justify-center gap-2 group-hover:border-editor-accent transition-colors overflow-hidden relative">
                        <div className="absolute inset-0 bg-gradient-to-br from-editor-accent/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
                        {i % 3 === 0 ? <Code2 size={24} className="text-editor-text-muted" /> : <Box size={24} className="text-editor-text-muted" />}
                        <div className="text-[10px] font-medium text-editor-text-muted group-hover:text-editor-text">
                          {i % 3 === 0 ? `Script_${i}.lua` : `Mesh_LOD_${i}`}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
              
              {activeBottomTab === 'log' && (
                <div className="h-full p-4 font-mono text-[10px] text-editor-text-muted overflow-y-auto space-y-1">
                  <div>[System] Alpha Matrix Engine initialized.</div>
                  <div>[Renderer] Vulkan 1.3 backend active.</div>
                  <div className="text-yellow-500">[Warning] Missing texture map for TorusKnot_01.</div>
                </div>
              )}

              {activeBottomTab === 'cognitive' && (
                <CognitiveMicroscope />
              )}
            </div>
          </div>
        </div>

        {/* Right Sidebar: Details / Inspector / Forge */}
        <aside className="w-80 border-l border-editor-border bg-editor-panel flex flex-col">
          <div className="flex items-center border-b border-editor-border bg-editor-bg">
            <button 
              onClick={() => setActiveRightTab('details')}
              className={cn(
                "flex-1 p-3 text-[10px] font-bold uppercase tracking-wider transition-colors border-b-2",
                activeRightTab === 'details' ? "border-editor-accent text-editor-text" : "border-transparent text-editor-text-muted hover:text-editor-text"
              )}
            >
              Details
            </button>
            <button 
              onClick={() => setActiveRightTab('forge')}
              className={cn(
                "flex-1 p-3 text-[10px] font-bold uppercase tracking-wider transition-colors border-b-2 flex items-center justify-center gap-2",
                activeRightTab === 'forge' ? "border-amber-500 text-amber-400" : "border-transparent text-editor-text-muted hover:text-editor-text"
              )}
            >
              <Sparkles size={12} />
              AI Forge
            </button>
          </div>

          <div className="flex-1 overflow-hidden">
            {activeRightTab === 'details' ? (
              selectedEntity ? (
                <div className="h-full overflow-y-auto p-4 space-y-6">
                  <section>
                    <div className="text-[10px] font-bold text-editor-text-muted uppercase mb-3 flex items-center gap-2">
                      <Maximize2 size={10} /> Transform
                    </div>
                    <div className="space-y-2">
                      {['Location', 'Rotation', 'Scale'].map(label => (
                        <div key={label} className="grid grid-cols-4 items-center gap-2">
                          <span className="text-[10px] text-editor-text-muted">{label}</span>
                          <div className="col-span-3 grid grid-cols-3 gap-1">
                            {['X', 'Y', 'Z'].map(axis => (
                              <div key={axis} className="bg-editor-bg border border-editor-border rounded px-1 py-0.5 flex items-center gap-1">
                                <span className="text-[8px] font-bold text-editor-text-muted">{axis}</span>
                                <input type="text" defaultValue="0.0" className="bg-transparent w-full text-[10px] outline-none font-mono" />
                              </div>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  </section>

                  <section>
                    <div className="text-[10px] font-bold text-editor-text-muted uppercase mb-3 flex items-center gap-2">
                      <Zap size={10} /> Matrix Pipeline
                    </div>
                    <div className="space-y-3">
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] text-editor-text-muted">Virtualized Geometry</span>
                        <div className="w-8 h-4 bg-editor-accent rounded-full relative">
                          <div className="absolute right-1 top-1 w-2 h-2 bg-white rounded-full" />
                        </div>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] text-editor-text-muted">8K Texture Streaming</span>
                        <div className="w-8 h-4 bg-editor-accent rounded-full relative">
                          <div className="absolute right-1 top-1 w-2 h-2 bg-white rounded-full" />
                        </div>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] text-editor-text-muted">Dynamic GI (Lumen)</span>
                        <div className="w-8 h-4 bg-editor-border rounded-full relative">
                          <div className="absolute left-1 top-1 w-2 h-2 bg-editor-text-muted rounded-full" />
                        </div>
                      </div>
                      <div className="flex items-center justify-between">
                        <div className="flex flex-col">
                          <span className="text-[10px] text-editor-text-muted">Real-time Ray Tracing</span>
                          <span className="text-[8px] text-editor-accent font-mono uppercase">Vulkan RT Extension</span>
                        </div>
                        <button 
                          onClick={() => setRayTracingEnabled(!rayTracingEnabled)}
                          className={cn(
                            "w-8 h-4 rounded-full relative transition-colors",
                            rayTracingEnabled ? "bg-editor-accent" : "bg-editor-border"
                          )}
                        >
                          <motion.div 
                            animate={{ x: rayTracingEnabled ? 16 : 0 }}
                            className={cn(
                              "absolute left-1 top-1 w-2 h-2 rounded-full transition-colors",
                              rayTracingEnabled ? "bg-white" : "bg-editor-text-muted"
                            )}
                          />
                        </button>
                      </div>
                    </div>
                  </section>

                  <section>
                    <div className="text-[10px] font-bold text-editor-text-muted uppercase mb-3">Material Layers</div>
                    <div className="aspect-video bg-editor-bg border border-editor-border rounded-lg flex items-center justify-center relative overflow-hidden group">
                      <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent" />
                      <span className="text-[10px] font-mono z-10">M_TorusKnot_PBR</span>
                      <div className="absolute bottom-2 right-2 w-6 h-6 bg-editor-accent rounded border border-white/20" />
                    </div>
                  </section>
                </div>
              ) : (
                <div className="h-full flex items-center justify-center text-xs text-editor-text-muted italic">
                  Select an entity to view details
                </div>
              )
            ) : (
              <AIAssetForge />
            )}
          </div>
        </aside>
      </main>

      {/* Footer Status Bar */}
      <footer className="h-6 border-t border-editor-border bg-editor-panel flex items-center justify-between px-3 text-[10px] font-medium text-editor-text-muted">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-1.5">
            <div className="w-2 h-2 rounded-full bg-green-500" />
            <span>Engine Ready</span>
          </div>
          <div className="flex items-center gap-1.5">
            <Terminal size={10} />
            <span>Compiled SPIR-V shaders (124)</span>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <span>Memory: 1.2GB / 16GB</span>
          <span>VRAM: 4.5GB / 24GB</span>
          <span className="text-editor-accent">v0.1.0-alpha.build.2026</span>
        </div>
      </footer>

      {/* Plugin Manager Modal */}
      <AnimatePresence>
        {showPluginManager && (
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-sm"
          >
            <motion.div 
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="w-[600px] bg-editor-panel border border-editor-border rounded-lg shadow-2xl flex flex-col overflow-hidden"
            >
              {/* Modal Header */}
              <div className="h-12 border-b border-editor-border flex items-center justify-between px-4 bg-editor-bg">
                <div className="flex items-center gap-2 text-sm font-bold">
                  <Plug size={16} className="text-editor-accent" />
                  Plugin Manager
                </div>
                <button 
                  onClick={() => setShowPluginManager(false)}
                  className="text-editor-text-muted hover:text-editor-text transition-colors"
                >
                  <X size={16} />
                </button>
              </div>

              {/* Modal Body */}
              <div className="p-4 flex flex-col gap-4">
                <div className="flex items-center justify-between">
                  <div className="text-xs text-editor-text-muted">
                    Manage runtime plugins (.dll / .so) via Lucy Core
                  </div>
                </div>

                <div className="border border-editor-border rounded-lg overflow-hidden bg-editor-bg">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-editor-panel border-b border-editor-border text-editor-text-muted">
                      <tr>
                        <th className="px-4 py-2 font-medium">Status</th>
                        <th className="px-4 py-2 font-medium">Name</th>
                        <th className="px-4 py-2 font-medium">Version</th>
                        <th className="px-4 py-2 font-medium">File</th>
                        <th className="px-4 py-2 font-medium text-right">Action</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-editor-border">
                      {uiPlugins.map(plugin => (
                        <tr key={plugin.id} className="hover:bg-white/5 transition-colors">
                          <td className="px-4 py-3">
                            {plugin.status === 'loaded' ? (
                              <div className="flex items-center gap-1.5 text-green-500">
                                <CheckCircle2 size={14} />
                                <span>Loaded</span>
                              </div>
                            ) : plugin.status === 'error' ? (
                              <div className="flex items-center gap-1.5 text-red-500">
                                <AlertCircle size={14} />
                                <span>Error</span>
                              </div>
                            ) : (
                              <div className="flex items-center gap-1.5 text-editor-text-muted">
                                <div className="w-3.5 h-3.5 rounded-full border-2 border-current opacity-50" />
                                <span>Unloaded</span>
                              </div>
                            )}
                          </td>
                          <td className="px-4 py-3 font-medium">
                            <div>{plugin.name}</div>
                            <div className="text-[10px] text-editor-text-muted font-normal">{plugin.category}</div>
                          </td>
                          <td className="px-4 py-3 text-editor-text-muted">{plugin.version}</td>
                          <td className="px-4 py-3 font-mono text-[10px] text-editor-text-muted">{plugin.id}.dll</td>
                          <td className="px-4 py-3 text-right">
                            <button 
                              onClick={() => togglePlugin(plugin.id)}
                              className={cn(
                                "px-3 py-1 rounded text-[10px] font-bold transition-colors",
                                plugin.status === 'loaded' 
                                  ? "bg-red-500/10 text-red-500 hover:bg-red-500/20" 
                                  : "bg-editor-accent/10 text-editor-accent hover:bg-editor-accent/20"
                              )}
                            >
                              {plugin.status === 'loaded' ? 'UNLOAD' : 'LOAD'}
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
              
              {/* Modal Footer */}
              <div className="p-3 border-t border-editor-border bg-editor-bg text-[10px] text-editor-text-muted flex items-center justify-between">
                <span>Hot-reloading enabled for loaded modules.</span>
                <span>{uiPlugins.filter(p => p.status === 'loaded').length} Active Plugins</span>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
