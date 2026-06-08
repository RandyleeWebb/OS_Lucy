import React, { useEffect, useRef, useState } from "react";

import { Terminal } from "xterm";
import "xterm/css/xterm.css";

export default function TerminalWindow() {
  const termRef = useRef<HTMLDivElement | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const xtermRef = useRef<Terminal | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [status, setStatus] = useState("disconnected");

  useEffect(() => {
	let mounted = true;

	async function startSession() {
	  setStatus("creating");
	  try {
	  // Use relative path; server proxy forwards /terminal -> EMMA
	  const res = await fetch(`/terminal/session`, { method: "POST", headers: { "x-secret-key": "lucy-secret" } });
	  const data: any = await res.json();
	  if (!mounted) return;
	  setSessionId(data.session_id);

		// init xterm
		const term = new Terminal({ cursorBlink: true, convertEol: true, scrollback: 1000 });
		xtermRef.current = term;
		if (termRef.current) term.open(termRef.current);

		// Build ws url
		const proto = location.protocol === "https:" ? "wss:" : "ws:";
		// Relative websocket path — the server will proxy /terminal/ws to Emma
		const wsUrl = `${proto}//${window.location.host}/terminal/ws/${data.session_id}?x-secret-key=lucy-secret`;
		const ws = new WebSocket(wsUrl);
		wsRef.current = ws;

		ws.onopen = () => {
		  setStatus("connected");
		  term.write('\r\n[CONNECTED to session]\r\n');
		};

		ws.onmessage = (ev) => {
		  try {
			const raw = ev.data as string;
			// some messages are plain strings, some may be JSON
			let out = raw;
			try {
			  const parsed = JSON.parse(raw);
			  if (parsed && parsed.type === 'output' && parsed.data) out = parsed.data;
			  else if (parsed && parsed.type === 'status' && parsed.msg) out = `\r\n[STATUS] ${parsed.msg}\r\n`;
			} catch {}
			term.write(out);
		  } catch (e) {}
		};

		ws.onclose = () => {
		  setStatus("closed");
		  term.write('\r\n[WS closed]\r\n');
		};

		ws.onerror = (e) => {
		  setStatus("error");
		  term.write('\r\n[WS error]\r\n');
		};

		// Send terminal input to websocket
		term.onData((data) => {
		  try {
			if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ type: 'input', data }));
		  } catch (e) {
			// best-effort
		  }
		});

	  } catch (err) {
		setStatus("error");
		console.error("Failed to create terminal session", err);
	  }
	}

	startSession();

	return () => {
	  mounted = false;
	  // cleanup
	  try {
		if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
		  wsRef.current.close();
		}
	  } catch {}
	  try {
		if (xtermRef.current) {
		  xtermRef.current.dispose();
		}
	  } catch {}
		// close session on backend
	  if (sessionId) {
		fetch(`/terminal/session/${sessionId}/close`, { method: "POST", headers: { "x-secret-key": "lucy-secret" } }).catch(() => {});
	  }
	};
  }, []);

  return (
	<div className="h-full flex flex-col">
	  <div className="flex items-center gap-3 px-4 py-2 border-b border-white/5 bg-slate-900/50">
		<div className="text-sm font-semibold">Terminal</div>
		<div className="text-xs text-slate-400">Status: {status}</div>
	  </div>
	  <div ref={termRef} style={{ flex: 1, minHeight: 200 }} />
	</div>
  );
}
