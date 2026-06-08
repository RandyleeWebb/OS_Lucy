import React, { useState, useEffect, useRef } from "react";
import { Rnd } from "react-rnd";
import { motion, AnimatePresence } from "motion/react";
import {
  Shield, Terminal, Activity, Settings, Music, Globe, Folder, Brain, Bot, 
  Bell, Cloud, Search, Newspaper, Compass, BookOpen, Minimize2, Maximize2, X, AlertCircle,
  Command, HardDrive, Server, Wifi, Lock, Play, Pause
} from "lucide-react";
import dynamic from 'next/dynamic';
import axios from 'axios';
import TerminalWindow from './TerminalWindow';
import AgentWedgit from './wedgits/AgentWedgit';
import ReplicationDock from './wedgits/ReplicationDock';
import AnalyzerWedgit from './wedgits/AnalyzerWedgit';
import SafeGuardInjector from './wedgits/SafeGuardInjector';
import './wedgits/styles.css';

// --- TYPES ---
export interface OSWindow {
  id: string;
  appId: string;
  title: string;
  x: number;
  y: number;
  width: number | string;
  height: number | string;
  minimized: boolean;
  maximized: boolean;
  zIndex: number;
}

export interface AppDefinition {
  id: string;
  name: string;
  icon: JSX.Element;
  component: React.FC<{ win: OSWindow; onClose: () => void }>;
  defaultWidth?: number;
  defaultHeight?: number;
}

