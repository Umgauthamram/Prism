"use client";

import React, { useEffect, useState, useRef } from "react";
import { fetchState, EpisodeState, step, resetEpisode, TaskDomain, AgentCount, FailureRate, startICLTraining, fetchModelsConfig } from "@/lib/api";

const roleColors: Record<string, string> = {
  Planner: "bg-indigo-600 text-white border-black",
  Researcher: "bg-blue-600 text-white border-black",
  Coder: "bg-emerald-600 text-white border-black",
  Critic: "bg-amber-600 text-white border-black",
  Synthesizer: "bg-rose-600 text-white border-black",
};

const statusColors: Record<string, string> = {
  pending: "bg-white text-black/20 border-black",
  running: "bg-white text-black border-black animate-pulse",
  done: "bg-black text-white border-black",
  failed: "bg-red-600 text-white border-black",
};

interface EpisodeViewerProps {
  autoStartEval?: boolean;
  onAutoEvalConsumed?: () => void;
  onEvalComplete?: () => void;
  onOptimizeFurther?: () => void;
  showResultsMode?: boolean;
  config: {
    domain: TaskDomain;
    agents: AgentCount;
    failureRate: FailureRate;
    seed: number;
  };
  evalContext?: {
    prevScore: number;
    modelName: string;
    parentEpisodeId?: string;
  } | null;
  onEpisodeIdUpdate?: (id: string) => void;
}

