"use client";

import React, { useEffect, useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import { fetchModelComparison, RewardPoint, resetEpisode, setModelConfig, step } from "@/lib/api";

const COLORS = ["#10b981", "#3b82f6", "#f59e0b", "#8b5cf6", "#ef4444", "#ec4899"];
const MAX_STEPS = 25;

export default function ModelComparisonChart() {
  const [data, setData] = useState<Record<string, RewardPoint[]>>({});
  const [loading, setLoading] = useState(true);
  const [tournamentRunning, setTournamentRunning] = useState(false);
  const [statuses, setStatuses] = useState<Record<string, string>>({});

  const startTournament = async () => {
    setTournamentRunning(true);
    setStatuses({});
    // Clear old chart data so the new run starts fresh
    setData({});

    try {
        // Read system parameters from the DifficultyControls UI
        // Look for the active button specifically among the domain options (debug, research, etl)
        const domainButtons = Array.from(document.querySelectorAll<HTMLButtonElement>('button'));
        const domainBtn = domainButtons.find(btn => {
          const text = btn.textContent?.toLowerCase().trim() || "";
          const isActive = btn.className.includes("bg-black") && btn.className.includes("text-white");
          return isActive && (text === "debug" || text === "research" || text === "etl");
        });

        const activeDomain = domainBtn?.textContent?.toLowerCase().trim() || "debug";
        // Map display label back to API value
        const domainMap: Record<string, string> = { research: "market_research", debug: "debug", etl: "etl" };
        const domain = domainMap[activeDomain] || activeDomain;

        // Read agent count from the UI
        const agentBtn = document.querySelectorAll<HTMLButtonElement>(
          '[class*="border-black"][class*="bg-black"][class*="text-white"][class*="shadow"]'
        );
        let agents = 4;
        agentBtn.forEach(btn => {
          const txt = btn.textContent || "";
          if (txt.includes("Agents")) {
            const n = parseInt(txt);
            if (!isNaN(n)) agents = n;
          }
        });

        // Read seed from the input
        const seedInput = document.querySelector<HTMLInputElement>('input[type="number"]');
        const seed = seedInput ? parseInt(seedInput.value) || 42 : 42;

        // Fetch current active models from backend comparison state
        const comp = await fetchModelComparison();
        const modelsToRun = Object.keys(comp.models);

        if (modelsToRun.length === 0) {
            modelsToRun.push("groq/llama-3.3-70b-versatile", "gemini/gemini-2.0-flash");
        }

        // Phase 1: Reset an episode for each model and store their episode IDs
        const activeEpisodes: { provider: string; model: string; eid: string; done: boolean; rewards: RewardPoint[] }[] = [];
        for (const m of modelsToRun) {
            const [provider, model] = m.includes("/") ? m.split("/") : ["groq", m];
            setStatuses(prev => ({ ...prev, [`${provider}/${model}`]: "initializing" }));
            
            const obs = await resetEpisode({ task_domain: domain as any, agents: agents as any, failure_rate: 0 as any, seed });
            const eid = obs.observation?.episode_id || obs.episode_id;
            await setModelConfig(provider, model, "SAVED", eid);
            
            activeEpisodes.push({ provider, model, eid, done: false, rewards: [] });
        }

        // Brief pause so the UI shows the initialized state
        await new Promise(r => setTimeout(r, 500));

        // Phase 2: Round-Robin lockstep — each model takes one step before advancing
        // ALWAYS run exactly MAX_STEPS for every model, never exit early
        let currentStep = 1;
        while (currentStep <= MAX_STEPS) {
            for (const ep of activeEpisodes) {
                try {
                    const stepResult = await step("checkpoint", {}, ep.eid);
                    const reward = stepResult.reward ?? 0;

                    // Track reward locally so we don't depend on the backend's global state
                    ep.rewards.push({ step: currentStep, total: reward, breakdown: stepResult.info?.reward_breakdown || {} });

                    // Update the chart data in real-time from local tracking
                    setData(prev => ({
                        ...prev,
                        [`${ep.provider}/${ep.model}`]: [...ep.rewards]
                    }));
                    
                    setStatuses(prev => ({ 
                        ...prev, 
                        [`${ep.provider}/${ep.model}`]: `step ${currentStep}/${MAX_STEPS}` 
                    }));
                } catch (stepErr) {
                    ep.rewards.push({ 
                        step: currentStep, 
                        total: -0.1, 
                        breakdown: { progress_delta: 0, atomic_health: 0, coord_efficiency: 0, hallucination_penalty: 0, terminal_bonus: 0 } 
                    });
                    setData(prev => ({
                        ...prev,
                        [`${ep.provider}/${ep.model}`]: [...ep.rewards]
                    }));
                }
            }

            currentStep++;
            
            await new Promise(r => setTimeout(r, 800));
        }

        // Mark all models as finished
        for (const ep of activeEpisodes) {
            setStatuses(prev => ({ ...prev, [`${ep.provider}/${ep.model}`]: "finished" }));
        }

    } catch (err) {
        console.error("Tournament failed", err);
    } finally {
        setTournamentRunning(false);
    }
  };

  useEffect(() => {
    // Only poll when tournament is NOT running (avoids overwriting local tracking)
    if (tournamentRunning) return;

    const poll = async () => {
      try {
        const result = await fetchModelComparison();
        if (result.models && Object.keys(result.models).length > 0) {
          setData(prev => ({ ...prev, ...result.models }));
        }
      } catch { /* ignore poll errors */ }
      setLoading(false);
    };

    poll();
    const interval = setInterval(poll, 3000);
    return () => clearInterval(interval);
  }, [tournamentRunning]);

  const modelKeys = Object.keys(data);

  if (loading) {
    return (
      <div className="glass-panel flex h-72 items-center justify-center text-[10px] font-black uppercase tracking-widest text-black/40">
        Syncing comparison matrix...
      </div>
    );
  }

  const maxSteps = modelKeys.length > 0
    ? Math.min(Math.max(...modelKeys.map(k => (data[k] || []).length)), MAX_STEPS)
    : 0;

  const chartData = Array.from({ length: maxSteps }, (_, i) => {
    const point: any = { step: i + 1 };
    modelKeys.forEach(key => {
      if (data[key] && data[key][i]) {
        point[key] = data[key][i].total;
      }
    });
    return point;
  });

  return (
    <div className="glass-panel p-6">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h3 className="text-sm font-black uppercase tracking-widest text-black">Model Agnosticism Proof</h3>
          <p className="text-xs text-black/40">Cross-LLM reward trajectory comparison</p>
        </div>
        <button 
            onClick={startTournament}
            disabled={tournamentRunning}
            className={`px-4 py-2 text-[10px] font-black uppercase tracking-widest transition-all border-2 ${
                tournamentRunning 
                ? "bg-black/20 text-black border-black animate-pulse" 
                : "bg-black text-white hover:bg-gray-800 border-black"
            }`}
        >
          {tournamentRunning ? "Tournament Active" : "Start Tournament"}
        </button>
      </div>

      {Object.keys(statuses).length > 0 && (
        <div className="mb-6 flex flex-wrap gap-2">
            {Object.entries(statuses).map(([key, status]) => (
                <div key={key} className={`border-2 px-3 py-1 text-[8px] font-black uppercase tracking-widest flex items-center gap-2 ${
                    status === "running" || status.startsWith("step") ? "bg-black text-white border-black" : "bg-white text-black border-black"
                }`}>
                    <span className={`h-1 w-1 rounded-full ${status === "running" || status.startsWith("step") ? "bg-white animate-pulse" : "bg-black"}`} />
                    {key.split("/").pop()} : {status}
                </div>
            ))}
        </div>
      )}

      <div className="h-96 w-full">
        {modelKeys.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center text-center">
            <div className="mb-2 text-2xl">⚖️</div>
            <div className="text-[10px] font-black uppercase tracking-widest text-black/40 max-w-[200px]">
              No benchmark data yet. Select models above and click "SET ACTIVE" to add them to the race.
            </div>
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData} margin={{ top: 5, right: 20, left: -10, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#00000015" vertical={false} />
              <XAxis 
                dataKey="step" 
                stroke="#000000" 
                fontSize={11} 
                fontWeight="bold" 
                tickLine={true} 
                axisLine={true}
                interval={0}
                label={{ value: "Tournament Step", position: "insideBottom", offset: -5, fontSize: 10, fontWeight: 900}}
              />
              <YAxis 
                domain={[0, 1]} 
                stroke="#000000" 
                fontSize={11} 
                fontWeight="bold" 
                tickLine={true} 
                axisLine={true}
                label={{ value: "Total Reward", angle: -90, position: "insideLeft", offset: 15, fontSize: 10, fontWeight: 900 }}
              />
              <Tooltip
                contentStyle={{ 
                  backgroundColor: "#ffffff", 
                  borderColor: "#000000",
                  borderWidth: "2px",
                  borderRadius: "0px",
                  fontSize: "11px",
                  fontWeight: "bold"
                }}
              />
              <Legend 
                iconType="rect" 
                wrapperStyle={{ paddingTop: "25px", fontSize: "11px", fontWeight: "900", textTransform: "uppercase", letterSpacing: "0.05em" }} 
              />
              {modelKeys.map((key, index) => (
                <Line
                  key={key}
                  type="monotone"
                  dataKey={key}
                  stroke={COLORS[index % COLORS.length]}
                  strokeWidth={3}
                  name={key.replace("/", " / ")}
                  dot={{ r: 4, fill: COLORS[index % COLORS.length] }}
                  activeDot={{ r: 6, stroke: 'white', strokeWidth: 2 }}
                  animationDuration={500}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
