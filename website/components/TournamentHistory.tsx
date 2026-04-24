"use client";

import React, { useEffect, useState } from "react";
import { fetchHistory as apiFetchHistory, HistoryItem } from "../lib/api";

interface HistoryRecord {
  id: string;
  model: string;
  provider: string;
  domain: string;
  final_reward: number;
  steps: number;
  timestamp: number;
}

export default function TournamentHistory() {
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchHistoryData = async () => {
    try {
      const data = await apiFetchHistory();
      setHistory(data);
    } catch (err) {
      console.error("Failed to fetch history", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHistoryData();
    const interval = setInterval(fetchHistoryData, 5000);
    return () => clearInterval(interval);
  }, []);

  if (loading && history.length === 0) {
    return (
      <div className="glass-panel p-6 text-center text-[10px] font-black uppercase tracking-widest text-black/40">
        Loading Archive...
      </div>
    );
  }

  return (
    <div className="glass-panel p-6 overflow-hidden">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h3 className="text-sm font-black uppercase tracking-widest text-black">Tournament Archive</h3>
          <p className="text-xs text-black/40">Persistent evaluation history</p>
        </div>
        <div className="text-[10px] font-black text-white bg-black px-2 py-1 border-2 border-black">
          {history.length} RECORDS
        </div>
      </div>

      <div className="max-h-64 overflow-y-auto space-y-2 pr-2 custom-scrollbar">
        {history.length === 0 ? (
          <div className="text-center py-8 text-[10px] font-black uppercase tracking-widest text-gray-600">
            No history found. Run a tournament to begin archiving.
          </div>
        ) : (
          history.map((record) => (
            <div 
              key={record.id} 
              className="flex items-center justify-between p-3 border-2 border-black bg-white hover:bg-gray-50 transition-all group"
            >
              <div className="flex flex-col gap-1">
                <div className="flex items-center gap-2">
                  <span className="text-[10px] font-black uppercase text-black truncate max-w-[150px]">
                    {record.model.split("/").pop()}
                  </span>
                  <span className="text-[8px] font-black uppercase tracking-widest px-1.5 py-0.5 border border-black bg-black text-white">
                    {record.domain}
                  </span>
                </div>
                <div className="text-[8px] text-black/40 font-mono">
                  ID: {record.id.slice(0, 8)}... | {new Date(record.timestamp * 1000).toLocaleTimeString()}
                </div>
              </div>

              <div className="flex items-center gap-4">
                <div className="text-right">
                  <div className="text-[10px] font-black text-black">
                    {record.final_reward.toFixed(2)}
                  </div>
                  <div className="text-[8px] font-black text-black/40 uppercase">
                    {record.steps} STEPS
                  </div>
                </div>
                <button 
                  onClick={() => window.open(`${process.env.NEXT_PUBLIC_ENV_URL || ''}/history/${record.id}`, '_blank')}
                  className="opacity-0 group-hover:opacity-100 transition-all bg-black text-white px-3 py-1.5 text-[9px] font-black uppercase tracking-widest border border-black"
                >
                  View JSON
                </button>
              </div>
            </div>
          ))
        )}
      </div>

      <style jsx>{`
        .custom-scrollbar::-webkit-scrollbar {
          width: 4px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
          background: transparent;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background: rgba(255, 255, 255, 0.1);
          border-radius: 10px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover {
          background: rgba(255, 255, 255, 0.2);
        }
      `}</style>
    </div>
  );
}