// --- DESKTOP SHELL ---
export default function LucyVerseDesktop() {
  const [windows, setWindows] = useState<OSWindow[]>([]);
  const [apiClient, setApiClient] = useState(() => axios);
  const [activeWorkspace, setActiveWorkspace] = useState("Development");
  const [searchOpen, setSearchOpen] = useState(false);
  const [nextZ, setNextZ] = useState(10);
  const [toasts, setToasts] = useState<{id:string, title:string, message:string}[]>([])

  // toast helper
  const showToast = (title: string, message: string) => {
    const id = `t-${Date.now()}`
    setToasts(prev => [...prev, {id, title, message}])
    setTimeout(()=>{
      setToasts(prev => prev.filter(t => t.id !== id))
    }, 6000)
  }

  // helper to update agent state store (simple local map for now)
  const [agentStates, setAgentStates] = useState<Record<string, any>>({})
  const setAgentState = (agentId: string, patch: any) => {
    setAgentStates(prev => ({ ...prev, [agentId]: { ...(prev[agentId]||{}), ...patch } }))
  }

  const togglePerf = async (agentId: string, start: boolean) => {
    // For simulation, we write a perfmon entry to datavault with agent_id when starting
    try{
      if(start){
        // mark running locally
        setAgentState(agentId, { perfRunning: true })
        // write a simulated perf sample
        await fetch('/datavault/log', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({source:'perfmon', payload:{cpu: Math.floor(Math.random()*50)+1, mem: Math.floor(Math.random()*50)+1, agent_id: agentId}})})
        // refresh telemetry
        const res = await fetch(`/datavault/entries?source=perfmon&limit=5&agent_id=${encodeURIComponent(agentId)}`)
        const j = await res.json().catch(()=>({entries:[]}))
        setAgentState(agentId, { telemetry: j.entries || [] })
      }else{
        setAgentState(agentId, { perfRunning: false })
      }
    }catch(e){
      console.error(e)
    }
  }

  // Global Hotkey (Cmd/Ctrl + Space)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.code === "Space") {
        e.preventDefault();
        setSearchOpen((prev) => !prev);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  const openApp = (appId: string) => {
    const appDef = APPLICATIONS.find(a => a.id === appId);
    if (!appDef) return;

    // Check if already open
    const existing = windows.find(w => w.appId === appId);
    if (existing) {
      focusWindow(existing.id);
      if (existing.minimized) toggleMinimize(existing.id);
      return;
    }

    const newWin: OSWindow = {
      id: `${appId}-${Date.now()}`,
      appId,
      title: appDef.name,
      x: window.innerWidth / 2 - (appDef.defaultWidth || 800) / 2 + (Math.random() * 40 - 20),
      y: window.innerHeight / 2 - (appDef.defaultHeight || 600) / 2 + (Math.random() * 40 - 20),
      width: appDef.defaultWidth || 800,
      height: appDef.defaultHeight || 600,
      minimized: false,
      maximized: false,
      zIndex: nextZ,
    };
    setNextZ(nextZ + 1);
    setWindows([...windows, newWin]);
  };

  const closeWindow = (id: string) => {
    setWindows(windows.filter(w => w.id !== id));
  };

  const focusWindow = (id: string) => {
    setWindows(windows.map(w => w.id === id ? { ...w, zIndex: nextZ } : w));
    setNextZ(nextZ + 1);
  };

  const toggleMinimize = (id: string) => {
    setWindows(windows.map(w => w.id === id ? { ...w, minimized: !w.minimized } : w));
  };

  const toggleMaximize = (id: string) => {
    setWindows(windows.map(w => w.id === id ? { ...w, maximized: !w.maximized } : w));
  };

  const updateWindowPos = (id: string, x: number, y: number, width: number | string, height: number | string) => {
    setWindows(windows.map(w => w.id === id ? { ...w, x, y, width, height } : w));
  };

  return (
    <div className="flex flex-col h-screen w-full bg-slate-950 text-slate-200 overflow-hidden font-sans relative selection:bg-indigo-500/30">
      {/* Background Gradient & Ambient Glows */}
      <div className="absolute inset-0 bg-gradient-to-br from-slate-900 via-slate-950 to-slate-900 pointer-events-none"></div>
      
      {/* Pulse / Ambient Activity Indicators */}
      <div className="absolute top-1/4 left-1/4 w-[500px] h-[500px] bg-indigo-500/10 rounded-full blur-[120px] pointer-events-none animate-pulse"></div>
      <div className="absolute bottom-1/4 right-1/4 w-[400px] h-[400px] bg-purple-500/10 rounded-full blur-[100px] pointer-events-none animate-pulse" style={{ animationDelay: '2s' }}></div>

      {/* TOP SYSTEM BAR */}
      <TopBar activeWorkspace={activeWorkspace} setActiveWorkspace={setActiveWorkspace} onSearchClick={() => setSearchOpen(true)} />

      {/* DESKTOP CANVAS */}
      <div className="flex-1 relative overflow-hidden" id="desktop-canvas">
        {windows.map((win) => {
          if (win.minimized) return null;
          const AppRenderer = APPLICATIONS.find(a => a.id === win.appId)?.component;
          if (!AppRenderer) return null;

          return (
            <WindowContainer
              key={win.id}
              win={win}
              onClose={() => closeWindow(win.id)}
              onFocus={() => focusWindow(win.id)}
              onMinimize={() => toggleMinimize(win.id)}
              onMaximize={() => toggleMaximize(win.id)}
              onUpdate={updateWindowPos}
            >
              <AppRenderer win={win} onClose={() => closeWindow(win.id)} />
            </WindowContainer>
          );
        })}

        {/* Auxiliary wedgits panel (keeps imports in use and provides stable layout after edits) */}
        <div className="absolute bottom-24 left-8 pointer-events-none">
          <div className="flex gap-3 pointer-events-auto">
            <div style={{display:'flex', flexDirection:'column', gap:8}}>
              <div style={{display:'flex', gap:8}} className="clones-container">
                <AgentWedgit id="agent-1" label="Agent A" state={agentStates['agent-1'] || {}} />
                {/* Render clones here */}
                {(agentStates['clones'] || []).map((c:any)=> (
                  <div key={c.id} className={`clone-item enter`}>
                    <div className={agentStates[c.id]?.glow ? 'replication-glow' : ''}>
                      <AgentWedgit id={c.id} label={c.label} state={{...c.state, ...agentStates[c.id]}} />
                    </div>
                  </div>
                ))}
                {/* Analyzer telemetry overlays for linked agents */}
                {(agentStates['clones'] || []).map((c:any)=> (
                  (agentStates[c.id] && agentStates[c.id].linked) ? (
                    <div key={`${c.id}-telemetry`} style={{position:'absolute', top:'100%', left:0, marginTop:8}}>
                      <div style={{fontSize:11, color:'#9CA3AF'}}>Telemetry</div>
                      <div style={{display:'flex', alignItems:'center', gap:8, marginTop:6}}>
                        <div style={{fontSize:12, color:'#D1D5DB'}}>
                          {(agentStates[c.id].telemetry || []).slice(0,3).map((e:any, i:number)=> (
                            <div key={i}>CPU: {e.record.payload.cpu} MEM: {e.record.payload.mem}</div>
                          ))}
                        </div>
                        <div style={{display:'flex', gap:6}}>
                          {agentStates[c.id].perfRunning ? (
                            <button onClick={() => togglePerf(c.id, false)} className="px-2 py-1 bg-rose-600 rounded text-xs"> <Pause size={12}/> Stop</button>
                          ) : (
                            <button onClick={() => togglePerf(c.id, true)} className="px-2 py-1 bg-emerald-600 rounded text-xs"> <Play size={12}/> Start</button>
                          )}
                        </div>
                      </div>
                    </div>
                  ) : null
                ))}
              </div>
            </div>
            <ReplicationDock onDropAgent={async (agentId: string) => {
              try {
                // call orchestrator replication endpoint (proxied) and read response for UI feedback
                const res = await fetch('/orchestrator/replicate', {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({ agent_id: agentId })
                });
                const j = await res.json().catch(() => ({ ok: res.ok, status: res.status }));
                if (j && j.ok) {
                  // show replication glow / create cloned widget (currently logged for future UI hook)
                  console.log('replication success', j);
                  const entryHash = j.datavault?.entry_hash || j.datavault?.entryHash || null
                  setAgentState(agentId, { replicated: true })
                  // create a clone entry in agentStates.clones
                  const cloneId = `${agentId}-clone-${Date.now()}`
                  const clone = { id: cloneId, label: `${agentId}-clone`, state: { replicated:true } }
                  setAgentState('clones', [...(agentStates['clones']||[]), clone])
                  // add temporary glow
                  setAgentState(cloneId, { glow: true })
                  setTimeout(()=> setAgentState(cloneId, { glow: false }), 1200)
                  showToast('Replication succeeded', `Replicated ${agentId} - DataVault: ${entryHash || 'n/a'}`)
                } else {
                  console.warn('replication failed', j);
                  if (j && j.datavault) {
                    const decision = j.audit?.decision || 'deny'
                    const entryHash = j.datavault?.entry_hash || j.datavault?.entryHash || null
                    const reason = j.audit?.reason || null
                    setAgentState(agentId, { alert: true, safeguard: { decision, entry: entryHash, reason } })
                    showToast('Replication blocked', `SafeGuard denied replication for ${agentId} - DataVault: ${entryHash || 'n/a'}`)
                  } else {
                    showToast('Replication blocked', `SafeGuard denied replication for ${agentId}`)
                  }
                }
              } catch (err) {
                console.error(err);
              }
            }} />
            <AnalyzerWedgit onBindAgent={async (agentId: string) => {
              try {
                // Fetch recent datavault perfmon entries for this agent
                const res = await fetch(`/datavault/entries?source=perfmon&limit=10&agent_id=${encodeURIComponent(agentId)}`);
                const j = await res.json().catch(() => ({ ok: res.ok, status: res.status }));
                console.log('analyzer bound, recent perfmon entries for', agentId, j);
                // link analyzer visually to agent and store recent telemetry
                setAgentState(agentId, { linked: true, telemetry: j.entries || [] })
              } catch (err) {
                console.error(err);
              }
            }} />
            <SafeGuardInjector onAttach={async (agentId: string) => {
              try {
                const res = await fetch('/safeguard/audit', {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({ agent_id: agentId, action: 'attach_safeguard' })
                });
                const j = await res.json().catch(() => ({ ok: res.ok, status: res.status }));
                // update AgentWedgit state to reflect safeguard decision
                console.log('safeguard attach', agentId, j);
                if (j) {
                  const decision = j.decision || (j.audit && j.audit.decision) || 'allow'
                  const entryHash = (j.datavault && (j.datavault.entry_hash || j.datavault.entryHash)) || null
                  const reason = j.reason || (j.audit && j.audit.reason) || ''
                  // set visual state
                  setAgentState(agentId, { locked: true, safeguard: { decision, entry: entryHash, reason } })
                  showToast(decision === 'allow' ? 'SafeGuard allowed' : 'SafeGuard denied', `DataVault: ${entryHash || 'n/a'}`)
                }
              } catch (err) {
                console.error(err);
              }
            }} />
          </div>
        </div>

        {/* toasts */}
        <div className="absolute top-20 right-8 flex flex-col gap-2 z-50 pointer-events-none">
          {toasts.map(t => (
            <div key={t.id} className="bg-black/80 text-white px-3 py-2 rounded pointer-events-auto shadow-lg"> 
              <div className="font-semibold">{t.title}</div>
              <div className="text-xs text-slate-300">{t.message}</div>
            </div>
          ))}
        </div>

        {windows.length === 0 && (
          <div className="absolute inset-0 flex items-center justify-center opacity-30 pointer-events-none">
            <span className="text-5xl font-light tracking-[0.3em] text-white select-none">
              LUCY OS
            </span>
          </div>
        )}
      </div>

      {/* AGENT PRESENCE PANEL (Right Side) */}
      <AgentPresencePanel />

      {/* BOTTOM DOCK */}
      <BottomDock windows={windows} openApp={openApp} toggleMinimize={toggleMinimize} focusWindow={focusWindow} />

      {/* SEARCH EVERYWHERE / COMMAND PALETTE */}
      <AnimatePresence>
        {searchOpen && <SearchEverywhere onClose={() => setSearchOpen(false)} openApp={openApp} />}
      </AnimatePresence>
    </div>
  );
}

