"use client";

import React, { useState, useEffect } from "react";
import { fetchAvailableModels, fetchModelsConfig, setModelConfig, testConnection, ModelsConfig } from "@/lib/api";

export default function ModelSelector() {
  const [available, setAvailable] = useState<Record<string, { models: string[] }>>({});
  const [config, setConfig] = useState<ModelsConfig | null>(null);
  
  const [selectedProvider, setSelectedProvider] = useState<string>("groq");
  const [selectedModel, setSelectedModel] = useState<string>("");
  const [apiKey, setApiKey] = useState<string>("");
  const [showKey, setShowKey] = useState(false);
  
  const [loading, setLoading] = useState(false);
  const [testResult, setTestResult] = useState<{ success: boolean; latency: number; msg: string } | null>(null);
  const [status, setStatus] = useState<{ type: "success" | "error"; msg: string } | null>(null);

  useEffect(() => {
    const init = async () => {
      try {
        const [availData, configData] = await Promise.all([
          fetchAvailableModels(),
          fetchModelsConfig()
        ]);
        setAvailable(availData);
        setConfig(configData);
        
        // Set default model if available
        if (availData[selectedProvider]?.models.length > 0) {
          setSelectedModel(availData[selectedProvider].models[0]);
        }
      } catch (err) {
        // Silent until backend is ready
        console.debug("Models configuration not yet available");
      }
    };
    init();
  }, []);

  useEffect(() => {
    if (available[selectedProvider]?.models.length > 0) {
      setSelectedModel(available[selectedProvider].models[0]);
    }
  }, [selectedProvider, available]);

  const handleTest = async () => {
    if (!apiKey) return;
    setLoading(true);
    setTestResult(null);
    try {
      const res = await testConnection(selectedProvider, selectedModel, apiKey);
      setTestResult({ success: res.success, latency: res.latency_ms, msg: res.response });
    } catch (err) {
      setTestResult({ success: false, latency: 0, msg: "Connection failed" });
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    if (!apiKey) {
        setStatus({ type: "error", msg: "API Key required" });
        return;
    }
    setLoading(true);
    setStatus(null);
    try {
      await setModelConfig(selectedProvider, selectedModel, apiKey);
      const newConfig = await fetchModelsConfig();
      setConfig(newConfig);
      setStatus({ type: "success", msg: "Model activated successfully" });
    } catch (err) {
      setStatus({ type: "error", msg: "Failed to activate model" });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="glass-panel space-y-6 rounded-2xl p-6">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-black uppercase tracking-widest text-white">Model Selector</h3>
        {config?.active_model ? (
          <div className="flex items-center gap-2 rounded-full bg-emerald-500/10 border border-emerald-500/20 px-3 py-1">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
            <span className="text-[9px] font-black uppercase tracking-widest text-emerald-400">
                {config.active_provider} / {config.active_model.split('-').pop()}
            </span>
          </div>
        ) : (
          <span className="text-[9px] font-black uppercase tracking-widest text-gray-600">No model active</span>
        )}
      </div>

      {/* Provider Selector */}
      <div className="grid grid-cols-3 gap-2">
        {Object.keys(available).map((p) => (
          <button
            key={p}
            onClick={() => setSelectedProvider(p)}
            className={`flex flex-col items-center justify-center rounded-xl border py-3 transition-all ${
              selectedProvider === p
                ? "border-emerald-500/50 bg-emerald-500/10 text-emerald-400"
                : "border-white/5 bg-white/5 text-gray-500 hover:bg-white/10"
            }`}
          >
            <span className="text-[10px] font-black uppercase tracking-widest">{p}</span>
            {config?.providers[p]?.configured && (
              <span className="mt-1 text-[8px] font-bold text-emerald-500">✓ SAVED</span>
            )}
          </button>
        ))}
      </div>

      {/* Model Selector */}
      <div className="space-y-2">
        <label className="text-[10px] font-black uppercase tracking-widest text-gray-500">Select Model</label>
        <select
          value={selectedModel}
          onChange={(e) => setSelectedModel(e.target.value)}
          className="w-full rounded-xl border border-white/5 bg-black/40 p-3 text-xs text-white focus:border-emerald-500/50 focus:outline-none"
        >
          {available[selectedProvider]?.models.map((m) => (
            <option key={m} value={m}>
              {m}
            </option>
          ))}
        </select>
      </div>

      {/* API Key */}
      <div className="space-y-2">
        <div className="flex justify-between items-center">
          <label className="text-[10px] font-black uppercase tracking-widest text-gray-500">
            {selectedProvider.toUpperCase()} API KEY
          </label>
          <button 
            onClick={() => setShowKey(!showKey)}
            className="text-[9px] font-bold text-gray-600 hover:text-gray-400"
          >
            {showKey ? "HIDE" : "SHOW"}
          </button>
        </div>
        <input
          type={showKey ? "text" : "password"}
          value={apiKey}
          onChange={(e) => setApiKey(e.target.value)}
          placeholder={`Enter your ${selectedProvider} key...`}
          className="w-full rounded-xl border border-white/5 bg-black/40 p-3 font-mono text-xs text-gray-300 focus:border-emerald-500/50 focus:outline-none"
        />
      </div>

      {/* Action Buttons */}
      <div className="grid grid-cols-2 gap-3">
        <button
          onClick={handleTest}
          disabled={loading || !apiKey}
          className="rounded-xl border border-white/10 bg-white/5 py-3 text-[10px] font-black uppercase tracking-widest text-gray-300 hover:bg-white/10 disabled:opacity-50"
        >
          {loading ? "..." : "Test Link"}
        </button>
        <button
          onClick={handleSave}
          disabled={loading || !apiKey}
          className="rounded-xl bg-white py-3 text-[10px] font-black uppercase tracking-widest text-black hover:bg-gray-200 disabled:opacity-50"
        >
          {loading ? "..." : "Set Active"}
        </button>
      </div>

      {/* Result Box */}
      {testResult && (
        <div className={`rounded-xl border p-3 text-[10px] font-bold ${testResult.success ? "border-emerald-500/20 bg-emerald-500/5 text-emerald-400" : "border-red-500/20 bg-red-500/5 text-red-400"}`}>
          <div className="flex justify-between mb-1">
            <span>{testResult.success ? "SUCCESS" : "FAILED"}</span>
            {testResult.success && <span>{testResult.latency}ms</span>}
          </div>
          <div className="font-mono text-gray-500 truncate">{testResult.msg}</div>
        </div>
      )}

      {status && (
        <p className={`text-center text-[9px] font-black uppercase tracking-[0.2em] ${status.type === "success" ? "text-emerald-500" : "text-red-500"}`}>
          {status.msg}
        </p>
      )}
    </div>
  );
}
