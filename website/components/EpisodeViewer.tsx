"use client";

import React, { useEffect, useState } from "react";
import { fetchState, EpisodeState, step } from "@/lib/api";

const roleColors: Record<string, string> = {
  Planner: "bg-violet-500/20 text-violet-400 border-violet-500/50",
  Researcher: "bg-blue-500/20 text-blue-400 border-blue-500/50",
  Coder: "bg-emerald-500/20 text-emerald-400 border-emerald-500/50",
  Critic: "bg-orange-500/20 text-orange-400 border-orange-500/50",
  Synthesizer: "bg-pink-500/20 text-pink-400 border-pink-500/50",
};

const statusColors: Record<string, string> = {
  pending: "bg-gray-500/20 text-gray-400 border-gray-500/50",
  running: "bg-yellow-500/20 text-yellow-400 border-yellow-500/50 animate-pulse",
  done: "bg-green-500/20 text-green-400 border-green-500/50",
  failed: "bg-red-500/20 text-red-400 border-red-500/50",
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
      <div className="flex h-96 items-center justify-center rounded-lg border border-gray-800 bg-[#0a0a0f] text-gray-500">
        Initializing environment state…
      </div>
    );
  }

  return (
    <div className="glass-panel space-y-6 rounded-2xl p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className={`rounded-lg border px-3 py-1.5 text-[10px] font-black uppercase tracking-widest ${roleColors[state.agent_role]}`}>
            {state.agent_role}
          </div>
          {state.terminated && (
            <div className="rounded-lg bg-emerald-500/20 px-3 py-1.5 text-[10px] font-black uppercase tracking-widest text-emerald-500 border border-emerald-500/50">
              FINISHED
            </div>
          )}
          <div className="flex items-center gap-2 text-[10px] font-bold text-gray-500 uppercase tracking-widest">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
            Step {state.step}
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setAutoRun(!autoRun)}
            className={`rounded-lg px-3 py-1.5 text-[9px] font-black uppercase tracking-widest border transition-all ${
              autoRun ? "bg-emerald-500 border-emerald-500 text-black shadow-[0_0_15px_rgba(16,185,129,0.4)]" : "bg-white/5 border-white/10 text-gray-400 hover:bg-white/10"
            }`}
          >
            {autoRun ? "Auto: ON" : "Auto: OFF"}
          </button>
          <button
            onClick={handleStep}
            disabled={stepping || state.terminated}
            className="rounded-lg bg-white px-3 py-1.5 text-[9px] font-black uppercase tracking-widest text-black hover:bg-gray-200 disabled:opacity-50 transition-all active:scale-95"
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
      <div className="space-y-3">
        <h4 className="text-[10px] font-black uppercase tracking-[0.2em] text-gray-500">Task Execution Graph</h4>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {Object.entries(state.task_graph).map(([id, node]) => (
            <div key={id} className={`flex items-center justify-between rounded-xl border p-3 transition-all hover:scale-[1.02] ${statusColors[node.status]}`}>
              <span className="font-mono text-[10px] font-bold">{id}</span>
              <span className="text-[9px] font-black uppercase tracking-tighter">{node.status}</span>
            </div>
          ))}
        </div>
      </div>

      {/* World Model */}
      <div className="space-y-3">
        <h4 className="text-[10px] font-black uppercase tracking-[0.2em] text-gray-500">Shared World Model</h4>
        <div className="max-h-40 overflow-y-auto rounded-xl border border-white/5 bg-black/20 p-1 custom-scrollbar">
          <table className="w-full text-left">
            <tbody className="divide-y divide-white/5">
              {Object.entries(state.world_model).map(([key, value]) => (
                <tr key={key} className="group transition-colors hover:bg-white/[0.02]">
                  <td className="px-3 py-2.5 font-mono text-[10px] text-gray-400 group-hover:text-gray-200">{key}</td>
                  <td className="px-3 py-2.5 text-right font-mono text-[10px] text-emerald-400 font-bold">{JSON.stringify(value)}</td>
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
          className="flex w-full items-center justify-between rounded-xl border border-white/5 bg-white/5 p-3 text-[10px] font-black uppercase tracking-widest text-gray-400 transition-all hover:bg-white/10 hover:text-gray-200"
        >
          <span>Last Tool Output</span>
          <span className="text-lg leading-none">{showToolOutput ? "−" : "+"}</span>
        </button>
        {showToolOutput && (
          <div className="relative group">
            <div className="absolute inset-0 bg-emerald-500/5 blur-xl group-hover:bg-emerald-500/10 transition-all" />
            <pre className="relative mt-2 overflow-x-auto rounded-xl border border-white/5 bg-black/40 p-4 font-mono text-[10px] text-gray-300 custom-scrollbar leading-relaxed">
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
      <div className="flex flex-wrap items-center justify-between gap-4 pt-2 text-[9px] font-black uppercase tracking-widest text-gray-600">
        <div className="flex items-center gap-2 bg-white/5 px-2 py-1 rounded">
          <span className="text-gray-700">Domain</span>
          <span className="text-gray-400">{state.task_domain}</span>
        </div>
        <div className="flex items-center gap-2 bg-white/5 px-2 py-1 rounded">
          <span className="text-gray-700">Agents</span>
          <span className="text-gray-400">{state.agents}</span>
        </div>
        <div className="flex items-center gap-2 bg-white/5 px-2 py-1 rounded">
          <span className="text-gray-700">Failure</span>
          <span className="text-gray-400">{state.failure_rate}</span>
        </div>
      </div>
    </div>
  );
}