// --- TOP BAR ---
function TopBar({ activeWorkspace, setActiveWorkspace, onSearchClick }: any) {
  const [time, setTime] = useState(new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }));
  const workspaces = ["Development", "Research", "Music", "Security"];
  
  useEffect(() => {
    const timer = setInterval(() => setTime(new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })), 1000);
    return () => clearInterval(timer);
  }, []);

  return (
    <div className="h-9 bg-slate-950/60 backdrop-blur-xl border-b border-white/[0.05] flex items-center justify-between px-4 text-xs font-medium text-slate-300 z-50 relative shadow-sm">
      <div className="flex items-center gap-6">
         <div className="flex items-center gap-2 text-white font-bold tracking-wide">
           <Shield size={14} className="text-white drop-shadow-[0_0_8px_rgba(255,255,255,0.8)]" />
           <span>LucyVerse</span>
         </div>
         <div className="flex items-center gap-4">
           {workspaces.map(ws => (
              <span 
                key={ws} 
                onClick={() => setActiveWorkspace(ws)}
                className={`cursor-pointer transition-colors ${activeWorkspace === ws ? 'text-white font-semibold' : 'text-slate-500 hover:text-slate-300'}`}
              >
                {ws}
              </span>
           ))}
         </div>
      </div>

      <div onClick={onSearchClick} className="absolute left-1/2 -translate-x-1/2 flex items-center gap-2 px-3 hover:bg-white/5 rounded border border-transparent hover:border-white/10 transition-colors cursor-text text-slate-400 w-64 justify-center h-6">
         <Search size={12} />
         <span>Search Everywhere (⌘ Space)</span>
      </div>

      <div className="flex items-center gap-5">
        <div className="flex items-center gap-2 cursor-pointer hover:text-white transition-colors">
          <AlertCircle size={14} className="text-emerald-400" />
          <span>Sentinel: Active</span>
        </div>
        <div className="cursor-pointer hover:text-white transition-colors flex items-center gap-2">
          <span>{time}</span>
        </div>
      </div>
    </div>
  );
}

// --- AGENT PRESENCE PANEL ---
function AgentPresencePanel() {
  const agents = [
    { name: "Emma", status: "Active", color: "bg-emerald-400" },
    { name: "Lucy", status: "Active", color: "bg-emerald-400" },
    { name: "Forge", status: "Building", color: "bg-blue-400", pulse: true },
    { name: "Scout", status: "Searching", color: "bg-amber-400" },
    { name: "Sentinel", status: "Monitoring", color: "bg-rose-400" },
    { name: "DJ", status: "Idle", color: "bg-slate-500" },
  ];

  return (
    <div className="absolute right-4 top-16 w-64 flex flex-col gap-2 z-40 pointer-events-none">
      {agents.map((ag) => (
        <div key={ag.name} className="bg-slate-900/40 backdrop-blur border border-white/5 p-3 rounded-xl flex items-center justify-between shadow-lg pointer-events-auto hover:bg-slate-900/60 transition-colors">
           <span className="text-sm font-semibold text-slate-200">{ag.name}</span>
           <div className="flex items-center gap-2">
             <span className="text-[10px] uppercase tracking-widest text-slate-500 font-bold">{ag.status}</span>
             <div className={`w-2 h-2 rounded-full ${ag.color} ${ag.pulse ? 'animate-pulse drop-shadow-[0_0_5px_rgba(255,255,255,0.6)]' : ''}`}></div>
           </div>
        </div>
      ))}
    </div>
  );
}

// --- BOTTOM DOCK ---
function BottomDock({ windows, openApp, toggleMinimize, focusWindow }: any) {
  const dockApps = ["lucy", "files", "browser", "dj", "memory", "agents"];

  return (
    <div className="absolute bottom-4 left-1/2 -translate-x-1/2 bg-slate-900/40 backdrop-blur-2xl border border-white/10 shadow-2xl p-2 rounded-3xl flex gap-2 z-50">
      {dockApps.map((id) => {
        const app = APPLICATIONS.find(a => a.id === id);
        if (!app) return null;
        
        const isOpen = windows.some((w: any) => w.appId === app.id);
        const isMinimized = windows.some((w: any) => w.appId === app.id && w.minimized);
        
        return (
          <div
            key={app.id}
            onClick={() => {
               if (isOpen && !isMinimized) {
                  openApp(app.id); 
               } else {
                  openApp(app.id);
               }
            }}
            className={`relative group p-3 flex items-center justify-center w-14 h-14 rounded-2xl cursor-pointer transition-all duration-300 hover:-translate-y-2 hover:scale-110 ${isOpen ? 'bg-white/10 shadow-inner' : 'hover:bg-white/5'}`}
          >
            <div className={`text-slate-200 drop-shadow-md transition-transform duration-300 ${isOpen ? 'scale-110' : ''}`}>
              {app.icon}
            </div>
            {isOpen && (
              <div className={`absolute -bottom-1.5 left-1/2 -translate-x-1/2 w-1 h-1 rounded-full ${isMinimized ? 'bg-slate-500' : 'bg-emerald-400 drop-shadow-[0_0_3px_rgba(52,211,153,0.8)]'}`}></div>
            )}
            {/* Tooltip */}
            <div className="absolute -top-12 left-1/2 -translate-x-1/2 bg-slate-800/90 backdrop-blur text-white text-xs px-3 py-1.5 rounded-lg opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity whitespace-nowrap shadow-xl font-medium tracking-wide">
              {app.name}
            </div>
          </div>
        );
      })}
    </div>
  );
}

