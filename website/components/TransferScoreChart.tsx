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
  ReferenceLine,
} from "recharts";
import { fetchMetrics, Metrics, TransferPoint, CurriculumStage } from "@/lib/api";

export default function TransferScoreChart() {
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const poll = async () => {
      try {
        const data = await fetchMetrics();
        setMetrics(data);
        setError(null);
      } catch (err) {
        setError("Backend offline");
      }
    };

    poll();
    const interval = setInterval(poll, 2000);
    return () => clearInterval(interval);
  }, []);

  if (error) return null;

  if (!metrics || metrics.transfer_scores.length === 0) {
    return (
      <div className="flex h-64 items-center justify-center rounded-lg border border-gray-800 bg-[#0a0a0f] text-gray-500">
        Transfer scores logged every 50 episodes…
      </div>
    );
  }

  // Group transfer scores by eval_episode
  const groupedData: any[] = [];
  const episodes = Array.from(new Set(metrics.transfer_scores.map((s) => s.eval_episode)));
  
  episodes.sort((a, b) => a - b).forEach((ep) => {
    const point: any = { eval_episode: ep };
    metrics.transfer_scores.filter(s => s.eval_episode === ep).forEach(s => {
      point[s.domain] = s.score;
    });
    groupedData.push(point);
  });

  return (
    <div className="glass-panel rounded-2xl p-6">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h3 className="text-sm font-bold uppercase tracking-wider text-white">
            Cross-Domain Generalization
          </h3>
          <p className="text-xs text-gray-500">Zero-shot transfer performance across domains</p>
        </div>
      </div>
      <div className="h-72 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={groupedData} margin={{ top: 5, right: 5, left: -20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#ffffff05" vertical={false} />
            <XAxis dataKey="eval_episode" stroke="#4b5563" fontSize={10} tickLine={false} axisLine={false} />
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
              wrapperStyle={{ paddingTop: "20px", fontSize: "10px", fontWeight: "bold", textTransform: "uppercase", letterSpacing: "0.05em" }} 
            />
            
            {metrics.curriculum_stages.map((stage) => (
              <ReferenceLine
                key={stage.stage}
                x={stage.stage * 100}
                stroke="#ffffff10"
                strokeDasharray="3 3"
                label={{ value: `Stage ${stage.stage}`, position: 'top', fill: '#4b5563', fontSize: 8, fontWeight: 'bold' }}
              />
            ))}

            <Line type="monotone" dataKey="debug" stroke="#10b981" strokeWidth={2} name="Debug" dot={{ r: 4, fill: '#10b981' }} activeDot={{ r: 6 }} />
            <Line type="monotone" dataKey="market_research" stroke="#3b82f6" strokeWidth={2} name="Research" dot={{ r: 4, fill: '#3b82f6' }} activeDot={{ r: 6 }} />
            <Line type="monotone" dataKey="etl" stroke="#ec4899" strokeWidth={2} name="ETL" dot={{ r: 4, fill: '#ec4899' }} activeDot={{ r: 6 }} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
