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
    <div className="glass-panel space-y-6 p-6">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-black uppercase tracking-widest text-black">Model Policy</h3>
        {config?.active_model ? (
          <div className="flex items-center gap-2 border-2 border-black bg-black px-3 py-1">
            <span className="h-1.5 w-1.5 rounded-full bg-white animate-pulse" />
            <span className="text-[9px] font-black uppercase tracking-widest text-white">
                {config.active_provider} / {config.active_model.split('-').pop()}
            </span>
          </div>
        ) : (
          <span className="text-[9px] font-black uppercase tracking-widest text-black/40">No model active</span>
        )}
      </div>

      <div className="grid grid-cols-3 gap-2">
        {Object.keys(available).map((p) => (
          <button
            key={p}
            onClick={() => setSelectedProvider(p)}
            className={`flex flex-col items-center justify-center border-2 py-3 transition-all ${
              selectedProvider === p
                ? "border-black bg-black text-white shadow-[4px_4px_0px_rgba(0,0,0,1)]"
                : "border-black bg-white text-black hover:bg-gray-50"
            }`}
          >
            <span className="text-[10px] font-black uppercase tracking-widest">{p}</span>
            {config?.providers[p]?.configured && (
              <span className="mt-1 text-[8px] font-bold text-black opacity-40">✓ SAVED</span>
            )}
          </button>
        ))}
      </div>

      <div className="space-y-2">
        <label className="text-[10px] font-black uppercase tracking-widest text-black/40">Select Model</label>
        <select
          value={selectedModel}
          onChange={(e) => setSelectedModel(e.target.value)}
          className="w-full border-2 border-black bg-white p-3 text-xs text-black focus:outline-none"
        >
          {available[selectedProvider]?.models.map((m) => (
            <option key={m} value={m}>
              {m}
            </option>
          ))}
        </select>
      </div>

      <div className="space-y-2">
        <div className="flex justify-between items-center">
          <label className="text-[10px] font-black uppercase tracking-widest text-black/40">
            {selectedProvider.toUpperCase()} API KEY
          </label>
          <button 
            onClick={() => setShowKey(!showKey)}
            className="text-[9px] font-bold text-black/60 hover:text-black"
          >
            {showKey ? "HIDE" : "SHOW"}
          </button>
        </div>
        <input
          type={showKey ? "text" : "password"}
          value={apiKey}
          onChange={(e) => setApiKey(e.target.value)}
          placeholder={`Enter your ${selectedProvider} key...`}
          className="w-full border-2 border-black bg-white p-3 font-mono text-xs text-black focus:outline-none"
        />
      </div>

      <div className="grid grid-cols-2 gap-3">
        <button
          onClick={handleTest}
          disabled={loading || !apiKey}
          className="border-2 border-black bg-white py-3 text-[10px] font-black uppercase tracking-widest text-black hover:bg-gray-100 disabled:opacity-50"
        >
          {loading ? "..." : "Test Link"}
        </button>
        <button
          onClick={handleSave}
          disabled={loading || !apiKey}
          className="bg-black py-3 text-[10px] font-black uppercase tracking-widest text-white hover:bg-gray-800 disabled:opacity-50 border-2 border-black"
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
