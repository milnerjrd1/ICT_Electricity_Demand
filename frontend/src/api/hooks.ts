// TanStack Query hooks for all API endpoints

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from './client';
import type {
  HealthResponse,
  RunStatusResponse,
  ScenarioDetail,
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

export function useScenario(id: string | null) {
  return useQuery({
    queryKey: ['scenario', id],
    queryFn: () => api.get<ScenarioDetail>(`/scenarios/${id}`),
    enabled: !!id,
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
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (params: ScenarioParams) =>
      api.post<{ run_id: string; status: string }>('/runs', params),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['run'] });
    },
  });
}

// ── Config ─────────────────────────────────────────────────────────────────

export function useAssumptions() {
  return useQuery({
    queryKey: ['assumptions'],
    queryFn: () => api.get<Record<string, unknown>>('/config/assumptions'),
    staleTime: 10 * 60_000,
  });
}