// --- SEARCH EVERYWHERE ---
function SearchEverywhere({ onClose, openApp }: any) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [query, setQuery] = useState("");
  
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const MOCK_DATA = [
    { id: '1', type: 'app', title: 'Lucy Console', subtitle: 'Chat with Lucy', icon: <Terminal size={18} className="text-indigo-400" />, action: () => openApp("lucy") },
    { id: '2', type: 'app', title: 'Memory Galaxy', subtitle: 'Explore Semantic Memory', icon: <Brain size={18} className="text-purple-400" />, action: () => openApp("memory") },
    { id: '3', type: 'app', title: 'Security Fabric', subtitle: 'Review Sentinel Logs', icon: <Shield size={18} className="text-rose-400" />, action: () => openApp("security") },
    { id: '4', type: 'app', title: 'OS Namespace', subtitle: 'Cloud Execution Mounts', icon: <Folder size={18} className="text-slate-400" />, action: () => openApp("files") },
    { id: '5', type: 'app', title: 'System Monitor', subtitle: 'View Active Processes', icon: <Activity size={18} className="text-emerald-400" />, action: () => openApp("monitor") },
    { id: '6', type: 'app', title: 'Agent Browser', subtitle: 'OS Native Sandboxed Engine', icon: <Globe size={18} className="text-blue-400" />, action: () => openApp("browser") },
    { id: '7', type: 'app', title: 'Music Studio', subtitle: 'Generative Audio Studio', icon: <Music size={18} className="text-pink-400" />, action: () => openApp("dj") },
    { id: '7b', type: 'app', title: 'Authority Plane', subtitle: 'Local Identity & Override', icon: <Command size={18} className="text-amber-400" />, action: () => openApp("authority") },
    { id: '7c', type: 'app', title: 'Agent Center', subtitle: 'Multi-Agent Operations', icon: <Bot size={18} className="text-emerald-400" />, action: () => openApp("agents") },
    
    { id: '8', type: 'file', title: 'project_aurora_spec.md', subtitle: 'Document in /lucy/workspaces/aurora', icon: <Folder size={18} className="text-amber-400" />, action: () => openApp("files") },
    { id: '9', type: 'file', title: 'aegis_firewall_rules.json', subtitle: 'Document in /lucy/home/config', icon: <Shield size={18} className="text-rose-400" />, action: () => openApp("files") },
    
    { id: '10', type: 'memory', title: 'User prefers dark mode interfaces', subtitle: 'Semantic Memory Node', icon: <Brain size={18} className="text-purple-400" />, action: () => openApp("memory") },
    { id: '11', type: 'memory', title: 'Last checked system security at 14:00', subtitle: 'Episodic Memory Sequence', icon: <Brain size={18} className="text-purple-400" />, action: () => openApp("memory") },

    { id: '12', type: 'conversation', title: 'Discussing the new UI layout with Lucy', subtitle: 'Chat History', icon: <Terminal size={18} className="text-indigo-400" />, action: () => openApp("lucy") },
  ];

  const results = MOCK_DATA.filter(item => 
    item.title.toLowerCase().includes(query.toLowerCase()) || 
    item.subtitle.toLowerCase().includes(query.toLowerCase()) ||
    item.type.toLowerCase().includes(query.toLowerCase())
  );

  return (
    <motion.div 
      initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
      className="absolute inset-0 z-[100] flex items-center justify-center bg-slate-950/60 backdrop-blur-sm"
      onClick={onClose}
    >
      <motion.div 
        initial={{ scale: 0.95, y: -20, opacity: 0 }} animate={{ scale: 1, y: 0, opacity: 1 }} exit={{ scale: 0.95, y: -20, opacity: 0 }}
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-2xl bg-slate-900/90 backdrop-blur-3xl border border-white/10 rounded-2xl shadow-2xl overflow-hidden flex flex-col font-sans max-h-[80vh]"
      >
         <div className="flex items-center border-b border-white/10 px-6 py-4 gap-4">
            <Search size={24} className="text-indigo-400" />
            <input 
              ref={inputRef}
              type="text" 
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="flex-1 bg-transparent border-none outline-none text-xl text-white placeholder-slate-500 font-light"
              placeholder="Ask LucyVerse, search files, or launch apps..."
              onKeyDown={(e) => {
                 if(e.key === "Enter" && results.length > 0) {
                    results[0].action();
                    onClose();
                 }
                 if(e.key === "Escape") onClose();
              }}
            />
         </div>
         <div className="p-2 space-y-1 overflow-y-auto">
            {results.length > 0 ? (
                results.map((item, index) => (
                    <div 
                        key={item.id}
                        className={`flex items-center gap-4 px-6 py-3 hover:bg-white/5 rounded-xl cursor-pointer text-slate-200 transition-colors ${index === 0 && query ? 'bg-white/10' : ''}`}
                        onClick={() => { item.action(); onClose(); }}
                    >
                        {item.icon}
                        <div className="flex flex-col">
                            <span className="font-medium">{item.title}</span>
                            <span className="text-xs text-slate-500 font-medium">{item.subtitle}</span>
                        </div>
                    </div>
                ))
            ) : (
                <div className="px-6 py-8 text-center text-slate-500 flex flex-col items-center justify-center gap-3">
                    <Search size={32} className="opacity-40" />
                    <p>No results found for "{query}"</p>
                </div>
            )}
         </div>
         <div className="bg-white/5 px-6 py-2 text-xs text-slate-500 flex justify-end">
            <span className="font-semibold">↵ Enter</span> &nbsp;to open
         </div>
      </motion.div>
    </motion.div>
  );
}

