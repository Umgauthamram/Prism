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
}

export interface ResetOptions {
  task_domain: TaskDomain;
  agents: AgentCount;
  failure_rate: FailureRate;
  seed?: number;
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

const BASE = typeof window !== 'undefined'
  ? (process.env.NEXT_PUBLIC_ENV_URL || 'http://localhost:8000')
  : 'http://localhost:8000';

const API_BASE = BASE;

export async function fetchHealth() {
  const res = await fetch(`${API_BASE}/health?t=${Date.now()}`, { cache: 'no-store' });
  if (!res.ok) throw new Error("Backend offline");
  const data = await res.json();
  if (data.status !== "ok" || data.project !== "prism") throw new Error("Invalid backend");
  return data;
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
