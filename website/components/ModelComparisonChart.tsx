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

export default function ModelComparisonChart() {
  const [data, setData] = useState<Record<string, RewardPoint[]>>({});
  const [loading, setLoading] = useState(true);
  const [tournamentRunning, setTournamentRunning] = useState(false);
  const [statuses, setStatuses] = useState<Record<string, string>>({});

  const startTournament = async () => {
    // 1. Get all models that the user has configured/selected
    const activeDomainElement = document.querySelector('.bg-emerald-500\\/20');
    const activeDomain = activeDomainElement?.textContent?.toLowerCase().trim() || "debug";
    
    setTournamentRunning(true);
    try {
        // Fetch current active models from backend comparison state
        const comp = await fetchModelComparison();
        const modelsToRun = Object.keys(comp.models);

        if (modelsToRun.length === 0) {
            // Fallback to defaults if none active
            modelsToRun.push("groq/llama-3.3-70b-versatile", "gemini/gemini-2.0-flash");
        }

        await Promise.all(modelsToRun.map(m => {
            const [provider, model] = m.includes("/") ? m.split("/") : ["groq", m];
            return runTournamentEpisode(provider, model, activeDomain);
        }));
    } finally {
        setTournamentRunning(false);
    }
  };

  const runTournamentEpisode = async (provider: string, model: string, domain: string) => {
    try {
        setStatuses(prev => ({ ...prev, [`${provider}/${model}`]: "running" }));
        const obs = await resetEpisode({ task_domain: domain as any, agents: 4, failure_rate: 0, seed: 42 });
        const eid = obs.episode_id;

        await setModelConfig(provider, model, "SAVED", eid);

        let done = false;
        let currentStep = 0;
        while (!done && currentStep < 30) {
            const data = await step("checkpoint", {}, eid);
            done = data.terminated;
            currentStep++;
            await new Promise(r => setTimeout(r, 1000));
        }
        setStatuses(prev => ({ ...prev, [`${provider}/${model}`]: "finished" }));
    } catch (err) {
        console.error(`Tournament episode for ${model} failed`, err);
    }
  };

  useEffect(() => {
    const poll = async () => {
      const result = await fetchModelComparison();
      setData(result.models);
      setLoading(false);
    };

    poll();
    const interval = setInterval(poll, 2000);
    return () => clearInterval(interval);
  }, []);

  const modelKeys = Object.keys(data);

  if (loading) {
    return (
      <div className="glass-panel flex h-72 items-center justify-center rounded-2xl text-[10px] font-black uppercase tracking-widest text-gray-600">
        Syncing comparison matrix...
      </div>
    );
  }

  const maxSteps = Math.max(...modelKeys.map(k => data[k].length || 0), 0);
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
    <div className="glass-panel rounded-2xl p-6">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h3 className="text-sm font-black uppercase tracking-widest text-white">Model Agnosticism Proof</h3>
          <p className="text-xs text-gray-500">Cross-LLM reward trajectory comparison</p>
        </div>
        <button 
            onClick={startTournament}
            disabled={tournamentRunning}
            className={`rounded-lg px-4 py-2 text-[10px] font-black uppercase tracking-widest transition-all ${
                tournamentRunning 
                ? "bg-emerald-500/20 text-emerald-500 border border-emerald-500/50 animate-pulse" 
                : "bg-white text-black hover:bg-gray-200"
            }`}
        >
          {tournamentRunning ? "Tournament Active" : "Start Tournament"}
        </button>
      </div>

      {Object.keys(statuses).length > 0 && (
        <div className="mb-6 flex flex-wrap gap-2">
            {Object.entries(statuses).map(([key, status]) => (
                <div key={key} className={`rounded-lg border px-3 py-1 text-[8px] font-black uppercase tracking-widest flex items-center gap-2 ${
                    status === "running" ? "bg-blue-500/10 border-blue-500/30 text-blue-400" : "bg-emerald-500/10 border-emerald-500/30 text-emerald-400"
                }`}>
                    <span className={`h-1 w-1 rounded-full ${status === "running" ? "bg-blue-500 animate-pulse" : "bg-emerald-500"}`} />
                    {key.split("/").pop()} : {status}
                </div>
            ))}
        </div>
      )}

      <div className="h-72 w-full">
        {modelKeys.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center text-center">
            <div className="mb-2 text-2xl">⚖️</div>
            <div className="text-[10px] font-black uppercase tracking-widest text-gray-500 max-w-[200px]">
              No benchmark data yet. Select models above and click "SET ACTIVE" to add them to the race.
            </div>
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData} margin={{ top: 5, right: 5, left: -20, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#ffffff05" vertical={false} />
              <XAxis dataKey="step" stroke="#4b5563" fontSize={10} tickLine={false} axisLine={false} />
              <YAxis domain={[0, 1]} stroke="#4b5563" fontSize={10} tickLine={false} axisLine={false} />
              <Tooltip
                contentStyle={{ 
                  backgroundColor: "rgba(5, 5, 8, 0.9)", 
                  borderColor: "rgba(255, 255, 255, 0.1)",
                  borderRadius: "12px",
                  backdropFilter: "blur(10px)",
                  fontSize: "10px"
                }}
              />
              <Legend 
                iconType="circle" 
                wrapperStyle={{ paddingTop: "20px", fontSize: "9px", fontWeight: "bold", textTransform: "uppercase", letterSpacing: "0.05em" }} 
              />
              {modelKeys.map((key, index) => (
                <Line
                  key={key}
                  type="monotone"
                  dataKey={key}
                  stroke={COLORS[index % COLORS.length]}
                  strokeWidth={2}
                  strokeDasharray={index % 2 === 0 ? "" : "5 5"} // Differentiate overlapping lines
                  name={key.replace("/", " / ")}
                  dot={{ r: 3, fill: COLORS[index % COLORS.length] }}
                  activeDot={{ r: 5, stroke: 'white', strokeWidth: 2 }}
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
