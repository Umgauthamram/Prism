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
      <div className="flex h-64 items-center justify-center border-2 border-black bg-red-50 text-red-600 font-bold uppercase text-xs">
        {error}
      </div>
    );
  }

  if (data.length === 0) {
    return (
      <div className="flex h-64 items-center justify-center border-2 border-black bg-white text-black/20 font-black uppercase text-xs">
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
    <div className="glass-panel p-6">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h3 className="text-sm font-black uppercase tracking-widest text-black">
            Reward Trajectory
          </h3>
          <p className="text-xs text-black/40">Real-time performance across 5 reward vectors</p>
        </div>
      </div>
      <div className="h-96 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData} margin={{ top: 5, right: 20, left: -10, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#00000015" vertical={false} />
            <XAxis dataKey="step" stroke="#000000" fontSize={11} fontWeight="bold" tickLine={true} axisLine={true} />
            <YAxis domain={[0, 1]} stroke="#000000" fontSize={11} fontWeight="bold" tickLine={true} axisLine={true} />
            <Tooltip
              contentStyle={{ 
                backgroundColor: "#ffffff", 
                borderColor: "#000000",
                borderWidth: "2px",
                borderRadius: "0px",
                fontSize: "11px",
                fontWeight: "bold"
              }}
              itemStyle={{ padding: "2px 0" }}
            />
            <Legend 
              iconType="rect" 
              wrapperStyle={{ paddingTop: "25px", fontSize: "11px", fontStyle: "normal", fontWeight: "900", textTransform: "uppercase", letterSpacing: "0.05em" }} 
            />
            <Line
              type="monotone"
              dataKey="total"
              stroke="#000000"
              strokeWidth={4}
              name="Total Reward"
              dot={false}
              activeDot={{ r: 6, stroke: 'white', strokeWidth: 2 }}
              animationDuration={500}
            />
            <Line
              type="monotone"
              dataKey="progress"
              stroke="#3b82f6"
              strokeWidth={2.5}
              name="Progress"
              dot={false}
            />
            <Line
              type="monotone"
              dataKey="atomic"
              stroke="#f59e0b"
              strokeWidth={2.5}
              name="Atomic"
              dot={false}
            />
            <Line
              type="monotone"
              dataKey="coord"
              stroke="#8b5cf6"
              strokeWidth={2.5}
              name="Coord"
              dot={false}
            />
            <Line
              type="monotone"
              dataKey="hallucination"
              stroke="#ef4444"
              strokeWidth={2.5}
              name="Hallucination"
              dot={false}
            />
            <Line
              type="monotone"
              dataKey="terminal"
              stroke="#ec4899"
              strokeWidth={2.5}
              name="Terminal"
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
