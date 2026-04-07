import axios from 'axios';

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
});

// 用例管理
export const casesApi = {
  list: (params?: { tags?: string; priority?: string }) =>
    api.get('/cases', { params }),
  get: (filePath: string) => api.get(`/cases/${filePath}`),
  create: (data: { filename: string; content: string }) =>
    api.post('/cases', data),
  update: (filePath: string, content: string) =>
    api.put(`/cases/${filePath}`, { content }),
  delete: (filePath: string) => api.delete(`/cases/${filePath}`),
  validate: (content: string) => api.post('/cases/validate', { content }),
};

// 环境管理
export const environmentsApi = {
  list: () => api.get('/environments'),
  get: (name: string) => api.get(`/environments/${name}`),
  create: (data: { name: string; base_url: string; variables?: Record<string, string> }) =>
    api.post('/environments', data),
  update: (name: string, data: { base_url?: string; variables?: Record<string, string> }) =>
    api.put(`/environments/${name}`, data),
  delete: (name: string) => api.delete(`/environments/${name}`),
};

// 执行管理
export const executionApi = {
  run: (data: { file: string; environment?: string; base_url?: string; variables?: Record<string, string> }) =>
    api.post('/execution/run', data),
  runSync: (data: { file: string; environment?: string; base_url?: string }) =>
    api.post('/execution/run-sync', data),
  batch: (data: { files?: string[]; directory?: string; environment?: string }) =>
    api.post('/execution/batch', data),
  status: (executionId: string) => api.get(`/execution/status/${executionId}`),
  history: (params?: { limit?: number; status?: string }) =>
    api.get('/execution/history', { params }),
};

// 报告管理
export const reportsApi = {
  list: () => api.get('/reports'),
  summary: () => api.get('/reports/summary'),
  generate: (executionId: string) => api.post(`/reports/generate/${executionId}`),
  delete: (fileName: string) => api.delete(`/reports/${fileName}`),
};

// Mock 管理
export const mockApi = {
  configs: () => api.get('/mock/configs'),
  getConfig: (fileName: string) => api.get(`/mock/configs/${fileName}`),
  dataTypes: () => api.get('/mock/data-factory/types'),
};

// 健康检查
export const healthApi = {
  check: () => api.get('/health'),
};

export default api;
