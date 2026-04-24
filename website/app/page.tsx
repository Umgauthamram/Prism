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
  const [currentTab, setCurrentTab] = useState<"dashboard" | "archive">("dashboard");

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
    <div className="min-h-screen p-6 lg:p-10 w-full bg-white text-black">
      {/* Header Bar */}
      <header className="mb-10 flex flex-col justify-between gap-8 lg:flex-row lg:items-end border-b-[4px] border-black pb-8">
        <div className="space-y-1">
          <h1 className="text-5xl font-black tracking-tighter lg:text-7xl uppercase leading-none">
            prism <span className="text-black/20">RL</span>
          </h1>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <StatBadge label="Episodes" value={metrics?.total_episodes ?? 0} />
          <StatBadge label="Rolling Reward" value={metrics?.rolling_reward.toFixed(2) ?? "0.00"} />
          <StatBadge label="Training Stage" value={metrics?.current_stage ?? 0} />
          
          <div className={`flex flex-col items-center justify-center border-[2px] px-3 py-2 transition-all duration-500 shadow-[3px_3px_0px_rgba(0,0,0,1)] ${
            online ? "border-black bg-white" : "border-red-500 bg-red-50"
          }`}>
            <div className={`text-[7px] font-black uppercase tracking-widest mb-0.5 ${online ? "text-black" : "text-red-500"}`}>
              {online ? "Connected" : "Offline"}
            </div>
            <div className="text-[10px] font-black uppercase tracking-tighter">
              {online ? (process.env.NEXT_PUBLIC_ENV_URL || "Local (8000)") : "No Backend"}
            </div>
          </div>
        </div>
      </header>

      {/* Tab Navigation */}
      <nav className="mb-8 flex gap-3">
        {[
          { id: "dashboard", label: "Active Environment & Training" },
          { id: "archive", label: "Evaluation Archive" },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setCurrentTab(tab.id as any)}
            className={`px-5 py-2.5 text-[9px] font-black uppercase tracking-widest transition-all border-[2px] shadow-[3px_3px_0px_rgba(0,0,0,1)] active:translate-x-0.5 active:translate-y-0.5 active:shadow-none ${
              currentTab === tab.id
                ? "bg-black text-white border-black"
                : "bg-white text-black border-black hover:bg-gray-100"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </nav>

      {/* Main Content */}
      <main className="min-h-[500px]">
        {currentTab === "dashboard" && (
          <div className="grid grid-cols-1 gap-8 lg:grid-cols-12 items-start animate-in fade-in duration-500">
            {/* Left Column - Controls & Status */}
            <div className="space-y-8 lg:col-span-5">
              <div className="space-y-3">
                <h2 className="text-[9px] font-black uppercase tracking-[0.3em] text-black/40 ml-2">Active Environment</h2>
                <EpisodeViewer />
              </div>
              <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
                <div className="space-y-3">
                    <h2 className="text-[9px] font-black uppercase tracking-[0.3em] text-black/40 ml-2">System Parameters</h2>
                    <DifficultyControls />
                </div>
                <div className="space-y-3">
                    <h2 className="text-[9px] font-black uppercase tracking-[0.3em] text-black/40 ml-2">Model Policy</h2>
                    <ModelSelector />
                </div>
              </div>
            </div>

            {/* Right Column - Analytics */}
            <div className="space-y-8 lg:col-span-7">
              <div className="space-y-3">
                <h2 className="text-[9px] font-black uppercase tracking-[0.3em] text-black/40 ml-2">Reward Optimization</h2>
                <RewardCurveChart />
              </div>
              <div className="space-y-3">
                <h2 className="text-[9px] font-black uppercase tracking-[0.3em] text-black/40 ml-2">Transfer Benchmarks</h2>
                <TransferScoreChart />
              </div>
              <div className="space-y-3">
                <h2 className="text-[9px] font-black uppercase tracking-[0.3em] text-black/40 ml-2">Model Benchmarking</h2>
                <ModelComparisonChart />
              </div>
            </div>
          </div>
        )}

        {currentTab === "archive" && (
          <div className="animate-in fade-in duration-500">
            <div className="space-y-8">
              <h2 className="text-[11px] font-black uppercase tracking-[0.3em] text-black/40 ml-2">Evaluation Archive</h2>
              <TournamentHistory />
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

function StatBadge({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="tech-card px-6 py-5 min-w-[140px] transition-all bg-white border-black border-[3px] shadow-[4px_4px_0px_rgba(0,0,0,1)]">
      <div className="text-[10px] font-black uppercase tracking-widest text-black/40 mb-1">{label}</div>
      <div className="text-2xl font-mono font-black text-black">{value}</div>
    </div>
  );
}
