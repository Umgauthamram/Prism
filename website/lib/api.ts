export type TaskDomain = "debug" | "market_research" | "etl";
export type AgentCount = 2 | 4 | 8;
export type FailureRate = 0 | 0.2 | 0.5;
export type AgentRole = "Planner" | "Researcher" | "Coder" | "Critic" | "Synthesizer";
export type NodeStatus = "pending" | "running" | "done" | "failed";

export interface TaskNode {
  status: NodeStatus;
  dependencies: string[];
}

export interface RewardBreakdown {
  progress_delta: number;
  atomic_health: number;
  coord_efficiency: number;
  hallucination_penalty: number;
  terminal_bonus: number;
}

export interface RewardPoint {
  step: number;
  total: number;
  breakdown: RewardBreakdown;
}

export interface TransferPoint {
  eval_episode: number;
  domain: TaskDomain;
  score: number;
}

export interface CurriculumStage {
  stage: number;
  failure_rate: number;
  agents: number;
  domains: TaskDomain[];
  threshold: number;
}

export interface Metrics {
  reward_curve: RewardPoint[];
  transfer_scores: TransferPoint[];
  current_stage: number;
  next_threshold: number;
  rolling_reward: number;
  total_episodes: number;
  curriculum_stages: CurriculumStage[];
}

export interface EpisodeState {
  task_graph: Record<string, TaskNode>;
  world_model: Record<string, any>;
  last_tool_output: any;
  checkpoint_id: string;
  agent_role: AgentRole;
  injected_failure_flag: boolean;
  episode_id: string;
  step: number;
  task_domain: TaskDomain;
  agents: AgentCount;
  failure_rate: FailureRate;
  terminated: boolean;
  feedback?: string;
  last_reward?: number;
  parent_episode_id?: string;
  parent_score?: number;
}

export interface ResetOptions {
  task_domain?: string;
  agents?: number;
  failure_rate?: number;
  seed?: number;
  parent_episode_id?: string;
  parent_score?: number;
}

export interface ProviderConfig {
  configured: boolean;
  models: string[];
}

export interface ModelsConfig {
  active_provider: string | null;
  active_model: string | null;
  providers: Record<string, { configured: boolean }>;
}

export interface TestConnectionResult {
  success: boolean;
  response: string;
  latency_ms: number;
}

export interface ModelComparisonData {
  models: Record<string, RewardPoint[]>;
}

export interface HistoryItem {
  id: string;
  model: string;
  provider: string;
  domain: TaskDomain;
  final_reward: number;
  steps: number;
  timestamp: number;
}

const getBaseUrl = () => {
  if (typeof window === 'undefined') return 'http://localhost:8000';
  
  // 1. Use explicit environment variable if provided
  if (process.env.NEXT_PUBLIC_ENV_URL && process.env.NEXT_PUBLIC_ENV_URL !== "") {
    return process.env.NEXT_PUBLIC_ENV_URL;
  }
  
  // 2. Local development fallback: if we are on localhost, backend is likely on 8000
  if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
    return 'http://localhost:8000';
  }
  
  // 3. Production/HF Spaces: use relative path
  return window.location.pathname.replace(/\/$/, '');
};

const API_BASE = getBaseUrl();
console.log(`[Prism API] Base URL initialized as: ${API_BASE}`);

export async function fetchHealth() {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) throw new Error("Backend offline");
  return res.json();
}

export async function fetchMetrics(): Promise<Metrics> {
  const res = await fetch(`${API_BASE}/metrics`);
  if (!res.ok) throw new Error("Failed to fetch metrics");
  return res.json();
}

export async function fetchState(): Promise<EpisodeState> {
  const res = await fetch(`${API_BASE}/state`);
  if (!res.ok) throw new Error("Failed to fetch state");
  return res.json();
}

export async function resetEpisode(options: ResetOptions) {
  const res = await fetch(`${API_BASE}/reset`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(options),
  });
  if (!res.ok) throw new Error("Failed to reset episode");
  return res.json();
}

export async function step(tool: string, args: any = {}, episodeId: string | null = null) {
  const res = await fetch(`${API_BASE}/step`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ 
      action: { tool, args }, 
      episode_id: episodeId 
    }),
  });
  if (!res.ok) throw new Error("Failed to execute step");
  return res.json();
}

