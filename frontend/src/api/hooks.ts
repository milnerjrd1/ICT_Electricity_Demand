// TanStack Query hooks for all API endpoints

import { useMutation, useQuery } from '@tanstack/react-query';
import { api } from './client';
import type {
  HealthResponse,
  RunStatusResponse,
  ScenarioMeta,
  ScenarioParams,
} from '../types/schema';

// ── Health ─────────────────────────────────────────────────────────────────

export function useHealth() {
  return useQuery({
    queryKey: ['health'],
    queryFn: () => api.get<HealthResponse>('/health'),
    refetchInterval: 30_000,
  });
}

// ── Scenarios ──────────────────────────────────────────────────────────────

export function useScenarios() {
  return useQuery({
    queryKey: ['scenarios'],
    queryFn: () => api.get<ScenarioMeta[]>('/scenarios'),
    staleTime: 5 * 60_000,
  });
}

// ── Runs ───────────────────────────────────────────────────────────────────

export function useRunStatus(runId: string | null) {
  return useQuery({
    queryKey: ['run', runId],
    queryFn: () => api.get<RunStatusResponse>(`/runs/${runId}`),
    enabled: !!runId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === 'done' || status === 'failed') return false;
      return 500; // poll every 500ms while running
    },
  });
}

export function useCreateRun() {
  return useMutation({
    mutationFn: (params: ScenarioParams) =>
      api.post<{ run_id: string; status: string }>('/runs', params),
  });
}

