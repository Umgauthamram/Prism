"use client";

import React, { useState } from "react";
import { resetEpisode, TaskDomain, AgentCount, FailureRate } from "@/lib/api";

interface DifficultyControlsProps {
  config: {
    domain: TaskDomain;
    agents: AgentCount;
    failureRate: FailureRate;
    seed: number;
  };
  setConfig: (config: any) => void;
}

export default function DifficultyControls({ config, setConfig }: DifficultyControlsProps) {
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<{ type: "success" | "error"; msg: string } | null>(null);

  const handleReset = async () => {
    setLoading(true);
    setStatus(null);
    try {
      await resetEpisode({
        task_domain: config.domain,
        agents: config.agents,
        failure_rate: config.failureRate,
        seed: config.seed,
      });
      setStatus({ type: "success", msg: "Environment reset successful" });
    } catch (err) {
      setStatus({ type: "error", msg: "Failed to reset environment" });
    } finally {
      setLoading(false);
    }
  };

  const update = (key: string, val: any) => {
    setConfig({ ...config, [key]: val });
  };

  return (
    <div className="glass-panel space-y-10 p-10">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-black uppercase tracking-widest text-black">Injectors</h3>
        <span className="bg-black px-3 py-1 text-[10px] font-black uppercase tracking-widest text-white border-2 border-black">Active</span>
      </div>

      <div className="space-y-4">
        <label className="text-[11px] font-black uppercase tracking-[0.2em] text-black/40">Task Environment</label>
        <div className="grid grid-cols-3 gap-2">
          {["debug", "market_research", "etl"].map((d) => (
            <button
              key={d}
              onClick={() => update("domain", d as TaskDomain)}
              className={`border-2 py-2.5 text-[10px] font-black uppercase tracking-tighter transition-all ${
                config.domain === d 
                ? "border-black bg-black text-white shadow-[4px_4px_0px_rgba(0,0,0,1)]" 
                : "border-black bg-white text-black hover:bg-gray-100"
              }`}
            >
              {d === "market_research" ? "Research" : d}
            </button>
          ))}
        </div>
      </div>

      <div className="space-y-4">
        <label className="text-[11px] font-black uppercase tracking-[0.2em] text-black/40">Agent Concurrency (Inj 1)</label>
        <div className="grid grid-cols-3 gap-2">
          {[2, 4, 8].map((n) => (
            <button
              key={n}
              onClick={() => update("agents", n as AgentCount)}
              className={`border-2 py-2.5 text-[10px] font-black uppercase tracking-widest transition-all ${
                config.agents === n 
                ? "border-black bg-black text-white shadow-[4px_4px_0px_rgba(0,0,0,1)]" 
                : "border-black bg-white text-black hover:bg-gray-100"
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
          <label className="text-[10px] font-black uppercase tracking-[0.2em] text-black/40">Instability (Inj 2)</label>
          <span className="bg-black px-2 py-0.5 font-mono text-[10px] font-bold text-white border border-black">{config.failureRate}</span>
        </div>
        <input
          type="range"
          min="0"
          max="2"
          step="1"
          value={config.failureRate === 0 ? 0 : config.failureRate === 0.2 ? 1 : 2}
          onChange={(e) => {
            const val = parseInt(e.target.value);
            update("failureRate", val === 0 ? 0 : val === 1 ? 0.2 : 0.5);
          }}
          className="h-1.5 w-full cursor-pointer appearance-none rounded-lg bg-black/10 accent-black hover:accent-gray-800"
        />
      </div>

      <div className="space-y-3">
        <label className="text-[10px] font-black uppercase tracking-[0.2em] text-black/40">Reproduction Seed</label>
        <div className="relative group">
          <input
            type="number"
            value={config.seed}
            onChange={(e) => {
              const val = parseInt(e.target.value);
              update("seed", isNaN(val) ? 0 : val);
            }}
            className="w-full border-2 border-black bg-white p-3 font-mono text-xs text-black transition-all focus:outline-none focus:ring-2 focus:ring-black/5"
          />
        </div>
      </div>

      {/* Reset Button */}
      <div className="pt-2">
        <button
          disabled={loading}
          onClick={handleReset}
          className="relative w-full bg-black p-3.5 text-xs font-black uppercase tracking-[0.3em] text-white transition-all hover:bg-gray-800 active:scale-[0.95] disabled:opacity-50 border-2 border-black"
        >
          <span className="relative">{loading ? "Reconfiguring..." : "Sync & Reset"}</span>
        </button>
        {status && (
          <p className={`mt-4 text-center text-[10px] font-black uppercase tracking-widest ${status.type === "success" ? "text-black" : "text-red-600"}`}>
            {status.msg}
          </p>
        )}
      </div>
    </div>
  );
}
