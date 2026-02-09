/**
 * API 客户端
 */
import axios from 'axios';
import { API_BASE_URL } from '../utils/constants';
import type { SearchRequest, SearchResponse, UnifiedPost, UnifiedComment, AnalysisStats } from '../types';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.request.use((config) => config, (error) => Promise.reject(error));

// 响应直接返回 data；不再打印 X-Server-PID / 请求 URL
api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    console.error('API Error:', error);
    return Promise.reject(error);
  }
);

export const searchApi = {
  /**
   * 启动搜索
   */
  startSearch: async (request: SearchRequest): Promise<SearchResponse> => {
    return api.post('/api/search/start', request);
  },

  /**
   * 获取搜索状态
   */
  getSearchStatus: async (taskId: string): Promise<SearchResponse> => {
    return api.get(`/api/search/status/${taskId}`);
  },

  /**
   * 获取搜索结果
   */
  getSearchResults: async (taskId: string, platform?: string): Promise<UnifiedPost[]> => {
    const params = platform ? { platform } : {};
    return api.get(`/api/search/results/${taskId}`, { params });
  },

  /**
   * 停止搜索
   */
  stopSearch: async (taskId: string): Promise<void> => {
    return api.post(`/api/search/stop/${taskId}`);
  },

  /**
   * 获取帖子评论
   */
  getPostComments: async (platform: string, postId: string, taskId?: string): Promise<UnifiedComment[]> => {
    const params = taskId ? { task_id: taskId } : {};
    return api.get(`/api/search/comments/${platform}/${postId}`, { params });
  },
};

export const analysisApi = {
  /**
   * 获取统计数据
   */
  getStats: async (taskId: string): Promise<AnalysisStats> => {
    return api.post('/api/analysis/stats', null, { 
      params: { task_id: taskId },
      headers: { 'Content-Type': 'application/json' }
    });
  },

  /**
   * 获取平台分布
   */
  getDistribution: async (taskId: string): Promise<Record<string, number>> => {
    return api.post('/api/analysis/distribution', null, { 
      params: { task_id: taskId },
      headers: { 'Content-Type': 'application/json' }
    });
  },

  /**
   * 获取时间趋势
   */
  getTrends: async (taskId: string, interval: string = 'day'): Promise<Record<string, number>> => {
    return api.post('/api/analysis/trends', null, { 
      params: { task_id: taskId, interval },
      headers: { 'Content-Type': 'application/json' }
    });
  },

  /**
   * 获取热门作者
   */
  getTopAuthors: async (taskId: string, limit: number = 10): Promise<any[]> => {
    return api.post('/api/analysis/top-authors', null, { 
      params: { task_id: taskId, limit },
      headers: { 'Content-Type': 'application/json' }
    });
  },
};

export default api;
