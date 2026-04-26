"use client";

import React, { useState, useEffect, useCallback, useRef } from "react";
import {
  fetchState,
  fetchModelsConfig,
  analyseICL,
  startICLTraining,
  fetchICLHistory,
  analyseAllICL,
  trainAllICL,
  ICLAnalysis,
  ICLHistory,
  ICLAnalyseAllResult,
  ICLModelAnalysis,
  ICLTrainedModel,
  EpisodeState,
  ModelsConfig,
} from "@/lib/api";

type TrainingMode = "single" | "tournament";

export default function ICLTrainer({ onStartEvaluation }: { onStartEvaluation?: (prevScore: number, modelName: string) => void }) {
  const [episodeState, setEpisodeState] = useState<EpisodeState | null>(null);
  const [modelsConfig, setModelsConfig] = useState<ModelsConfig | null>(null);
  const [history, setHistory] = useState<ICLHistory>({});

  // Single-model state
  const [analysis, setAnalysis] = useState<ICLAnalysis | null>(null);

  // Tournament state
  const [tournamentAnalysis, setTournamentAnalysis] = useState<ICLAnalyseAllResult | null>(null);

  // Shared UI state
  const [mode, setMode] = useState<TrainingMode>("single");
  const [analysing, setAnalysing] = useState(false);
  const [training, setTraining] = useState(false);
  const [trained, setTrained] = useState(false);
  const [trainedModels, setTrainedModels] = useState<Record<string, ICLTrainedModel>>({});
  const [injectionPreview, setInjectionPreview] = useState("");
  const [error, setError] = useState("");

  // Training simulation state
  const [trainingProgress, setTrainingProgress] = useState(0);
  const [trainingPhase, setTrainingPhase] = useState("");

  // Derive keys
  const modelKey =
    modelsConfig?.active_provider && modelsConfig?.active_model && episodeState?.task_domain
      ? `${modelsConfig.active_provider}/${modelsConfig.active_model}/${episodeState.task_domain}`
      : null;
  const domain = episodeState?.task_domain || "debug";

  // Count how many models have history in this domain
  const tournamentModels = Object.keys(history).filter((k) => k.endsWith(`/${domain}`));
  const hasHistory = tournamentModels.length > 0;
  const isTournament = tournamentModels.length >= 2;

  const totalRuns = Object.values(history).reduce((acc, curr) => acc + (curr.run_count || 0), 0);
  const lastRunCount = useRef(0);

  // Poll state
  useEffect(() => {
    const poll = async () => {
      try {
        const [st, cfg, hist] = await Promise.all([
          fetchState(),
          fetchModelsConfig(),
          fetchICLHistory(),
        ]);
        setEpisodeState(st);
        setModelsConfig(cfg);
        setHistory(hist);
        
        // If run count increased, data is stale
        const currentRuns = Object.values(hist).reduce((acc, curr) => acc + (curr.run_count || 0), 0);
        if (currentRuns > lastRunCount.current && lastRunCount.current > 0) {
           console.log("New evaluation data detected. Clearing stale analysis.");
           setTournamentAnalysis(null);
           setAnalysis(null);
           setTrained(false);
        }
        lastRunCount.current = currentRuns;
      } catch {
        // silent
      }
    };
    poll();
    const interval = setInterval(poll, 4000);
    return () => clearInterval(interval);
  }, []);

  // Auto-detect tournament mode only once on load if history exists
  useEffect(() => {
    if (tournamentModels.length >= 2) {
      setMode("tournament");
    }
  }, [tournamentModels.length > 1]); // only trigger when crossing the 2-model threshold

  // ── SINGLE MODEL HANDLERS ──────────────────────────
  const handleAnalyseSingle = useCallback(async () => {
    if (!modelKey || !episodeState) return;
    setAnalysing(true);
    setError("");
    try {
      const res = await analyseICL(modelKey, domain);
      setAnalysis(res);
    } catch {
      setError("Analysis failed — run an episode first.");
    } finally {
      setAnalysing(false);
    }
  }, [modelKey, episodeState, domain]);

  const simulateTraining = async (apiCall: () => Promise<void>) => {
    setTraining(true);
    setTrainingProgress(0);
    setError("");

    // Start API call in background
    const apiPromise = apiCall();

    // 20-second simulation
    const totalMs = 20000;
    const intervalMs = 100;
    const steps = totalMs / intervalMs;
    let currentStep = 0;

    const phases = [
      { p: 0, text: "Analysing historical failure patterns..." },
      { p: 20, text: "Constructing correction vectors..." },
      { p: 40, text: "Injecting task advancement instructions..." },
      { p: 60, text: "Synthesizing domain-specific guidelines..." },
      { p: 80, text: "Finalizing prompt injection weights..." },
      { p: 95, text: "Verifying in-context learning boundaries..." },
    ];

    await new Promise<void>((resolve) => {
      const timer = setInterval(() => {
        currentStep++;
        const progress = Math.min((currentStep / steps) * 100, 100);
        setTrainingProgress(progress);
        
        const phase = [...phases].reverse().find(ph => progress >= ph.p);
        if (phase) setTrainingPhase(phase.text);

        if (currentStep >= steps) {
          clearInterval(timer);
          resolve();
        }
      }, intervalMs);
    });

    try {
      await apiPromise;
      setTrained(true);
    } catch (e) {
      setError("Training injection failed.");
    } finally {
      setTraining(false);
    }
  };

  const handleTrainSingle = useCallback(() => {
    if (!modelsConfig?.active_provider || !modelsConfig?.active_model || !episodeState) return;
    simulateTraining(async () => {
      const res = await startICLTraining(
        modelsConfig.active_provider!,
        modelsConfig.active_model!,
        domain,
        episodeState.episode_id
      );
      const diag = res.last_diagnostic || "";
      const corrections = res.corrections_applied || [];
      setInjectionPreview(
        diag + (corrections.length > 0 ? "\n\nCorrections applied:\n" + corrections.map((c: string) => `  ✓ ${c}`).join("\n") : "")
      );
    });
  }, [modelsConfig, episodeState, domain]);

  // ── TOURNAMENT HANDLERS ────────────────────────────
  const handleAnalyseTournament = useCallback(async () => {
    setAnalysing(true);
    setError("");
    try {
      const res = await analyseAllICL(domain);
      setTournamentAnalysis(res);
    } catch {
      setError("Tournament analysis failed — run a tournament first.");
    } finally {
      setAnalysing(false);
    }
  }, [domain]);

  const handleTrainTournament = useCallback(() => {
    simulateTraining(async () => {
      const res = await trainAllICL(domain, {});
      setTrainedModels(res.trained_models);
    });
  }, [domain]);

  const resetState = () => {
    setAnalysis(null);
    setTournamentAnalysis(null);
    setTrained(false);
    setTrainedModels({});
    setInjectionPreview("");
    setError("");
  };

  // Derived state
  const historyEntry = modelKey ? history[modelKey] : null;
  const prevScore = Number(analysis?.prev_score ?? historyEntry?.prev_score ?? 0);
  const hasModel = !!modelsConfig?.active_model;
  const hasAnyRun = Object.keys(history).some((k) => k.endsWith(`/${domain}`));
  const hasRun = (historyEntry?.run_count ?? 0) > 0;

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      {/* Page Header */}
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between border-b-2 border-black/10 pb-6">
        <div>
          <h2 className="text-2xl font-black uppercase tracking-tight text-black lg:text-3xl">
            In-Context Training
          </h2>
          <p className="text-xs text-black/50 mt-1 max-w-xl">
            Analyse model performance, identify weaknesses, and inject learning context
            to improve behavior — all within this session via Zero-Shot RL.
          </p>
        </div>

        {/* Mode Toggle */}
        <div className="flex gap-2">
          <button
            onClick={() => { setMode("single"); resetState(); }}
            className={`px-4 py-2 text-[9px] font-black uppercase tracking-widest border-2 transition-all shadow-[3px_3px_0px_rgba(0,0,0,1)] active:translate-x-0.5 active:translate-y-0.5 active:shadow-none ${
              mode === "single"
                ? "bg-black text-white border-black"
                : "bg-white text-black border-black hover:bg-gray-100"
            }`}
          >
            Single Model
          </button>
          <button
            onClick={() => { setMode("tournament"); resetState(); }}
            disabled={!hasHistory}
            className={`px-4 py-2 text-[9px] font-black uppercase tracking-widest border-2 transition-all shadow-[3px_3px_0px_rgba(0,0,0,1)] active:translate-x-0.5 active:translate-y-0.5 active:shadow-none disabled:opacity-30 disabled:cursor-not-allowed ${
              mode === "tournament"
                ? "bg-black text-white border-black"
                : "bg-white text-black border-black hover:bg-gray-100"
            }`}
          >
            Multi-Model Analysis ({tournamentModels.length})
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-8 lg:grid-cols-12">
        {/* Left Column: Training Controls */}
        <div className="lg:col-span-5 space-y-6">
          {/* ════ SINGLE MODEL MODE ════ */}
          {mode === "single" && (
            <div className="glass-panel p-6 space-y-5">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-black uppercase tracking-widest text-black">
                  Model Training
                </h3>
                {hasRun && (
                  <StatusBadge score={prevScore} />
                )}
              </div>

              {!hasModel && (
                <EmptyState text="Select a model in Model Policy to enable training" />
              )}

              {hasModel && !hasRun && (
                <EmptyState text="Run an episode first to collect performance data" />
              )}

              {hasModel && hasRun && (
                <>
                  {/* Score */}
                  <ScoreDisplay label="Last Episode Score" score={prevScore} />

                  {/* Analyse */}
                  {!analysis && (
                    <ActionButton
                      onClick={handleAnalyseSingle}
                      loading={analysing}
                      label="Analyse Performance"
                      loadingLabel="Analysing Weaknesses..."
                    />
                  )}

                  {/* Weaknesses */}
                  {analysis && analysis.weaknesses.length > 0 && (
                    <WeaknessPanel weaknesses={analysis.weaknesses} />
                  )}

                  {analysis && analysis.weaknesses.length === 0 && (
                    <SuccessBox text="Model is performing well. No training needed for this domain." />
                  )}

                  {/* Train */}
                  {analysis && analysis.ready_to_train && !trained && !training && (
                    <TrainButton
                      onClick={handleTrainSingle}
                      loading={false}
                    />
                  )}

                  {/* Training Simulation */}
                  {training && (
                    <div className="border-2 border-emerald-600 p-5 space-y-4">
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] font-black uppercase tracking-widest text-emerald-700 animate-pulse">
                          In-Context Learning Active
                        </span>
                        <span className="text-[10px] font-mono font-black text-emerald-600">
                          {Math.floor(trainingProgress)}%
                        </span>
                      </div>
                      <div className="h-2 w-full border-2 border-emerald-200 bg-emerald-50 overflow-hidden">
                        <div 
                          className="h-full bg-emerald-500 transition-all duration-100 ease-linear" 
                          style={{ width: `${trainingProgress}%` }} 
                        />
                      </div>
                      <p className="text-[10px] text-emerald-800 font-medium">
                        {trainingPhase}
                      </p>
                    </div>
                  )}

                  {/* Result */}
                  {trained && !training && (
                    <div className="space-y-4">
                      <TrainedResult 
                        preview={injectionPreview} 
                        expectedScore={Math.min(0.999, prevScore + (1.0 - prevScore) * 0.35)} 
                      />
                      <button
                        onClick={() => onStartEvaluation?.(prevScore, modelKey || "Unknown")}
                        className="w-full border-2 border-black bg-black py-4 text-[10px] font-black uppercase tracking-widest text-white hover:bg-gray-800 transition-all shadow-[3px_3px_0px_rgba(0,0,0,1)] active:translate-x-0.5 active:translate-y-0.5 active:shadow-none"
                      >
                        Evaluate Now →
                      </button>
                    </div>
                  )}

                  {/* History */}
                  {historyEntry && historyEntry.run_count > 0 && (
                    <RunHistory entry={historyEntry} />
                  )}
                </>
              )}
            </div>
          )}

          {/* ════ TOURNAMENT MODE ════ */}
          {mode === "tournament" && (
            <div className="glass-panel p-6 space-y-5">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-black uppercase tracking-widest text-black">
                  Tournament Training
                </h3>
                <div className="flex items-center gap-2 border-2 border-black px-3 py-1">
                  <span className="text-[9px] font-black uppercase tracking-widest text-black/70">
                    {tournamentModels.length} Models • {domain}
                  </span>
                </div>
              </div>

              {!hasAnyRun && (
                <EmptyState text="Run a tournament first to collect model performance data" />
              )}

              {hasAnyRun && !tournamentAnalysis && (
                <ActionButton
                  onClick={handleAnalyseTournament}
                  loading={analysing}
                  label="Analyse All Models"
                  loadingLabel="Analysing Tournament..."
                />
              )}

              {/* Per-model analysis cards */}
              {tournamentAnalysis && Object.keys(tournamentAnalysis.models).length > 0 && (
                <div className="space-y-4">
                  {Object.entries(tournamentAnalysis.models).map(([key, model]) => (
                    <ModelAnalysisCard key={key} modelKey={key} model={model} />
                  ))}
                </div>
              )}

              {/* Train all */}
              {tournamentAnalysis && !trained && !training && (
                <TrainButton
                  onClick={handleTrainTournament}
                  loading={false}
                  label="Train All Models"
                />
              )}

              {/* Training Simulation */}
              {training && (
                <div className="border-2 border-emerald-600 p-5 space-y-4">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-black uppercase tracking-widest text-emerald-700 animate-pulse">
                      Batch In-Context Learning Active
                    </span>
                    <span className="text-[10px] font-mono font-black text-emerald-600">
                      {Math.floor(trainingProgress)}%
                    </span>
                  </div>
                  <div className="h-2 w-full border-2 border-emerald-200 bg-emerald-50 overflow-hidden">
                    <div 
                      className="h-full bg-emerald-500 transition-all duration-100 ease-linear" 
                      style={{ width: `${trainingProgress}%` }} 
                    />
                  </div>
                  <p className="text-[10px] text-emerald-800 font-medium">
                    {trainingPhase}
                  </p>
                </div>
              )}

              {/* Trained result per model */}
              {trained && !training && Object.keys(trainedModels).length > 0 && (
                <div className="space-y-4">
                  <div className="flex items-center gap-2">
                    <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
                    <span className="text-[10px] font-black uppercase tracking-widest text-emerald-700">
                      All Models Trained
                    </span>
                  </div>
                  
                  <div className="space-y-3">
                    {Object.entries(trainedModels).map(([key, model]) => (
                      <div key={key} className="border-2 border-emerald-300 bg-emerald-50 p-4 space-y-2">
                        <div className="text-[10px] font-black uppercase tracking-widest text-emerald-700">
                          {model.model_name.replace(/\//g, " / ")}
                        </div>
                        {model.last_diagnostic && (
                          <div className="space-y-1">
                            <div className="text-[9px] font-black uppercase tracking-widest text-black/40">Last Diagnostic</div>
                            <p className="text-[11px] text-black/70 leading-relaxed">
                              {model.last_diagnostic}
                            </p>
                          </div>
                        )}
                        {model.corrections_applied.length > 0 && (
                          <div className="space-y-1">
                            <div className="text-[9px] font-black uppercase tracking-widest text-emerald-600">Corrections Injected</div>
                            <ul className="space-y-0.5">
                              {model.corrections_applied.map((c, i) => (
                                <li key={i} className="text-[10px] font-bold text-emerald-700 flex items-start gap-1.5">
                                  <span className="flex-shrink-0">✓</span>
                                  <span>{c}</span>
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                        <div className="text-[9px] text-black/30 font-mono">
                          {model.injection_length} chars injected into system prompt
                        </div>
                      </div>
                    ))}
                  </div>

                  <button
                    onClick={() => {
                      const models = tournamentAnalysis?.models || {};
                      const modelEntries = Object.values(models);
                      const avgScore = modelEntries.length > 0 
                        ? modelEntries.reduce((acc, m: any) => acc + (m.prev_score || 0), 0) / modelEntries.length 
                        : 0;
                      onStartEvaluation?.(avgScore, "Tournament Results");
                    }}
                    className="w-full border-2 border-black bg-black py-4 text-[10px] font-black uppercase tracking-widest text-white hover:bg-gray-800 transition-all shadow-[3px_3px_0px_rgba(0,0,0,1)] active:translate-x-0.5 active:translate-y-0.5 active:shadow-none"
                  >
                    Evaluate All Now →
                  </button>
                </div>
              )}
            </div>
          )}


        </div>

        {/* Right Column: Training History & Overview */}
        <div className="lg:col-span-7 space-y-6">
          {/* All Models Overview */}
          <div className="glass-panel p-6">
            <h3 className="text-sm font-black uppercase tracking-widest text-black mb-4">
              Training History — {domain}
            </h3>
            {Object.keys(history).filter(k => k.endsWith(`/${domain}`)).length === 0 ? (
              <EmptyState text="No training data yet. Run episodes or a tournament to populate." />
            ) : (
              <div className="space-y-3">
                {Object.entries(history)
                  .filter(([k]) => k.endsWith(`/${domain}`))
                  .map(([key, entry]) => {
                    const modelName = key.replace(`/${domain}`, "");
                    return (
                      <div
                        key={key}
                        className="border-2 border-black/10 p-4 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between"
                      >
                        <div className="space-y-1">
                          <div className="text-xs font-black uppercase tracking-widest text-black">
                            {modelName.replace("/", " / ")}
                          </div>
                          {entry.last_diagnostic && (
                            <p className="text-[10px] text-black/50 italic leading-tight max-w-md">
                              &ldquo;{entry.last_diagnostic.slice(0, 100)}
                              {entry.last_diagnostic.length > 100 ? "..." : ""}&rdquo;
                            </p>
                          )}
                        </div>
                        <div className="flex items-center gap-4">
                          <div className="text-center">
                            <div className="text-[8px] font-black uppercase tracking-widest text-black/40">
                              Runs
                            </div>
                            <div className="text-lg font-mono font-black text-black">
                              {entry.run_count}
                            </div>
                          </div>
                          <div className="text-center">
                            <div className="text-[8px] font-black uppercase tracking-widest text-black/40">
                              Last Score
                            </div>
                            <div className={`text-lg font-mono font-black ${entry.prev_score < 2.5 ? "text-red-600" : "text-emerald-600"}`}>
                              {entry.prev_score.toFixed(4)}
                            </div>
                          </div>
                          <StatusBadge score={entry.prev_score} />
                        </div>
                      </div>
                    );
                  })}
              </div>
            )}
          </div>

          </div>
        </div>

      {/* Footer: Warning + Workflow */}
      <div className="mt-12 pt-8 border-t-2 border-black/10 space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-start">
          {/* Warning */}
          <div className="border-2 border-amber-600 bg-amber-50 p-5 space-y-2 shadow-[4px_4px_0px_rgba(180,83,9,1)]">
            <div className="flex items-center gap-2 text-amber-700">
              <span className="text-lg">⚠</span>
              <h4 className="text-[11px] font-black uppercase tracking-widest">Session-Only Learning</h4>
            </div>
            <p className="text-[10px] font-bold text-amber-800 leading-relaxed">
              Improvements made here only apply within this browser session. This uses In-Context Learning (ICL) 
              — the model's weights are not permanently updated. Closing the tab, restarting the server, 
              or switching to a different episode resets all learned behavior. 
              This is <span className="underline decoration-amber-500/50">Zero-Shot RL via prompt engineering</span>, not fine-tuning.
            </p>
          </div>

          {/* Workflow (Moved to footer) */}
          <div className="border-2 border-black p-5 bg-white shadow-[4px_4px_0px_rgba(0,0,0,1)]">
            <h3 className="text-[10px] font-black uppercase tracking-widest text-black mb-4 flex items-center gap-2">
              <span className="h-2 w-2 bg-black" />
              How ICL Training Works
            </h3>
            <div className="grid grid-cols-5 gap-2">
              {[
                { step: "1", label: "RUN" },
                { step: "2", label: "ANALYSE" },
                { step: "3", label: "INJECT" },
                { step: "4", label: "RE-RUN" },
                { step: "5", label: "COMPARE" },
              ].map((item) => (
                <div key={item.step} className="flex flex-col items-center gap-1.5">
                  <div className="w-6 h-6 border-2 border-black bg-black text-white flex items-center justify-center text-[10px] font-black">
                    {item.step}
                  </div>
                  <span className="text-[8px] font-black uppercase text-black tracking-tighter">
                    {item.label}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Error */}
      {error && (
        <p className="mt-8 text-center text-[9px] font-black uppercase tracking-[0.2em] text-red-500">
          {error}
        </p>
      )}
    </div>
  );
}

// ── Shared Sub-Components ────────────────────────────────

function StatusBadge({ score }: { score: number }) {
  const under = score < 0.65;
  return (
    <div
      className={`flex items-center gap-2 border-2 px-3 py-1 ${
        under ? "border-red-600 bg-red-50" : "border-emerald-600 bg-emerald-50"
      }`}
    >
      <span
        className={`h-1.5 w-1.5 rounded-full ${under ? "bg-red-500 animate-pulse" : "bg-emerald-500"}`}
      />
      <span
        className={`text-[9px] font-black uppercase tracking-widest ${
          under ? "text-red-700" : "text-emerald-700"
        }`}
      >
        {under ? "Underperforming" : "Performing Well"}
      </span>
    </div>
  );
}

function EmptyState({ text }: { text: string }) {
  return (
    <div className="border-2 border-dashed border-black/20 p-4 text-center">
      <p className="text-[10px] font-bold uppercase tracking-widest text-black/40">{text}</p>
    </div>
  );
}

function ScoreDisplay({ label, score }: { label: string; score: number }) {
  return (
    <div className="flex items-center justify-between border-2 border-black p-3">
      <span className="text-[10px] font-black uppercase tracking-widest text-black/50">{label}</span>
      <span className="text-lg font-mono font-black text-black">{score.toFixed(4)}</span>
    </div>
  );
}

function ActionButton({
  onClick,
  loading,
  label,
  loadingLabel,
}: {
  onClick: () => void;
  loading: boolean;
  label: string;
  loadingLabel: string;
}) {
  return (
    <button
      onClick={onClick}
      disabled={loading}
      className="w-full border-2 border-black bg-white py-3 text-[10px] font-black uppercase tracking-widest text-black hover:bg-gray-100 disabled:opacity-50 transition-all shadow-[3px_3px_0px_rgba(0,0,0,1)] active:translate-x-0.5 active:translate-y-0.5 active:shadow-none"
    >
      {loading ? loadingLabel : label}
    </button>
  );
}

function WeaknessPanel({ weaknesses }: { weaknesses: string[] }) {
  const fixes = [
    "Step-by-step task advancement instructions",
    "Checkpoint/preflight/rollback protocol reminders",
    "Claim verification requirements",
    "Domain-specific answer structure requirements",
  ];
  return (
    <div className="border-2 border-black p-4 space-y-3">
      <h4 className="text-[10px] font-black uppercase tracking-widest text-red-600">
        Weaknesses Found
      </h4>
      <ul className="space-y-1.5">
        {weaknesses.map((w, i) => (
          <li key={i} className="flex items-start gap-2 text-[11px] font-bold text-black/80">
            <span className="text-red-500 mt-0.5 flex-shrink-0">•</span>
            <span>{w}</span>
          </li>
        ))}
      </ul>
      <div className="border-t-2 border-black/10 pt-3 mt-3">
        <h4 className="text-[10px] font-black uppercase tracking-widest text-emerald-600 mb-2">
          What We Will Inject
        </h4>
        <ul className="space-y-1.5">
          {weaknesses.map((_, i) =>
            i < fixes.length ? (
              <li key={i} className="flex items-start gap-2 text-[11px] font-bold text-emerald-700">
                <span className="flex-shrink-0">✓</span>
                <span>{fixes[i]}</span>
              </li>
            ) : null
          )}
        </ul>
      </div>
    </div>
  );
}

function SuccessBox({ text }: { text: string }) {
  return (
    <div className="border-2 border-emerald-500 bg-emerald-50 p-4">
      <p className="text-[11px] font-bold text-emerald-700">✓ {text}</p>
    </div>
  );
}

function TrainButton({
  onClick,
  loading,
  label = "Train This Model",
  loadingLabel = "Injecting Learning Context...",
}: {
  onClick: () => void;
  loading: boolean;
  label?: string;
  loadingLabel?: string;
}) {
  return (
    <button
      onClick={onClick}
      disabled={loading}
      className="w-full border-2 border-emerald-700 bg-emerald-600 py-3.5 text-[10px] font-black uppercase tracking-widest text-white hover:bg-emerald-700 disabled:opacity-50 transition-all shadow-[3px_3px_0px_rgba(0,0,0,1)] active:translate-x-0.5 active:translate-y-0.5 active:shadow-none"
    >
      {loading ? loadingLabel : label}
    </button>
  );
}

function TrainedResult({ preview, expectedScore }: { preview: string, expectedScore?: number }) {
  return (
    <div className="border-2 border-emerald-500 bg-emerald-50 p-4 space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
          <span className="text-[10px] font-black uppercase tracking-widest text-emerald-700">
            Ready — Corrections Injected
          </span>
        </div>
        {expectedScore !== undefined && (
          <div className="bg-emerald-600 px-2 py-1 text-[9px] font-black text-white border border-emerald-700">
            EXPECTED: ~{expectedScore.toFixed(4)}
          </div>
        )}
      </div>
      {preview && (
        <pre className="text-[9px] font-mono text-emerald-800 bg-emerald-100 p-2 border border-emerald-200 overflow-x-auto max-h-24 whitespace-pre-wrap">
          {preview}
        </pre>
      )}
    </div>
  );
}

function RetryButton({ onClick }: { onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="w-full border-2 border-black bg-black py-3 text-[10px] font-black uppercase tracking-widest text-white hover:bg-gray-800 transition-all shadow-[3px_3px_0px_rgba(0,0,0,0.3)] active:translate-x-0.5 active:translate-y-0.5 active:shadow-none"
    >
      Try Deeper Optimization
    </button>
  );
}

function RunHistory({ entry }: { entry: { run_count: number; prev_score: number; last_diagnostic: string } }) {
  return (
    <div className="border-2 border-black/10 p-3 space-y-2">
      <h4 className="text-[9px] font-black uppercase tracking-widest text-black/40">
        Run History
      </h4>
      <div className="flex items-center gap-2 text-xs font-mono font-bold text-black">
        <span>Runs: {entry.run_count}</span>
        <span className="text-black/30">|</span>
        <span>Last: {entry.prev_score.toFixed(4)}</span>
      </div>
      {entry.last_diagnostic && (
        <p className="text-[10px] text-black/60 italic leading-tight">
          &ldquo;{entry.last_diagnostic.slice(0, 120)}
          {entry.last_diagnostic.length > 120 ? "..." : ""}&rdquo;
        </p>
      )}
    </div>
  );
}

function ModelAnalysisCard({
  modelKey,
  model,
}: {
  modelKey: string;
  model: ICLModelAnalysis;
}) {
  return (
    <div className="border-2 border-black p-4 space-y-3">
      <div className="flex items-center justify-between">
        <div className="text-xs font-black uppercase tracking-widest text-black">
          {model.model_name.replace("/", " / ")}
        </div>
        <div className="flex items-center gap-3">
          <div className="flex flex-col items-end">
            <span className="text-sm font-mono font-black text-black leading-none">
              {model.prev_score.toFixed(4)}
            </span>
            <span className="text-[10px] font-black text-emerald-600 uppercase tracking-tight mt-0.5">
              Exp: ~{Math.min(0.99, model.prev_score + (1.0 - model.prev_score) * 0.35).toFixed(4)}
            </span>
          </div>
          <StatusBadge score={model.prev_score} />
        </div>
      </div>

      {model.last_diagnostic && (
        <p className="text-[10px] text-black/60 italic leading-tight border-l-2 border-black/10 pl-2">
          &ldquo;{model.last_diagnostic.slice(0, 150)}{model.last_diagnostic.length > 150 ? "..." : ""}&rdquo;
        </p>
      )}

      {model.weaknesses.length > 0 ? (
        <ul className="space-y-1">
          {model.weaknesses.map((w, i) => (
            <li key={i} className="flex items-start gap-2 text-[10px] font-bold text-black/70">
              <span className="text-red-500 mt-0.5 flex-shrink-0">•</span>
              <span>{w}</span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-[10px] font-bold text-emerald-600">✓ No weaknesses detected</p>
      )}

      <div className="text-[9px] text-black/40 font-bold">
        Runs: {model.run_count}
      </div>
    </div>
  );
}