// --- WINDOW MANAGER COMPONENT ---
function WindowContainer({ win, onClose, onFocus, onMinimize, onMaximize, onUpdate, children }: any) {
  if (win.maximized) {
    return (
      <div 
        className="absolute inset-0 bg-slate-950/90 backdrop-blur-2xl border border-white/10 flex flex-col z-[90] overflow-hidden"
        onMouseDownCapture={onFocus}
      >
         <WindowHeader title={win.title} onClose={onClose} onMinimize={onMinimize} onMaximize={onMaximize} />
         <div className="flex-1 overflow-auto bg-slate-900/20">{children}</div>
      </div>
    );
  }

  return (
    <Rnd
      size={{ width: win.width, height: win.height }}
      position={{ x: win.x, y: win.y }}
      onDragStop={(e, d) => onUpdate(win.id, d.x, d.y, win.width, win.height)}
      onResizeStop={(e, dir, ref, delta, pos) => {
         onUpdate(win.id, pos.x, pos.y, ref.style.width, ref.style.height);
      }}
      minWidth={400}
      minHeight={300}
      bounds="parent"
      dragHandleClassName="window-handle"
      className="bg-slate-950/80 backdrop-blur-3xl border border-white/10 shadow-[0_20px_50px_rgba(0,0,0,0.5)] rounded-2xl flex flex-col overflow-hidden"
      style={{ position: "absolute", zIndex: win.zIndex }}
      onMouseDownCapture={onFocus}
    >
      <WindowHeader title={win.title} onClose={onClose} onMinimize={onMinimize} onMaximize={onMaximize} />
      <div className="flex-1 overflow-auto bg-slate-900/20 relative">{children}</div>
    </Rnd>
  );
}

function WindowHeader({ title, onClose, onMinimize, onMaximize }: any) {
  return (
    <div className="window-handle cursor-grab active:cursor-grabbing h-12 flex items-center px-4 justify-between bg-white/5 shrink-0 transition-colors hover:bg-white/10 group border-b border-white/5">
      <div className="flex items-center gap-2 w-16">
        <button onClick={(e) => { e.stopPropagation(); onClose(); }} className="w-3 h-3 rounded-full bg-slate-600 hover:bg-rose-500 transition-colors flex items-center justify-center group/btn"><X size={8} className="opacity-0 group-hover/btn:opacity-100 text-white"/></button>
        <button onClick={(e) => { e.stopPropagation(); onMinimize(); }} className="w-3 h-3 rounded-full bg-slate-600 hover:bg-amber-500 transition-colors flex items-center justify-center group/btn"><Minimize2 size={8} className="opacity-0 group-hover/btn:opacity-100 text-amber-900"/></button>
        <button onClick={(e) => { e.stopPropagation(); onMaximize(); }} className="w-3 h-3 rounded-full bg-slate-600 hover:bg-emerald-500 transition-colors flex items-center justify-center group/btn"><Maximize2 size={8} className="opacity-0 group-hover/btn:opacity-100 text-emerald-900"/></button>
      </div>
      <span className="font-sans text-sm font-semibold text-slate-300 select-none tracking-wide text-center flex-1">{title}</span>
      <div className="w-16"></div>
    </div>
  );
}

// --- LUCY CONSOLE APP ---
function LucyConsoleApp() {
  const [messages, setMessages] = useState<{text: string, type: string, color: string, rawRole?: string, rawText?: string}[]>([
    { text: "> LUCY SYSTEM ONLINE", type: "system", color: "text-indigo-400" },
    { text: "> Bootstrapping Agent Bus...", type: "system", color: "text-slate-400" },
    { text: "> LLM: Ollama (llama3) → Gemini fallback", type: "system", color: "text-slate-400" },
    { text: "> Emma governance layer: :8010", type: "system", color: "text-slate-400" },
    { text: "> Environment: Desktop OS vNext", type: "system", color: "text-slate-400" },
    { text: "----------------------------------------------------", type: "divider", color: "text-slate-700/50" },
    { text: "> Waiting for command...", type: "system", color: "text-slate-500" },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
        scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || loading) return;
    
    const userMessage = input.trim();
    setMessages(prev => [...prev, { text: `> USER: ${userMessage}`, type: "user", color: "text-emerald-400 font-bold", rawRole: "user", rawText: userMessage }]);
    setInput("");
    setLoading(true);
    
    setMessages(prev => [...prev, { text: `> LUCY: Processing query...`, type: "system", color: "text-indigo-400 font-bold animate-pulse" }]);

    try {
        // Build history to send to server
        const history = messages
            .filter(m => m.rawRole)
            .map(m => ({ role: m.rawRole, text: m.rawText }));
        history.push({ role: "user", text: userMessage });

        const res = await fetch("/api/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ messages: history })
        });
        const data = await res.json();
        
        // Remove the "processing" message
        setMessages(prev => prev.filter(m => !m.text.includes('Processing query...')));
        
        const backendTag = data.backend === "ollama" ? " [ollama]" : data.backend === "gemini" ? " [gemini]" : "";
        const lines = (data.text || "No response generated.").split('\n');
        
        const newMessages = lines.map((line: string, i: number) => {
            if (i === 0) {
                return { text: `> LUCY${backendTag}: ${line}`, type: "lucy", color: "text-indigo-300", rawRole: "lucy", rawText: data.text };
            }
            return { text: `        ${line}`, type: "lucy", color: "text-indigo-300" };
        });
        
        setMessages(prev => [...prev, ...newMessages, { text: "> Waiting for command...", type: "system", color: "text-slate-500 mt-4" }]);

        // If the user typed a shell command starting with $, run it via Emma terminal session
        if (userMessage.startsWith("$ ")) {
            try {
                const cmd = userMessage.slice(2);
                // Try relative path first (works when reverse proxy routes /terminal to Emma)
                let res = await fetch('/terminal/exec', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'x-secret-key': 'lucy-secret' },
                    body: JSON.stringify({ command: cmd })
                });

                if (!res.ok) {
                    // Fallback to explicit Emma host/port
                    const API_BASE = `${location.protocol}//${location.hostname}:8010`;
                    res = await fetch(`${API_BASE}/terminal/exec`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json', 'x-secret-key': 'lucy-secret' },
                        body: JSON.stringify({ command: cmd })
                    });
                }

                const out = await res.json();
                setMessages(prev => [...prev, { text: `> OUTPUT:\n${out.result.stdout || ''}${out.result.stderr || ''}`, type: 'system', color: 'text-slate-400' }]);
            } catch (e) {
                setMessages(prev => [...prev, { text: `> ERROR: ${String(e)}`, type: 'system', color: 'text-rose-500' }]);
            }
        }

    } catch (err) {
        setMessages(prev => prev.filter(m => !m.text.includes('Processing query...')));
        setMessages(prev => [...prev, { text: `> SYSTEM ERROR: Cannot reach Lucy server. Is it running on :3000?`, type: "system", color: "text-rose-500 font-bold" }]);
    } finally {
        setLoading(false);
    }
  };

  return (
      <div className="h-full p-6 font-mono text-[13px] leading-relaxed flex flex-col">
        <div ref={scrollRef} className="flex-1 space-y-2 overflow-y-auto pr-3 scrollbar-hide pb-4">
          {messages.map((m, i) => (
             m.type === "divider" 
               ? <div key={i} className={`my-5 border-t border-dashed ${m.color}`}></div>
               : <div key={i} className={`${m.color} ${m.type === 'user' ? 'tracking-normal' : 'tracking-wide'}`} style={{ whiteSpace: "pre-wrap" }}>{m.text}</div>
          ))}
        </div>
        <div className="mt-auto border border-white/10 bg-black/40 p-3 py-4 rounded-xl flex gap-3 shrink-0 items-center shadow-inner">
          <span className="text-indigo-400 ml-2 font-bold">&gt;</span>
          <input 
             type="text" 
             value={input} 
             onChange={e => setInput(e.target.value)}
             onKeyDown={e => {
                if (e.key === "Enter") handleSend();
             }}
             disabled={loading}
             className="bg-transparent border-none outline-none flex-1 text-slate-200 placeholder-slate-600 font-sans font-medium disabled:opacity-50" 
             placeholder={loading ? "Synthesizing..." : "Talk to Lucy..."} 
             autoFocus
          />
        </div>
      </div>
  )
}

