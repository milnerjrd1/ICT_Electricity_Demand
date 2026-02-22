// Zustand store — UI state only (server data lives in TanStack Query)

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { RunResult, ScenarioParams } from '../types/schema';

export interface SavedScenario {
  id: string;
  label: string;
  color: string;
  params: ScenarioParams;
  result: RunResult | null;
  savedAt: string;
}

const SCENARIO_COLORS = ['#00D4FF', '#10B981', '#F59E0B', '#EF4444'];

interface ScenarioStore {
  // Active scenario being built/edited
  activeScenarioId: string;
  activeParams: ScenarioParams;
  isStale: boolean;
  currentRunId: string | null;

  // Saved scenarios (up to 4)
  savedScenarios: SavedScenario[];

  // Active page
  activePage: string;

  // Actions
  setActiveScenarioId: (id: string) => void;
  updateParam: <K extends keyof ScenarioParams>(key: K, value: ScenarioParams[K]) => void;
  setParams: (params: ScenarioParams) => void;
  markStale: () => void;
  setCurrentRunId: (id: string | null) => void;
  saveScenario: (label: string, params: ScenarioParams, result: RunResult) => void;
  removeScenario: (id: string) => void;
  updateScenarioResult: (id: string, result: RunResult) => void;
  setActivePage: (page: string) => void;
}

export const useScenarioStore = create<ScenarioStore>()(
  persist(
    (set, get) => ({
      activeScenarioId: 'ai_base',
      activeParams: {
        scenario_id: 'ai_base',
        pue_improvement_rate: 0.02,
        utilisation_multiplier: 1.0,
        ai_growth_rate: 0.20,
        hyperscale_share: 0.45,
        avg_lifespan_multiplier: 1.0,
        device_shipment_growth: 0.01,
        power_efficiency_factor: 1.0,
        seed: 42,
      },
      isStale: false,
      currentRunId: null,
      savedScenarios: [],
      activePage: 'mission-control',

      setActiveScenarioId: (id) =>
        set({ activeScenarioId: id, activeParams: { ...get().activeParams, scenario_id: id }, isStale: true }),

      updateParam: (key, value) =>
        set((s) => ({
          activeParams: { ...s.activeParams, [key]: value },
          isStale: true,
        })),

      setParams: (params) => set({ activeParams: params, isStale: true }),

      markStale: () => set({ isStale: true }),

      setCurrentRunId: (id) => set({ currentRunId: id, isStale: false }),

      saveScenario: (label, params, result) => {
        const existing = get().savedScenarios;
        if (existing.length >= 4) return; // max 4
        const colorIndex = existing.length % SCENARIO_COLORS.length;
        const saved: SavedScenario = {
          id: crypto.randomUUID(),
          label,
          color: SCENARIO_COLORS[colorIndex],
          params,
          result,
          savedAt: new Date().toISOString(),
        };
        set({ savedScenarios: [...existing, saved] });
      },

      removeScenario: (id) =>
        set((s) => ({ savedScenarios: s.savedScenarios.filter((sc) => sc.id !== id) })),

      updateScenarioResult: (id, result) =>
        set((s) => ({
          savedScenarios: s.savedScenarios.map((sc) =>
            sc.id === id ? { ...sc, result } : sc,
          ),
        })),

      setActivePage: (page) => set({ activePage: page }),
    }),
    {
      name: 'ict-scenario-store',
      partialize: (s) => ({
        activeScenarioId: s.activeScenarioId,
        activeParams: s.activeParams,
        savedScenarios: s.savedScenarios,
      }),
    },
  ),
);
