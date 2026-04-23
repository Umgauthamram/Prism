"use client";

import React, { useState } from "react";
import { resetEpisode, TaskDomain, AgentCount, FailureRate } from "@/lib/api";

export default function DifficultyControls() {
  const [domain, setDomain] = useState<TaskDomain>("debug");
  const [agents, setAgents] = useState<AgentCount>(4);
  const [failureRate, setFailureRate] = useState<FailureRate>(0.2);
  const [seed, setSeed] = useState(42);
  const [status, setStatus] = useState<{ type: "success" | "error"; msg: string } | null>(null);
  const [loading, setLoading] = useState(false);

  const handleReset = async () => {
    setLoading(true);
    setStatus(null);
    try {
      await resetEpisode({
        task_domain: domain,
        agents: agents,
        failure_rate: failureRate,
        seed: seed,
      });
      setStatus({ type: "success", msg: "Environment reset successful" });
    } catch (err) {
      setStatus({ type: "error", msg: "Failed to reset environment" });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="glass-panel space-y-8 rounded-2xl p-6">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-black uppercase tracking-widest text-white">Injectors</h3>
        <span className="rounded-full bg-emerald-500/10 px-2 py-0.5 text-[8px] font-black uppercase tracking-widest text-emerald-400 border border-emerald-500/20">Active</span>
      </div>

      {/* Task Domain */}
      <div className="space-y-3">
        <label className="text-[10px] font-black uppercase tracking-[0.2em] text-gray-500">Task Environment</label>
        <div className="grid grid-cols-3 gap-2">
          {["debug", "market_research", "etl"].map((d) => (
            <button
              key={d}
              onClick={() => setDomain(d as TaskDomain)}
              className={`rounded-xl border py-2.5 text-[10px] font-black uppercase tracking-tighter transition-all ${
                domain === d 
                ? "border-emerald-500/50 bg-emerald-500/10 text-emerald-400 shadow-[0_0_15px_rgba(16,185,129,0.1)]" 
                : "border-white/5 bg-white/5 text-gray-500 hover:border-white/10 hover:bg-white/10"
              }`}
            >
              {d === "market_research" ? "Research" : d}
            </button>
          ))}
        </div>
      </div>

      {/* Agent Count */}
      <div className="space-y-3">
        <label className="text-[10px] font-black uppercase tracking-[0.2em] text-gray-500">Agent Concurrency (Inj 1)</label>
        <div className="grid grid-cols-3 gap-2">
          {[2, 4, 8].map((n) => (
            <button
              key={n}
              onClick={() => setAgents(n as AgentCount)}
              className={`rounded-xl border py-2.5 text-[10px] font-black uppercase tracking-widest transition-all ${
                agents === n 
                ? "border-blue-500/50 bg-blue-500/10 text-blue-400 shadow-[0_0_15px_rgba(59,130,246,0.1)]" 
                : "border-white/5 bg-white/5 text-gray-500 hover:border-white/10 hover:bg-white/10"
              }`}
            >
              {n} Agents
            </button>
          ))}
        </div>
      </div>

      {/* Failure Rate */}
      <div className="space-y-3">
        <div className="flex justify-between items-center">
          <label className="text-[10px] font-black uppercase tracking-[0.2em] text-gray-500">Instability (Inj 2)</label>
          <span className="rounded bg-black/40 px-2 py-0.5 font-mono text-[10px] font-bold text-red-400">{failureRate}</span>
        </div>
        <input
          type="range"
          min="0"
          max="2"
          step="1"
          value={failureRate === 0 ? 0 : failureRate === 0.2 ? 1 : 2}
          onChange={(e) => {
            const val = parseInt(e.target.value);
            setFailureRate(val === 0 ? 0 : val === 1 ? 0.2 : 0.5);
          }}
          className="h-1.5 w-full cursor-pointer appearance-none rounded-lg bg-white/5 accent-red-500 hover:accent-red-400"
        />
      </div>

      {/* Seed */}
      <div className="space-y-3">
        <label className="text-[10px] font-black uppercase tracking-[0.2em] text-gray-500">Reproduction Seed</label>
        <div className="relative group">
          <input
            type="number"
            value={seed}
            onChange={(e) => setSeed(parseInt(e.target.value))}
            className="w-full rounded-xl border border-white/5 bg-black/40 p-3 font-mono text-xs text-gray-300 transition-all focus:border-emerald-500/50 focus:outline-none focus:ring-1 focus:ring-emerald-500/20"
          />
        </div>
      </div>

      {/* Reset Button */}
      <div className="pt-2">
        <button
          disabled={loading}
          onClick={handleReset}
          className="relative w-full group overflow-hidden rounded-xl bg-white p-3.5 text-xs font-black uppercase tracking-[0.3em] text-black transition-all hover:scale-[0.98] active:scale-[0.95] disabled:opacity-50"
        >
          <div className="absolute inset-0 bg-gradient-to-r from-emerald-400 to-blue-500 opacity-0 group-hover:opacity-10 transition-opacity" />
          <span className="relative">{loading ? "Reconfiguring..." : "Sync & Reset"}</span>
        </button>
        {status && (
          <p className={`mt-4 text-center text-[10px] font-black uppercase tracking-widest ${status.type === "success" ? "text-emerald-400" : "text-red-400"}`}>
            {status.msg}
          </p>
        )}
      </div>
    </div>
  );
}