// --- ACTUAL APPLICATION DEFINITIONS ---

export const APPLICATIONS: AppDefinition[] = [
  {
    id: "lucy",
    name: "Lucy Console",
    icon: <Terminal size={24} />,
    defaultWidth: 900,
    defaultHeight: 600,
    component: () => (
      // Lazy load terminal window to avoid bundling xterm in initial bundle
      <div className="h-full">
        {/* @ts-ignore - dynamic import fallback */}
        <TerminalWindow />
      </div>
    )
  },
  {
    id: "browser",
    name: "Agent Browser",
    icon: <Globe size={24} />,
    defaultWidth: 1050,
    defaultHeight: 750,
    component: () => (
      <div className="h-full flex gap-6 p-6 font-sans">
        <div className="w-56 flex flex-col shrink-0 border-r border-white/5 pr-4">
          <div className="text-[10px] uppercase tracking-widest font-bold text-slate-500 mb-3 px-2">Browser Capabilities</div>
          <div className="flex items-center gap-3 px-4 py-3 rounded-xl cursor-pointer transition-all duration-200 font-medium text-sm bg-indigo-500/10 text-indigo-400 border border-indigo-500/20"><Compass size={18}/> AI Search</div>
          <div className="flex items-center gap-3 px-4 py-3 rounded-xl cursor-pointer transition-all duration-200 font-medium text-sm text-slate-400 hover:bg-white/5 hover:text-slate-200"><BookOpen size={18}/> Research</div>
          <div className="flex items-center gap-3 px-4 py-3 rounded-xl cursor-pointer transition-all duration-200 font-medium text-sm text-slate-400 hover:bg-white/5 hover:text-slate-200"><Brain size={18}/> Memory</div>
        </div>
        <div className="flex-1 flex flex-col items-center justify-center text-slate-500">
           <Globe size={48} className="mb-4 opacity-50" />
           <p className="font-semibold tracking-wide text-slate-300">Scout Engine Sandboxed</p>
           <p className="text-sm mt-2">Awaiting Agent Input...</p>
        </div>
      </div>
    )
  },
  {
    id: "security",
    name: "Security Fabric",
    icon: <Shield size={24} />,
    defaultWidth: 950,
    defaultHeight: 650,
    component: () => (
      <div className="h-full p-6 flex flex-col font-sans">
         <div className="grid grid-cols-3 gap-6 mb-8">
            <div className="border border-white/10 bg-black/40 p-6 rounded-2xl flex flex-col gap-3">
               <span className="text-xs font-bold text-slate-400 uppercase tracking-widest">Fabric Status</span>
               <span className="text-5xl font-light tracking-tight text-emerald-400">SECURE</span>
            </div>
            <div className="border border-white/10 bg-black/40 p-6 rounded-2xl flex flex-col gap-3">
               <span className="text-xs font-bold text-slate-400 uppercase tracking-widest">Trapped Nodes</span>
               <span className="text-5xl font-light tracking-tight text-white">12</span>
            </div>
            <div className="border border-white/10 bg-black/40 p-6 rounded-2xl flex flex-col gap-3">
               <span className="text-xs font-bold text-slate-400 uppercase tracking-widest">Active Policies</span>
               <span className="text-5xl font-light tracking-tight text-white">48</span>
            </div>
         </div>
         <div className="flex-1 border border-white/10 bg-black/40 rounded-2xl p-6 flex flex-col">
            <h3 className="text-sm font-semibold text-slate-300 mb-4 tracking-wide uppercase">Fabric Telemetry Log</h3>
            <div className="text-slate-500 font-mono text-sm leading-relaxed">
               No recent anomalies in Sentinel stream.
            </div>
         </div>
      </div>
    )
  },
  {
    id: "memory",
    name: "Memory Galaxy",
    icon: <Brain size={24} />,
    defaultWidth: 850,
    defaultHeight: 650,
    component: () => (
      <div className="h-full flex flex-col items-center justify-center text-slate-400 font-sans relative p-6">
        <div className="w-[400px] h-[400px] border border-indigo-500/20 rounded-full flex items-center justify-center relative mb-12">
            <div className="absolute w-full h-full animate-[spin_40s_linear_infinite] rounded-full border border-indigo-500/20 border-dashed"></div>
            <div className="absolute w-[280px] h-[280px] animate-[spin_25s_linear_infinite_reverse] rounded-full border border-purple-400/20"></div>
            <div className="bg-slate-900/90 backdrop-blur-2xl border border-indigo-500/40 p-8 rounded-full shadow-[0_0_60px_rgba(99,102,241,0.25)] relative z-10">
              <Brain size={48} className="text-indigo-400" />
            </div>
        </div>
        <h2 className="text-3xl font-bold text-slate-100 mb-3 tracking-tight">Memory Core Online</h2>
        <p className="text-sm font-medium">Interactive semantic graph mapping.</p>
      </div>
    )
  },
  {
    id: "files",
    name: "OS Namespace",
    icon: <Folder size={24} />,
    defaultWidth: 750,
    defaultHeight: 500,
    component: () => (
      <div className="h-full p-6 flex flex-col font-sans">
         <div className="flex justify-between items-end mb-6 border-b border-white/10 pb-4">
            <div>
              <h2 className="text-xl font-light text-slate-100 tracking-tight">Cloud Execution Namespace</h2>
              <p className="text-xs text-slate-500 font-mono mt-1">Mounted resources owned by Operator: Lucy</p>
            </div>
            <div className="flex gap-2">
               <button className="px-4 py-2 border border-white/10 bg-white/5 rounded hover:bg-white/10 text-xs font-semibold text-slate-300">Mount Resource</button>
            </div>
         </div>
         <div className="flex gap-6 h-full">
            <div className="w-48 border-r border-white/5 pr-4 flex flex-col gap-1">
               <div className="text-[10px] uppercase tracking-widest font-bold text-slate-500 mb-2 px-2">Mount Points</div>
               <div className="px-3 py-2 bg-indigo-500/10 text-indigo-400 rounded cursor-pointer font-mono text-xs border border-indigo-500/20">/lucy/home/</div>
               <div className="px-3 py-2 text-slate-400 hover:text-slate-200 hover:bg-white/5 rounded cursor-pointer font-mono text-xs">/lucy/apps/</div>
               <div className="px-3 py-2 text-slate-400 hover:text-slate-200 hover:bg-white/5 rounded cursor-pointer font-mono text-xs">/lucy/models/</div>
               <div className="px-3 py-2 text-slate-400 hover:text-slate-200 hover:bg-white/5 rounded cursor-pointer font-mono text-xs">/lucy/workspaces/</div>
            </div>
            <div className="flex-1 overflow-y-auto">
               <div className="grid grid-cols-4 gap-6 content-start">
                  <div className="flex flex-col items-center gap-3 cursor-pointer hover:bg-white/5 p-4 rounded-xl group border border-transparent hover:border-white/5"><Folder size={40} className="text-indigo-400 group-hover:scale-110 transition-transform"/><span className="text-xs text-slate-300 font-semibold text-center leading-tight">Project_Aurora</span></div>
                  <div className="flex flex-col items-center gap-3 cursor-pointer hover:bg-white/5 p-4 rounded-xl group border border-transparent hover:border-white/5"><Folder size={40} className="text-emerald-400 group-hover:scale-110 transition-transform"/><span className="text-xs text-slate-300 font-semibold text-center leading-tight">Simulations</span></div>
                  <div className="flex flex-col items-center gap-3 cursor-pointer hover:bg-white/5 p-4 rounded-xl group border border-transparent hover:border-white/5"><Folder size={40} className="text-amber-400 group-hover:scale-110 transition-transform"/><span className="text-xs text-slate-300 font-semibold text-center leading-tight">Agent_State</span></div>
                  <div className="flex flex-col items-center gap-3 cursor-pointer hover:bg-white/5 p-4 rounded-xl group border border-transparent hover:border-white/5"><Folder size={40} className="text-purple-400 group-hover:scale-110 transition-transform"/><span className="text-xs text-slate-300 font-semibold text-center leading-tight">Memory_Graphs</span></div>
               </div>
            </div>
         </div>
      </div>
    )
  },
  {
    id: "authority",
    name: "Authority Plane",
    icon: <Command size={24} />,
    defaultWidth: 700,
    defaultHeight: 500,
    component: () => (
      <div className="h-full p-6 flex flex-col font-sans">
         <div className="flex justify-between items-center mb-8 pb-4 border-b border-indigo-500/20">
            <div>
               <h2 className="text-2xl font-light text-slate-100 tracking-tight flex items-center gap-3"><Command size={24} className="text-indigo-400"/> Local Authority Plane</h2>
               <p className="text-xs text-slate-500 mt-1">Supervisor Control & Token Governance</p>
            </div>
            <div className="flex items-center gap-3">
               <div className="flex items-center gap-2 px-3 py-1.5 bg-emerald-500/10 border border-emerald-500/20 rounded-full text-emerald-400 text-xs font-bold tracking-widest"><Wifi size={14}/> CLOUD SYNC ACTIVE</div>
            </div>
         </div>

         <div className="grid grid-cols-2 gap-6">
            <div className="border border-white/10 bg-black/40 p-5 rounded-2xl flex flex-col shadow-inner">
               <div className="flex items-center gap-3 mb-4">
                  <HardDrive size={18} className="text-blue-400" />
                  <span className="font-semibold text-slate-200 tracking-wide">Local Supervisor Node</span>
               </div>
               <div className="space-y-3 text-sm font-medium">
                  <div className="flex justify-between items-center text-slate-400"><span>Identity Token:</span> <span className="font-mono text-slate-300">LOCAL_ANCHOR_9X</span></div>
                  <div className="flex justify-between items-center text-slate-400"><span>Authority:</span> <span className="font-mono text-emerald-400">MAXIMUM</span></div>
                  <div className="flex justify-between items-center text-slate-400"><span>Override Switch:</span> <button className="bg-rose-500/20 text-rose-400 px-3 py-1 rounded text-xs border border-rose-500/30">VETO ACTIVE SYSTEM</button></div>
               </div>
            </div>

            <div className="border border-indigo-500/20 bg-indigo-500/5 p-5 rounded-2xl flex flex-col shadow-inner relative overflow-hidden">
               <div className="absolute top-0 right-0 p-4 opacity-10"><Server size={80} /></div>
               <div className="flex items-center gap-3 mb-4 relative z-10">
                  <Server size={18} className="text-indigo-400" />
                  <span className="font-semibold text-slate-200 tracking-wide">Cloud Execution Plane</span>
               </div>
               <div className="space-y-3 text-sm font-medium relative z-10">
                  <div className="flex justify-between items-center text-slate-400"><span>Target Operator:</span> <span className="font-mono text-indigo-300">LUCY_CORE</span></div>
                  <div className="flex justify-between items-center text-slate-400"><span>Permissions:</span> <span className="font-mono text-amber-400">USERLAND_ROOT</span></div>
                  <div className="flex justify-between items-center text-slate-400"><span>State:</span> <span className="font-mono text-emerald-400">EXECUTING</span></div>
               </div>
            </div>
         </div>
         
         <div className="mt-6 border border-white/5 bg-black/20 p-4 rounded-xl flex items-start gap-4">
            <Lock size={24} className="text-slate-500 shrink-0 mt-1" />
            <p className="text-sm text-slate-400 leading-relaxed font-medium">
               <span className="text-slate-200 font-bold block mb-1">Architecture enforcement:</span>
               This machine serves as the primary monitor and keyboard. Lucy operates as the primary userland operator in the cloud payload. All files, models, and scripts imported are securely mounted directly into her namespace (/lucy/*).
            </p>
         </div>
      </div>
    )
  },
  {
    id: "dj",
    name: "Music Studio",
    icon: <Music size={24} />,
    defaultWidth: 800,
    defaultHeight: 500,
    component: () => (
      <div className="h-full flex text-slate-400 font-sans p-6">
        <div className="flex-1 flex flex-col items-center justify-center">
          <div className="w-24 h-24 rounded-full bg-purple-500/10 flex items-center justify-center text-purple-400 mb-6 shadow-inner border border-purple-500/20">
             <Music size={40} />
          </div>
          <p className="text-lg text-white font-medium mb-2">DJ Agent Studio</p>
          <span className="text-slate-500 font-medium tracking-wide">Ready for generative input.</span>
        </div>
      </div>
    )
  },
  {
    id: "agents",
    name: "Agent Center",
    icon: <Bot size={24} />,
    defaultWidth: 700,
    defaultHeight: 500,
    component: () => (
      <div className="h-full flex flex-col p-6 font-sans">
        <h2 className="text-2xl font-light text-slate-100 tracking-tight mb-6 flex items-center gap-3">
          <Bot className="text-indigo-400" size={28} />
          Agent Center
        </h2>
        <div className="grid grid-cols-2 gap-4">
          <div className="border border-white/10 bg-black/40 p-4 rounded-xl flex flex-col gap-2 relative overflow-hidden group hover:border-white/20 transition-colors cursor-pointer">
            <div className="flex justify-between items-start">
              <span className="font-semibold text-slate-200">Emma</span>
              <span className="text-[10px] uppercase tracking-widest text-emerald-400 font-bold px-2 py-1 bg-emerald-400/10 rounded-full">Active</span>
            </div>
            <span className="text-xs text-slate-400">Governance & Policy Enforcement</span>
          </div>
          <div className="border border-white/10 bg-black/40 p-4 rounded-xl flex flex-col gap-2 relative overflow-hidden group hover:border-white/20 transition-colors cursor-pointer">
            <div className="flex justify-between items-start">
              <span className="font-semibold text-slate-200">Lucy</span>
              <span className="text-[10px] uppercase tracking-widest text-emerald-400 font-bold px-2 py-1 bg-emerald-400/10 rounded-full">Active</span>
            </div>
            <span className="text-xs text-slate-400">Primary Core Orchestrator</span>
          </div>
          <div className="border border-white/10 bg-black/40 p-4 rounded-xl flex flex-col gap-2 relative overflow-hidden group hover:border-white/20 transition-colors cursor-pointer">
            <div className="flex justify-between items-start">
              <span className="font-semibold text-slate-200">Forge</span>
              <span className="text-[10px] uppercase tracking-widest text-blue-400 font-bold px-2 py-1 bg-blue-400/10 rounded-full">Building</span>
            </div>
            <span className="text-xs text-slate-400">Code & Compilation Pipeline</span>
          </div>
          <div className="border border-white/10 bg-black/40 p-4 rounded-xl flex flex-col gap-2 relative overflow-hidden group hover:border-white/20 transition-colors cursor-pointer">
            <div className="flex justify-between items-start">
              <span className="font-semibold text-slate-200">Scout</span>
              <span className="text-[10px] uppercase tracking-widest text-amber-400 font-bold px-2 py-1 bg-amber-400/10 rounded-full">Searching</span>
            </div>
            <span className="text-xs text-slate-400">Recon & Intelligence Gathering</span>
          </div>
          <div className="border border-white/10 bg-black/40 p-4 rounded-xl flex flex-col gap-2 relative overflow-hidden group hover:border-white/20 transition-colors cursor-pointer">
            <div className="flex justify-between items-start">
              <span className="font-semibold text-slate-200">Sentinel</span>
              <span className="text-[10px] uppercase tracking-widest text-rose-400 font-bold px-2 py-1 bg-rose-400/10 rounded-full">Monitoring</span>
            </div>
            <span className="text-xs text-slate-400">Aegis Security Fabric</span>
          </div>
          <div className="border border-white/10 bg-black/40 p-4 rounded-xl flex flex-col gap-2 relative overflow-hidden group hover:border-white/20 transition-colors cursor-pointer">
            <div className="flex justify-between items-start">
              <span className="font-semibold text-slate-200">DJ</span>
              <span className="text-[10px] uppercase tracking-widest text-slate-400 font-bold px-2 py-1 bg-slate-400/10 rounded-full">Idle</span>
            </div>
            <span className="text-xs text-slate-400">Audio Synthesis Engine</span>
          </div>
        </div>
      </div>
    )
  },
  {
    id: "monitor",
    name: "System Monitor",
    icon: <Activity size={24} />,
    defaultWidth: 700,
    defaultHeight: 500,
    component: () => (
      <div className="h-full flex flex-col p-6 font-sans gap-6">
        <div className="grid grid-cols-2 gap-4">
           <div className="bg-black/40 border border-white/10 rounded-xl p-4 flex flex-col gap-1">
              <span className="text-[10px] uppercase tracking-widest text-slate-500 font-bold">CPU Usage</span>
              <span className="text-2xl font-light text-slate-200">12%</span>
              <div className="w-full bg-slate-800 h-1.5 rounded-full mt-2 overflow-hidden"><div className="bg-indigo-500 h-full w-[12%] py-0 m-0"></div></div>
           </div>
           <div className="bg-black/40 border border-white/10 rounded-xl p-4 flex flex-col gap-1">
              <span className="text-[10px] uppercase tracking-widest text-slate-500 font-bold">Memory</span>
              <span className="text-2xl font-light text-slate-200">4.2 GB</span>
              <div className="w-full bg-slate-800 h-1.5 rounded-full mt-2 overflow-hidden"><div className="bg-emerald-500 h-full w-[42%] py-0 m-0"></div></div>
           </div>
        </div>
        <div className="flex-1 overflow-auto border border-white/10 bg-black/40 rounded-xl p-4">
           <div className="text-xs uppercase tracking-widest text-slate-500 font-bold mb-4">Active Processes</div>
           <div className="space-y-4">
              <div className="flex justify-between items-center text-sm"><span className="text-indigo-400 font-semibold">Lucy Core Node</span><span className="text-slate-400 font-mono">1.1 GB</span></div>
              <div className="flex justify-between items-center text-sm"><span className="text-blue-400 font-semibold">Emma Governance</span><span className="text-slate-400 font-mono">120 MB</span></div>
              <div className="flex justify-between items-center text-sm"><span className="text-rose-400 font-semibold">Aegis Sentinel</span><span className="text-slate-400 font-mono">450 MB</span></div>
           </div>
        </div>
      </div>
    )
  }
];
