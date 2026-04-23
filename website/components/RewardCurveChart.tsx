"use client";

import React, { useEffect, useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { fetchMetrics, Metrics, RewardPoint } from "@/lib/api";

export default function RewardCurveChart() {
  const [data, setData] = useState<RewardPoint[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const poll = async () => {
      try {
        const metrics = await fetchMetrics();
        setData(metrics.reward_curve);
        setError(null);
      } catch (err) {
        setError("Backend offline");
      }
    };

    poll();
    const interval = setInterval(poll, 2000);
    return () => clearInterval(interval);
  }, []);

  if (error) {
    return (
      <div className="flex h-64 items-center justify-center rounded-lg border border-red-900 bg-red-950/20 text-red-500">
        {error}
      </div>
    );
  }

  if (data.length === 0) {
    return (
      <div className="flex h-64 items-center justify-center rounded-lg border border-gray-800 bg-[#0a0a0f] text-gray-500">
        Waiting for training data…
      </div>
    );
  }

  const chartData = data.map((p) => ({
    step: p.step,
    total: p.total,
    progress: p.breakdown.progress_delta,
    atomic: p.breakdown.atomic_health,
    coord: p.breakdown.coord_efficiency,
    hallucination: p.breakdown.hallucination_penalty,
    terminal: p.breakdown.terminal_bonus,
  }));

  return (
    <div className="glass-panel rounded-2xl p-6">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h3 className="text-sm font-bold uppercase tracking-wider text-white">
            Reward Trajectories
          </h3>
          <p className="text-xs text-gray-500">Real-time performance across 5 reward vectors</p>
        </div>
      </div>
      <div className="h-72 w-full">
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
              itemStyle={{ padding: "2px 0" }}
            />
            <Legend 
              iconType="circle" 
              wrapperStyle={{ paddingTop: "20px", fontSize: "10px", fontWeight: "bold", textTransform: "uppercase", letterSpacing: "0.05em" }} 
            />
            <Line
              type="monotone"
              dataKey="total"
              stroke="#10b981"
              strokeWidth={3}
              name="Total Reward"
              dot={false}
              animationDuration={500}
            />
            <Line
              type="monotone"
              dataKey="progress"
              stroke="#3b82f6"
              strokeWidth={1.5}
              strokeDasharray="4 4"
              name="Progress"
              dot={false}
            />
            <Line
              type="monotone"
              dataKey="atomic"
              stroke="#f59e0b"
              strokeWidth={1.5}
              strokeDasharray="4 4"
              name="Atomic"
              dot={false}
            />
            <Line
              type="monotone"
              dataKey="coord"
              stroke="#8b5cf6"
              strokeWidth={1.5}
              strokeDasharray="4 4"
              name="Coord"
              dot={false}
            />
            <Line
              type="monotone"
              dataKey="hallucination"
              stroke="#ef4444"
              strokeWidth={1.5}
              strokeDasharray="4 4"
              name="Hallucination"
              dot={false}
            />
            <Line
              type="monotone"
              dataKey="terminal"
              stroke="#ec4899"
              strokeWidth={1.5}
              strokeDasharray="4 4"
              name="Terminal"
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
