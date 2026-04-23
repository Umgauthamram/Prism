"use client";

import React, { useEffect, useState } from "react";
import EpisodeViewer from "@/components/EpisodeViewer";
import DifficultyControls from "@/components/DifficultyControls";
import ModelSelector from "@/components/ModelSelector";
import RewardCurveChart from "@/components/RewardCurveChart";
import TransferScoreChart from "@/components/TransferScoreChart";
import ModelComparisonChart from "@/components/ModelComparisonChart";
import TournamentHistory from "@/components/TournamentHistory";
import { fetchHealth, fetchMetrics, Metrics } from "@/lib/api";

export default function Dashboard() {
  const [online, setOnline] = useState(false);
  const [metrics, setMetrics] = useState<Metrics | null>(null);

  useEffect(() => {
    const poll = async () => {
      try {
        await fetchHealth();
        setOnline(true);
      } catch {
        setOnline(false);
      }
      
      try {
        const m = await fetchMetrics();
        setMetrics(m);
      } catch {
        // Handled in components
      }
    };

    poll();
    const interval = setInterval(poll, 3000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="min-h-screen p-6 lg:p-12 max-w-[1600px] mx-auto">
      {/* Header Bar */}
      <header className="mb-12 flex flex-col justify-between gap-8 lg:flex-row lg:items-end">
        <div className="space-y-2">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 mb-2">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </span>
            <span className="text-[10px] font-black uppercase tracking-widest text-emerald-500">System Live</span>
          </div>
          <h1 className="text-5xl font-black tracking-tighter lg:text-7xl">
            prism <span className="text-gradient">RL</span>
          </h1>
          <p className="text-xs font-bold text-gray-500 max-w-md leading-relaxed">
            Autonomous multi-agent reliability training. Benchmarking long-horizon planning and self-improving capabilities on the OpenEnv protocol.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-4">
          <StatBadge label="Episodes" value={metrics?.total_episodes ?? 0} />
          <StatBadge label="Rolling Reward" value={metrics?.rolling_reward.toFixed(2) ?? "0.00"} />
          <StatBadge label="Training Stage" value={metrics?.current_stage ?? 0} />
          
          <div className={`flex flex-col items-center justify-center rounded-2xl border px-6 py-4 transition-all duration-500 ${
            online ? "border-emerald-500/20 bg-emerald-500/5" : "border-red-500/20 bg-red-500/5"
          }`}>
            <div className={`text-[10px] font-black uppercase tracking-widest mb-1 ${online ? "text-emerald-500" : "text-red-500"}`}>
              Backend
            </div>
            <div className="text-sm font-bold text-white uppercase tracking-tighter">
              {online ? "Connected" : "Offline"}
            </div>
          </div>
        </div>
      </header>

      {/* Main Grid */}
      <main className="grid grid-cols-1 gap-10 lg:grid-cols-12 items-start">
        {/* Left Column - Controls & Status */}
        <div className="space-y-10 lg:col-span-4">
          <div className="space-y-4">
            <h2 className="text-[10px] font-black uppercase tracking-[0.3em] text-gray-600 ml-2">Active Environment</h2>
            <EpisodeViewer />
          </div>
          <div className="space-y-4">
            <h2 className="text-[10px] font-black uppercase tracking-[0.3em] text-gray-600 ml-2">System Parameters</h2>
            <DifficultyControls />
          </div>
          <div className="space-y-4">
            <h2 className="text-[10px] font-black uppercase tracking-[0.3em] text-gray-600 ml-2">Model Policy</h2>
            <ModelSelector />
          </div>
        </div>

        {/* Right Column - Analytics */}
        <div className="space-y-10 lg:col-span-8">
          <div className="space-y-4">
            <h2 className="text-[10px] font-black uppercase tracking-[0.3em] text-gray-600 ml-2">Reward Optimization</h2>
            <RewardCurveChart />
          </div>
          <div className="space-y-4">
            <h2 className="text-[10px] font-black uppercase tracking-[0.3em] text-gray-600 ml-2">Transfer Benchmarks</h2>
            <TransferScoreChart />
          </div>
          <div className="space-y-4">
            <h2 className="text-[10px] font-black uppercase tracking-[0.3em] text-gray-600 ml-2">Model Benchmarking</h2>
            <ModelComparisonChart />
          </div>
        </div>

        {/* Full Width Bottom Section */}
        <div className="lg:col-span-12 mt-10">
          <div className="space-y-4">
            <h2 className="text-[10px] font-black uppercase tracking-[0.3em] text-gray-600 ml-2">Evaluation Archive</h2>
            <TournamentHistory />
          </div>
        </div>
      </main>
    </div>
  );
}

function StatBadge({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="tech-card group px-6 py-5 min-w-[140px] transition-all hover:border-white/10">
      <div className="text-[10px] font-black uppercase tracking-widest text-gray-500 mb-1">{label}</div>
      <div className="text-2xl font-mono font-black text-white">{value}</div>
    </div>
  );
}
