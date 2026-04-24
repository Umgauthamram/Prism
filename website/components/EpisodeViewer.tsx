"use client";

import React, { useEffect, useState } from "react";
import { fetchState, EpisodeState, step } from "@/lib/api";

const roleColors: Record<string, string> = {
  Planner: "bg-indigo-600 text-white border-black",
  Researcher: "bg-blue-600 text-white border-black",
  Coder: "bg-emerald-600 text-white border-black",
  Critic: "bg-amber-600 text-white border-black",
  Synthesizer: "bg-rose-600 text-white border-black",
};

const statusColors: Record<string, string> = {
  pending: "bg-white text-black/20 border-black",
  running: "bg-white text-black border-black animate-pulse",
  done: "bg-black text-white border-black",
  failed: "bg-red-600 text-white border-black",
};

export default function EpisodeViewer() {
  const [state, setState] = useState<EpisodeState | null>(null);
  const [autoRun, setAutoRun] = useState(false);
  const [stepping, setStepping] = useState(false);
  const [showToolOutput, setShowToolOutput] = useState(false);
  const [stepTimers, setStepTimers] = useState<{step: number, duration: number}[]>([]);

  useEffect(() => {
    const poll = async () => {
      try {
        const data = await fetchState();
        setState(data);
      } catch (err) {
        console.debug("Episode state not yet available");
      }
    };

    poll();
    const interval = setInterval(poll, 1000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    let timer: any;
    if (autoRun && state && !state.terminated && !stepping) {
      timer = setTimeout(handleStep, 1500);
    }
    return () => clearTimeout(timer);
  }, [autoRun, state?.step, state?.terminated, stepping]);

  const handleStep = async () => {
    if (!state || state.terminated || stepping) return;
    setStepping(true);
    const start = Date.now();
    try {
      await step("checkpoint", {});
      const end = Date.now();
      const duration = (end - start) / 1000;
      
      const newState = await fetchState();
      setState(newState);
      setStepTimers(prev => [...prev, { step: state.step, duration }]);
    } catch (err) {
      console.error("Step failed");
    } finally {
      setStepping(false);
    }
  };

  if (!state) {
    return (
      <div className="flex h-96 items-center justify-center border-3 border-black bg-white text-black">
        Initializing environment state…
      </div>
    );
  }

  return (
    <div className="glass-panel space-y-8 p-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className={`border-2 px-4 py-2 text-[11px] font-black uppercase tracking-widest ${roleColors[state.agent_role]}`}>
            {state.agent_role}
          </div>
          {state.terminated && (
            <div className="rounded-lg bg-emerald-500/20 px-3 py-1.5 text-[10px] font-black uppercase tracking-widest text-emerald-500 border border-emerald-500/50">
              FINISHED
            </div>
          )}
          <div className="flex flex-col gap-1.5">
            <div className="flex items-center gap-2 text-[11px] font-black text-black uppercase tracking-widest">
                <span className="h-2 w-2 rounded-full bg-black animate-pulse" />
                Step {state.step}
            </div>
            <div className="h-2 w-40 border-2 border-black bg-black/5 overflow-hidden">
                <div 
                    className="h-full bg-black transition-all duration-500" 
                    style={{ width: `${Math.min((state.step / 30) * 100, 100)}%` }} 
                />
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setAutoRun(!autoRun)}
            className={`px-3 py-1.5 text-[9px] font-black uppercase tracking-widest border-2 transition-all ${
              autoRun ? "bg-black border-black text-white shadow-[4px_4px_0px_rgba(0,0,0,1)]" : "bg-white border-black text-black hover:bg-gray-100"
            }`}
          >
            {autoRun ? "Auto: ON" : "Auto: OFF"}
          </button>
          <button
            onClick={handleStep}
            disabled={stepping || state.terminated}
            className="bg-black px-3 py-1.5 text-[9px] font-black uppercase tracking-widest text-white hover:bg-gray-800 disabled:opacity-50 transition-all active:scale-95 border-2 border-black"
          >
            {stepping ? "..." : "Next Step"}
          </button>
        </div>
      </div>

      {/* Failure Banner */}
      {state.injected_failure_flag && (
        <div className="flex items-center justify-center gap-3 animate-pulse-soft rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-center">
          <span className="text-xl">⚠</span>
          <span className="text-xs font-black tracking-[0.2em] text-red-400">INJECTED FAILURE ACTIVE</span>
        </div>
      )}

      {/* Task Graph */}
      <div className="space-y-4">
        <h4 className="text-[11px] font-black uppercase tracking-[0.2em] text-black/40">Task Execution Graph</h4>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {Object.entries(state.task_graph).map(([id, node]) => (
            <div key={id} className={`flex items-center justify-between border-2 p-4 transition-all hover:translate-x-1 ${statusColors[node.status]}`}>
              <span className="font-mono text-[11px] font-bold italic">{id}</span>
              <span className="text-[10px] font-black uppercase tracking-tighter">{node.status}</span>
            </div>
          ))}
        </div>
      </div>

      {/* World Model */}
      <div className="space-y-3">
        <h4 className="text-[10px] font-black uppercase tracking-[0.2em] text-black/40">Shared World Model</h4>
        <div className="max-h-40 overflow-y-auto border-2 border-black bg-white p-1 custom-scrollbar">
          <table className="w-full text-left">
            <tbody className="divide-y divide-black/10">
              {Object.entries(state.world_model).map(([key, value]) => (
                <tr key={key} className="group transition-colors hover:bg-black/[0.02]">
                  <td className="px-3 py-2.5 font-mono text-[10px] text-black group-hover:text-black">{key}</td>
                  <td className="px-3 py-2.5 text-right font-mono text-[10px] text-black font-bold">{JSON.stringify(value)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Tool Output */}
      <div className="space-y-3">
        <button
          onClick={() => setShowToolOutput(!showToolOutput)}
          className="flex w-full items-center justify-between border-2 border-black bg-white p-3 text-[10px] font-black uppercase tracking-widest text-black transition-all hover:bg-gray-50"
        >
          <span>Last Tool Output</span>
          <span className="text-lg leading-none">{showToolOutput ? "−" : "+"}</span>
        </button>
        {showToolOutput && (
          <div className="relative group">
            <pre className="relative mt-2 overflow-x-auto border-2 border-black bg-white p-4 font-mono text-[10px] text-black custom-scrollbar leading-relaxed">
              {JSON.stringify(state.last_tool_output, null, 2)}
            </pre>
          </div>
        )}
      </div>

      {/* Step Latency Log */}
      <div className="space-y-3 pt-4 border-t border-white/5">
        <h4 className="text-[10px] font-black uppercase tracking-[0.2em] text-gray-500">Step Performance Log</h4>
        <div className="flex flex-wrap gap-2 max-h-24 overflow-y-auto custom-scrollbar">
            {stepTimers.length === 0 ? (
                <div className="text-[8px] text-gray-700 italic">No steps recorded yet...</div>
            ) : (
                stepTimers.map((t, idx) => (
                    <div key={idx} className="bg-white/5 border border-white/5 rounded px-2 py-1 flex items-center gap-2">
                        <span className="text-[8px] font-bold text-gray-500">#{t.step}</span>
                        <span className="text-[10px] font-black text-blue-400">{t.duration.toFixed(2)}s</span>
                    </div>
                ))
            )}
        </div>
      </div>

      {/* Footer */}
      <div className="flex flex-wrap items-center justify-between gap-4 pt-2 text-[9px] font-black uppercase tracking-widest text-black/30">
        <div className="flex items-center gap-2 bg-black/5 px-2 py-1">
          <span className="text-black/60">Domain</span>
          <span className="text-black">{state.task_domain}</span>
        </div>
        <div className="flex items-center gap-2 bg-black/5 px-2 py-1">
          <span className="text-black/60">Agents</span>
          <span className="text-black">{state.agents}</span>
        </div>
        <div className="flex items-center gap-2 bg-black/5 px-2 py-1">
          <span className="text-black/60">Failure</span>
          <span className="text-black">{state.failure_rate}</span>
        </div>
      </div>
    </div>
  );
}