export default function EpisodeViewer({
  autoStartEval = false,
  onAutoEvalConsumed,
  onEvalComplete,
  onOptimizeFurther,
  showResultsMode = false,
  config,
  evalContext,
  onEpisodeIdUpdate
}: EpisodeViewerProps) {
  const [state, setState] = useState<EpisodeState | null>(null);
  const [autoRun, setAutoRun] = useState(false);
  const [stepping, setStepping] = useState(false);
  const [showToolOutput, setShowToolOutput] = useState(false);
  const [stepTimers, setStepTimers] = useState<{step: number, duration: number}[]>([]);
  const [isPostTrainingEval, setIsPostTrainingEval] = useState(false);
  const [showResults, setShowResults] = useState(false);
  const [preTrainingScore, setPreTrainingScore] = useState<number | null>(null);
  const autoEvalTriggered = useRef(false);
  const manualStateUpdate = useRef(false);

  useEffect(() => {
    const poll = async () => {
      try {
        if (manualStateUpdate.current) return;
        const data = await fetchState();
        setState(data);
      } catch (err) {
        console.debug("Episode state not yet available");
      }
    };

    poll();
    const interval = setInterval(poll, 1000);
    return () => clearInterval(interval);
  }, []);

  // Sync episode ID up to parent for the 'linker'
  useEffect(() => {
    if (state?.episode_id) {
      onEpisodeIdUpdate?.(state.episode_id);
    }
  }, [state?.episode_id, onEpisodeIdUpdate]);
  
  // Re-hydrate post-training mode from backend state (persistence after refresh)
  useEffect(() => {
    if (state?.parent_episode_id && !isPostTrainingEval) {
      setIsPostTrainingEval(true);
      if (state?.parent_score) setPreTrainingScore(state.parent_score);
    }
  }, [state?.parent_episode_id, state?.parent_score, isPostTrainingEval]);

  // Auto-start evaluation when ICL training sends us here
  useEffect(() => {
    if (autoStartEval && !autoEvalTriggered.current) {
      autoEvalTriggered.current = true;
      setIsPostTrainingEval(true);
      setShowResults(false);
      
      // Prioritize backend linker score, then evalContext, then current reward
      const prevScore = state?.parent_score ?? evalContext?.prevScore ?? state?.last_reward ?? 0;
      setPreTrainingScore(prevScore);

      // Reset episode and start auto-run using SHARED CONFIG
      const startEval = async () => {
        try {
          const parentScore = evalContext?.prevScore || state?.last_reward || 0;
          const parentId = evalContext?.parentEpisodeId || state?.episode_id;
          
          await resetEpisode({
            task_domain: config.domain,
            agents: config.agents,
            failure_rate: config.failureRate,
            seed: config.seed,
            parent_episode_id: parentId,
            parent_score: parentScore,
          });
          // Small delay for reset to propagate and backend to initialize
          await new Promise(r => setTimeout(r, 1200));
          const newState = await fetchState();
          
          // CRITICAL: Re-apply ICL Training to the NEW episode ID
          // This follows the 'PHASE C' flow requested by the user
          try {
            const mConfig = await fetchModelsConfig();
            if (mConfig.active_provider && mConfig.active_model) {
              await startICLTraining(
                mConfig.active_provider,
                mConfig.active_model,
                config.domain,
                newState.episode_id
              );
              console.log(`[ICL] Training context re-injected into episode ${newState.episode_id}`);
            }
          } catch (iclErr) {
            console.error("Failed to re-inject ICL context into new episode:", iclErr);
          }

          manualStateUpdate.current = true;
          setState(newState);
          setStepTimers([]);
          setAutoRun(true);
          onAutoEvalConsumed?.();
          setTimeout(() => { manualStateUpdate.current = false; }, 3000); // Resume polling after 3s
        } catch (err) {
          console.error("Failed to start post-training evaluation:", err);
          autoEvalTriggered.current = false; // Allow retry
          onAutoEvalConsumed?.();
        }
      };
      startEval();
    }
    if (!autoStartEval) {
      autoEvalTriggered.current = false;
    }
  }, [autoStartEval, onAutoEvalConsumed, config, evalContext]); // Removed state dependency to prevent loops

  // Detect episode completion during post-training eval
  useEffect(() => {
    if (isPostTrainingEval && state?.terminated && autoRun) {
      setAutoRun(false);
      // Don't show results immediately — user clicks "Show Results"
      onEvalComplete?.();
    }
  }, [isPostTrainingEval, state?.terminated, autoRun, onEvalComplete]);

  useEffect(() => {
    let timer: any;
    if (autoRun && state && !state.terminated && !stepping) {
      timer = setTimeout(handleStep, 1500);
    }
    return () => clearTimeout(timer);
  }, [autoRun, state?.step, state?.terminated, stepping]);

  const handleStep = async () => {
    if (!state || state.terminated || stepping) return;
    setStepping(true);
    const start = Date.now();
    try {
      await step("checkpoint", {});
      const end = Date.now();
      const duration = (end - start) / 1000;
      
      const newState = await fetchState();
      setState(newState);
      setStepTimers(prev => [...prev, { step: state.step, duration }]);
    } catch (err) {
      console.error("Step failed");
    } finally {
      setStepping(false);
    }
  };

  // Score thresholds
  const reward = state?.last_reward ?? 0;
  const isTopPerformance = reward >= 0.98;

  if (!state) {
    return (
      <div className="flex h-96 items-center justify-center border-2 border-black bg-white text-black">
        Initializing environment state…
      </div>
    );
  }

  return (
    <div className="glass-panel space-y-8 p-8">
      {/* Post-Training Auto-Eval Banner */}
      {isPostTrainingEval && !state.terminated && (
        <div className="border-2 border-blue-500 bg-blue-50 p-4 flex items-center gap-3 animate-pulse">
          <span className="h-3 w-3 rounded-full bg-blue-500 animate-ping" />
          <div className="flex-1">
            <div className="text-[10px] font-black uppercase tracking-widest text-blue-700">
              Post-Training Evaluation Running
            </div>
            <div className="flex flex-wrap gap-2 mt-1">
              {evalContext?.modelName && (
                <span className="bg-blue-600 text-[8px] font-black text-white px-1.5 py-0.5 uppercase">
                  Model: {evalContext.modelName}
                </span>
              )}
              {state.parent_episode_id && (
                <span className="border border-blue-400 text-[8px] font-black text-blue-600 px-1.5 py-0.5 uppercase">
                  Linked to: {state.parent_episode_id.slice(0, 8)}...
                </span>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className={`border-2 px-4 py-2 text-[11px] font-black uppercase tracking-widest ${roleColors[state.agent_role]}`}>
            {state.agent_role}
          </div>
          {state.terminated && (
            <div className="rounded-lg bg-emerald-500/20 px-3 py-1.5 text-[10px] font-black uppercase tracking-widest text-emerald-500 border border-emerald-500/50">
              FINISHED
            </div>
          )}
          <div className="flex flex-col gap-1.5">
            <div className="flex items-center gap-2 text-[11px] font-black text-black uppercase tracking-widest">
                <span className="h-2 w-2 rounded-full bg-black animate-pulse" />
                Step {state.step}
            </div>
            <div className="h-2 w-40 border-2 border-black bg-black/5 overflow-hidden">
                <div 
                    className="h-full bg-black transition-all duration-500" 
                    style={{ width: `${Math.min((state.step / 30) * 100, 100)}%` }} 
                />
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setAutoRun(!autoRun)}
            className={`px-3 py-1.5 text-[9px] font-black uppercase tracking-widest border-2 transition-all ${
              autoRun ? "bg-black border-black text-white shadow-[4px_4px_0px_rgba(0,0,0,1)]" : "bg-white border-black text-black hover:bg-gray-100"
            }`}
          >
            {autoRun ? "Auto: ON" : "Auto: OFF"}
          </button>
          <button
            onClick={handleStep}
            disabled={stepping || state.terminated}
            className="bg-black px-3 py-1.5 text-[9px] font-black uppercase tracking-widest text-white hover:bg-gray-800 disabled:opacity-50 transition-all active:scale-95 border-2 border-black"
          >
            {stepping ? "..." : "Next Step"}
          </button>
        </div>
      </div>

      {/* Failure Banner */}
      {state.injected_failure_flag && (
        <div className="flex items-center justify-center gap-3 animate-pulse-soft rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-center">
          <span className="text-xl">⚠</span>
          <span className="text-xs font-black tracking-[0.2em] text-red-400">INJECTED FAILURE ACTIVE</span>
        </div>
      )}

      {/* Task Graph */}
      <div className="space-y-4">
        <h4 className="text-[11px] font-black uppercase tracking-[0.2em] text-black/40">Task Execution Graph</h4>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {Object.entries(state.task_graph || {}).map(([id, node]) => (
            <div key={id} className={`flex items-center justify-between border-2 p-4 transition-all hover:translate-x-1 ${statusColors[node.status]}`}>
              <span className="font-mono text-[11px] font-bold italic">{id}</span>
              <span className="text-[10px] font-black uppercase tracking-tighter">{node.status}</span>
            </div>
          ))}
        </div>
      </div>

      {/* ── Performance Diagnostic ── */}
      {state.feedback && (
        <div className={`border-2 p-4 space-y-2 ${
          reward >= 0.45
            ? "border-emerald-500 bg-emerald-50"
            : reward >= 0.25
            ? "border-yellow-500 bg-yellow-50"
            : "border-red-500 bg-red-50"
        }`}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className={`h-2 w-2 rounded-full ${
                reward >= 0.45
                  ? "bg-emerald-500"
                  : reward >= 0.25
                  ? "bg-yellow-500 animate-pulse"
                  : "bg-red-500 animate-pulse"
              }`} />
              <span className={`text-[9px] font-black uppercase tracking-widest ${
                reward >= 0.45
                  ? "text-emerald-700"
                  : reward >= 0.25
                  ? "text-yellow-700"
                  : "text-red-700"
              }`}>
                {reward >= 0.45
                  ? "Performing Well"
                  : reward >= 0.25
                  ? "Moderate Performance"
                  : "Underperforming"}
              </span>
            </div>
            <span className="text-sm font-mono font-black text-black">
              {reward.toFixed(4)}
            </span>
          </div>
          <p className={`text-[11px] leading-relaxed font-medium ${
            reward >= 0.45
              ? "text-emerald-800"
              : reward >= 0.25
              ? "text-yellow-800"
              : "text-red-800"
          }`}>
            {state.feedback}
          </p>
        </div>
      )}

      {/* ── Post-Training Results Panel ── */}
      {state.terminated && isPostTrainingEval && !showResults && (
        <button
          onClick={() => setShowResults(true)}
          className="w-full border-2 border-black bg-black py-4 text-[10px] font-black uppercase tracking-widest text-white hover:bg-gray-800 transition-all shadow-[3px_3px_0px_rgba(0,0,0,1)] active:translate-x-0.5 active:translate-y-0.5 active:shadow-none"
        >
          Show Comparison Results
        </button>
      )}

      {showResults && state.terminated && (
        <div className="space-y-4">
          {/* Model Banner */}
          {evalContext?.modelName && (
            <div className="border-2 border-blue-500 bg-blue-50 p-3 text-center">
              <span className="text-[10px] font-black uppercase tracking-widest text-blue-700">
                EVALUATED MODEL: {evalContext.modelName.replace(/\//g, " / ")}
              </span>
            </div>
          )}

          {/* Comparison Card */}
          <div className="grid grid-cols-2 gap-4">
            <div className="border-2 border-black/10 p-5 bg-white space-y-2">
              <div className="text-[10px] font-black uppercase tracking-widest text-black/40">Before Training</div>
              <div className="text-3xl font-mono font-black text-black/20">
                {preTrainingScore !== null ? Number(preTrainingScore).toFixed(4) : "0.0000"}
              </div>
            </div>
            <div className="border-2 border-black p-5 bg-black space-y-2">
              <div className="text-[10px] font-black uppercase tracking-widest text-white/40">After Training</div>
              <div className="text-3xl font-mono font-black text-white">
                {Number(reward).toFixed(4)}
              </div>
              {preTrainingScore !== null && Number(reward) !== Number(preTrainingScore) && (
                <div className={`text-[9px] font-black uppercase tracking-widest ${Number(reward) > Number(preTrainingScore) ? 'text-emerald-400' : 'text-red-400'}`}>
                  {Number(reward) > Number(preTrainingScore) ? '+' : ''}{(Number(reward) - Number(preTrainingScore)).toFixed(4)} {Number(reward) > Number(preTrainingScore) ? 'Improvement' : 'Regression'}
                </div>
              )}
            </div>
          </div>

          {/* Top Performance Achievement */}
          {isTopPerformance && (
            <div className="border-2 border-emerald-500 bg-emerald-50 p-5 space-y-2 text-center">
              <div className="text-2xl">🏆</div>
              <div className="text-sm font-black uppercase tracking-widest text-emerald-700">
                Top Performance Achieved
              </div>
              <p className="text-[11px] text-emerald-700 max-w-md mx-auto">
                This model has reached the top performance threshold (≥ 0.98).
                The ICL training loop is complete. No further optimization needed.
              </p>
            </div>
          )}

          {/* Results summary */}
          {!isTopPerformance && (
            <div className="border-2 border-black p-5 space-y-3 bg-white">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-black uppercase tracking-widest text-black">
                  Self-Correction Diagnostic
                </span>
              </div>
              {state.feedback && (
                <p className="text-[11px] text-black/70 leading-relaxed italic">
                  &ldquo;{state.feedback}&rdquo;
                </p>
              )}
            </div>
          )}

          {/* Action buttons */}
          {!isTopPerformance && (
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <button
                onClick={() => {
                  setIsPostTrainingEval(false);
                  setShowResults(false);
                  onOptimizeFurther?.();
                }}
                className="border-2 border-black bg-black py-3.5 text-[10px] font-black uppercase tracking-widest text-white hover:bg-gray-800 transition-all shadow-[3px_3px_0px_rgba(0,0,0,1)] active:translate-x-0.5 active:translate-y-0.5 active:shadow-none"
              >
                Optimize Further →
              </button>
              <button
                onClick={() => {
                  setIsPostTrainingEval(false);
                  setShowResults(false);
                }}
                className="border-2 border-black bg-white py-3.5 text-[10px] font-black uppercase tracking-widest text-black hover:bg-gray-100 transition-all shadow-[3px_3px_0px_rgba(0,0,0,1)] active:translate-x-0.5 active:translate-y-0.5 active:shadow-none"
              >
                Done — Keep Current Score
              </button>
            </div>
          )}

          {isTopPerformance && (
            <button
              onClick={() => {
                setIsPostTrainingEval(false);
                setShowResults(false);
              }}
              className="w-full border-2 border-emerald-600 bg-emerald-600 py-3.5 text-[10px] font-black uppercase tracking-widest text-white hover:bg-emerald-700 transition-all shadow-[3px_3px_0px_rgba(0,0,0,1)] active:translate-x-0.5 active:translate-y-0.5 active:shadow-none"
            >
              ✓ Training Complete — Close
            </button>
          )}
        </div>
      )}

      {/* Tool Output */}
      <div className="space-y-3">
        <button
          onClick={() => setShowToolOutput(!showToolOutput)}
          className="flex w-full items-center justify-between border-2 border-black bg-white p-3 text-[10px] font-black uppercase tracking-widest text-black transition-all hover:bg-gray-50"
        >
          <span>Last Tool Output</span>
          <span className="text-lg leading-none">{showToolOutput ? "−" : "+"}</span>
        </button>
        {showToolOutput && (
          <div className="relative group">
            <pre className="relative mt-2 overflow-x-auto border-2 border-black bg-white p-4 font-mono text-[10px] text-black custom-scrollbar leading-relaxed">
              {JSON.stringify(state.last_tool_output, null, 2)}
            </pre>
          </div>
        )}
      </div>

      {/* Step Latency Log */}
      <div className="space-y-3 pt-4 border-t border-white/5">
        <h4 className="text-[10px] font-black uppercase tracking-[0.2em] text-gray-500">Step Performance Log</h4>
        <div className="flex flex-wrap gap-2 max-h-24 overflow-y-auto custom-scrollbar">
            {stepTimers.length === 0 ? (
                <div className="text-[8px] text-gray-700 italic">No steps recorded yet...</div>
            ) : (
                stepTimers.map((t, idx) => (
                    <div key={idx} className="bg-white/5 border border-white/5 rounded px-2 py-1 flex items-center gap-2">
                        <span className="text-[8px] font-bold text-gray-500">#{t.step}</span>
                        <span className="text-[10px] font-black text-blue-400">{t.duration.toFixed(2)}s</span>
                    </div>
                ))
            )}
        </div>
      </div>

      {/* Footer */}
      <div className="flex flex-wrap items-center justify-between gap-4 pt-2 text-[9px] font-black uppercase tracking-widest text-black/30">
        <div className="flex items-center gap-2 bg-black/5 px-2 py-1">
          <span className="text-black/60">Domain</span>
          <span className="text-black">{state.task_domain}</span>
        </div>
        <div className="flex items-center gap-2 bg-black/5 px-2 py-1">
          <span className="text-black/60">Agents</span>
          <span className="text-black">{state.agents}</span>
        </div>
        <div className="flex items-center gap-2 bg-black/5 px-2 py-1">
          <span className="text-black/60">Failure</span>
          <span className="text-black">{state.failure_rate}</span>
        </div>
      </div>
    </div>
  );
}