// Model Evaluation Functions
export async function fetchModelsConfig(): Promise<ModelsConfig> {
  const res = await fetch(`${API_BASE}/models/config`);
  if (!res.ok) throw new Error("Failed to fetch models config");
  return res.json();
}

export async function fetchAvailableModels(): Promise<Record<string, { models: string[] }>> {
  const res = await fetch(`${API_BASE}/models/available`);
  if (!res.ok) throw new Error("Failed to fetch available models");
  return res.json();
}

export async function setModelConfig(provider: string, model: string, api_key: string, episodeId: string | null = null) {
  const res = await fetch(`${API_BASE}/models/config`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ provider, model, api_key, episode_id: episodeId }),
  });
  if (!res.ok) throw new Error("Failed to set model config");
  return res.json();
}

export async function testConnection(provider: string, model: string, api_key: string): Promise<TestConnectionResult> {
  const res = await fetch(`${API_BASE}/models/test`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ provider, model, api_key }),
  });
  if (!res.ok) throw new Error("Failed to test connection");
  return res.json();
}

export async function fetchModelComparison(): Promise<ModelComparisonData> {
  try {
    const res = await fetch(`${API_BASE}/models/comparison`);
    if (!res.ok) return { models: {} };
    return await res.json();
  } catch (err) {
    return { models: {} };
  }
}

export async function fetchHistory(): Promise<HistoryItem[]> {
  const res = await fetch(`${API_BASE}/history`);
  if (!res.ok) throw new Error("Failed to fetch history");
  return res.json();
}

export async function fetchHistoryDetail(eid: string): Promise<any> {
  const res = await fetch(`${API_BASE}/history/${eid}`);
  if (!res.ok) throw new Error("Failed to fetch history detail");
  return res.json();
}

// ── ICL Training Types & Functions ─────────────────────────

export interface ICLAnalysis {
  prev_score: number;
  improvement_plan: string;
  weaknesses: string[];
  ready_to_train: boolean;
  run_count: number;
}

export interface ICLHistoryEntry {
  prev_score: number;
  run_count: number;
  last_diagnostic: string;
}

export type ICLHistory = Record<string, ICLHistoryEntry>;

export async function analyseICL(model_key: string, domain: string): Promise<ICLAnalysis> {
  const res = await fetch(`${API_BASE}/icl/analyse`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ model_key, domain }),
  });
  if (!res.ok) throw new Error("Failed to analyse ICL");
  return res.json();
}

export async function startICLTraining(
  provider: string,
  model: string,
  domain: string,
  episode_id: string
): Promise<{ ready: boolean; injection_preview: string; last_diagnostic?: string; corrections_applied?: string[] }> {
  const res = await fetch(`${API_BASE}/icl/train`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ provider, model, domain, episode_id }),
  });
  if (!res.ok) throw new Error("Failed to start ICL training");
  return res.json();
}

export async function fetchICLHistory(): Promise<ICLHistory> {
  const res = await fetch(`${API_BASE}/icl/history`);
  if (!res.ok) return {};
  return res.json();
}

// ── Tournament ICL Types & Functions ───────────────────────

export interface ICLModelAnalysis {
  model_name: string;
  prev_score: number;
  improvement_plan: string;
  weaknesses: string[];
  ready_to_train: boolean;
  run_count: number;
  last_diagnostic: string;
}

export interface ICLAnalyseAllResult {
  domain: string;
  models: Record<string, ICLModelAnalysis>;
  total_models: number;
}

export interface ICLTrainedModel {
  model_name: string;
  injected: boolean;
  last_diagnostic: string;
  corrections_applied: string[];
  injection_length: number;
}

export interface ICLTrainAllResult {
  domain: string;
  trained_models: Record<string, ICLTrainedModel>;
  total_trained: number;
}

export async function analyseAllICL(domain: string): Promise<ICLAnalyseAllResult> {
  const res = await fetch(`${API_BASE}/icl/analyse-all`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ domain }),
  });
  if (!res.ok) throw new Error("Failed to analyse all models");
  return res.json();
}

export async function trainAllICL(
  domain: string,
  episode_ids: Record<string, string>
): Promise<ICLTrainAllResult> {
  const res = await fetch(`${API_BASE}/icl/train-all`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ domain, episode_ids }),
  });
  if (!res.ok) throw new Error("Failed to train all models");
  return res.json();
}
