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
      <div className="flex h-64 items-center justify-center border-2 border-black bg-white text-black/20 font-black uppercase text-xs">
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
    <div className="glass-panel p-6">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h3 className="text-sm font-black uppercase tracking-widest text-black">
            Cross-Domain Generalization
          </h3>
          <p className="text-xs text-black/40">Zero-shot transfer performance across domains</p>
        </div>
      </div>
      <div className="h-96 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={groupedData} margin={{ top: 5, right: 20, left: -10, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#00000015" vertical={false} />
            <XAxis dataKey="eval_episode" stroke="#000000" fontSize={11} fontWeight="bold" tickLine={true} axisLine={true} />
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
            />
            <Legend 
              iconType="rect" 
              wrapperStyle={{ paddingTop: "25px", fontSize: "11px", fontWeight: "900", textTransform: "uppercase", letterSpacing: "0.05em" }} 
            />
            
            {metrics.curriculum_stages.map((stage) => (
              <ReferenceLine
                key={stage.stage}
                x={stage.stage * 100}
                stroke="#00000030"
                strokeDasharray="5 5"
                label={{ value: `Stage ${stage.stage}`, position: 'top', fill: '#000000', fontSize: 10, fontWeight: '900' }}
              />
            ))}

            <Line type="monotone" dataKey="debug" stroke="#10b981" strokeWidth={3} name="Debug" dot={{ r: 5, fill: '#10b981' }} activeDot={{ r: 7 }} />
            <Line type="monotone" dataKey="market_research" stroke="#3b82f6" strokeWidth={3} name="Research" dot={{ r: 5, fill: '#3b82f6' }} activeDot={{ r: 7 }} />
            <Line type="monotone" dataKey="etl" stroke="#ec4899" strokeWidth={3} name="ETL" dot={{ r: 5, fill: '#ec4899' }} activeDot={{ r: 7 }} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
