import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import type { LlmLeadsResult } from '../types';

export interface LlmAnalysisRecord {
  id: string;
  createdAt: string;
  name: string;
  model: string;
  postsCount: number;
  result: LlmLeadsResult;
  /** 分析场景 id，用于结果页展示对应供给方/需求方文案 */
  scene?: string;
  sceneName?: string;
  sellerLabel?: string;
  buyerLabel?: string;
}

interface LlmAnalysisState {
  records: LlmAnalysisRecord[];
  addRecord: (record: Omit<LlmAnalysisRecord, 'id' | 'createdAt'>) => void;
  deleteRecord: (id: string) => void;
  deleteRecords: (ids: string[]) => void;
  getRecord: (id: string) => LlmAnalysisRecord | undefined;
  clearAll: () => void;
}

export const useLlmAnalysisStore = create<LlmAnalysisState>()(
  persist(
    (set, get) => ({
      records: [],
      addRecord: (record) => {
        const id = `llm-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
        const createdAt = new Date().toISOString();
        set((state) => ({
          records: [{ ...record, id, createdAt }, ...state.records],
        }));
      },
      deleteRecord: (id) => {
        set((state) => ({
          records: state.records.filter((r) => r.id !== id),
        }));
      },
      deleteRecords: (ids) => {
        const idSet = new Set(ids);
        set((state) => ({
          records: state.records.filter((r) => !idSet.has(r.id)),
        }));
      },
      getRecord: (id) => get().records.find((r) => r.id === id),
      clearAll: () => set({ records: [] }),
    }),
    {
      name: 'getsomehints-llm-analysis',
      storage: createJSONStorage(() => localStorage),
    }
  )
);
