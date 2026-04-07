import { useEffect, useState } from 'react';
import {
  Settings,
  Plus,
  Trash2,
  Eye,
  X,
  Save,
  Globe,
} from 'lucide-react';
import { environmentsApi } from '../api/client';

interface EnvItem {
  file: string;
  name: string;
  base_url: string;
  variables_count: number;
}

interface EnvDetail {
  file: string;
  content: string;
  parsed?: {
    name: string;
    base_url: string;
    variables: Record<string, string>;
    headers: Record<string, string>;
  };
}

export default function Environments() {
  const [envs, setEnvs] = useState<EnvItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [detail, setDetail] = useState<EnvDetail | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [newEnv, setNewEnv] = useState({ name: '', base_url: '' });
  const [creating, setCreating] = useState(false);

  const loadEnvs = () => {
    setLoading(true);
    environmentsApi.list().then((res) => {
      setEnvs(res.data.environments || []);
      setLoading(false);
    }).catch(() => setLoading(false));
  };

  useEffect(() => { loadEnvs(); }, []);

  const viewEnv = (name: string) => {
    environmentsApi.get(name).then((res) => setDetail(res.data));
  };

  const deleteEnv = (name: string) => {
    if (!confirm(`确定删除环境 ${name}？`)) return;
    environmentsApi.delete(name).then(() => {
      loadEnvs();
      if (detail?.parsed?.name === name) setDetail(null);
    });
  };

  const createEnv = () => {
    if (!newEnv.name || !newEnv.base_url) return;
    setCreating(true);
    environmentsApi.create(newEnv).then(() => {
      setShowCreate(false);
      setNewEnv({ name: '', base_url: '' });
      setCreating(false);
      loadEnvs();
    }).catch(() => setCreating(false));
  };

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">环境配置</h1>
          <p className="text-gray-500 mt-1">管理测试环境（开发、测试、生产等）</p>
        </div>
        <button
          onClick={() => setShowCreate(!showCreate)}
          className="px-4 py-2.5 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 transition-colors flex items-center gap-2"
        >
          <Plus className="w-4 h-4" />
          新建环境
        </button>
      </div>

      {/* 创建表单 */}
      {showCreate && (
        <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
          <h3 className="text-sm font-semibold text-gray-700 mb-4">创建新环境</h3>
          <div className="flex items-end gap-4">
            <div className="flex-1">
              <label className="block text-xs text-gray-500 mb-1">环境名称</label>
              <input
                type="text"
                value={newEnv.name}
                onChange={(e) => setNewEnv({ ...newEnv, name: e.target.value })}
                placeholder="例如: staging"
                className="w-full px-3 py-2.5 rounded-lg border border-gray-200 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>
            <div className="flex-1">
              <label className="block text-xs text-gray-500 mb-1">Base URL</label>
              <input
                type="text"
                value={newEnv.base_url}
                onChange={(e) => setNewEnv({ ...newEnv, base_url: e.target.value })}
                placeholder="例如: https://api.staging.example.com"
                className="w-full px-3 py-2.5 rounded-lg border border-gray-200 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>
            <button
              onClick={createEnv}
              disabled={creating || !newEnv.name || !newEnv.base_url}
              className="px-5 py-2.5 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 transition-colors flex items-center gap-2"
            >
              <Save className="w-4 h-4" />
              创建
            </button>
            <button
              onClick={() => setShowCreate(false)}
              className="px-4 py-2.5 bg-gray-100 text-gray-600 rounded-lg text-sm hover:bg-gray-200 transition-colors"
            >
              取消
            </button>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* 环境列表 */}
        <div className="lg:col-span-1">
          {loading ? (
            <div className="flex justify-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600" />
            </div>
          ) : envs.length === 0 ? (
            <div className="text-center py-12 text-gray-400">
              <Settings className="w-12 h-12 mx-auto mb-3 opacity-50" />
              <p>暂无环境配置</p>
            </div>
          ) : (
            <div className="space-y-3">
              {envs.map((env) => (
                <div
                  key={env.name}
                  className={`bg-white rounded-xl border p-4 cursor-pointer transition-all hover:shadow-md ${
                    detail?.parsed?.name === env.name
                      ? 'border-indigo-300 ring-2 ring-indigo-100'
                      : 'border-gray-200'
                  }`}
                  onClick={() => viewEnv(env.name)}
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <Globe className="w-4 h-4 text-indigo-500" />
                      <span className="font-medium text-gray-900 text-sm">{env.name}</span>
                    </div>
                    <button
                      onClick={(e) => { e.stopPropagation(); deleteEnv(env.name); }}
                      className="p-1 rounded hover:bg-red-50 text-gray-400 hover:text-red-500"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                  <div className="text-xs text-gray-400 truncate">{env.base_url}</div>
                  <div className="text-xs text-gray-400 mt-1">{env.variables_count} 个变量</div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* 环境详情 */}
        <div className="lg:col-span-2">
          {detail ? (
            <div className="bg-white rounded-xl border border-gray-200">
              <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
                <h3 className="font-semibold text-gray-900">{detail.parsed?.name || detail.file}</h3>
                <button onClick={() => setDetail(null)} className="p-1 hover:bg-gray-100 rounded-lg">
                  <X className="w-4 h-4 text-gray-400" />
                </button>
              </div>
              {detail.parsed && (
                <div className="p-6 space-y-4">
                  <div>
                    <div className="text-xs text-gray-500 mb-1">Base URL</div>
                    <div className="text-sm font-mono bg-gray-50 rounded-lg px-3 py-2">
                      {detail.parsed.base_url}
                    </div>
                  </div>
                  {Object.keys(detail.parsed.variables).length > 0 && (
                    <div>
                      <div className="text-xs text-gray-500 mb-2">变量</div>
                      <div className="space-y-1">
                        {Object.entries(detail.parsed.variables).map(([k, v]) => (
                          <div key={k} className="flex items-center gap-2 text-sm">
                            <span className="font-mono text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded">{k}</span>
                            <span className="text-gray-400">=</span>
                            <span className="text-gray-700">{v}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  <div>
                    <div className="text-xs text-gray-500 mb-1">原始配置</div>
                    <pre className="bg-gray-900 text-gray-100 rounded-lg p-4 text-xs overflow-auto font-mono leading-relaxed">
                      {detail.content}
                    </pre>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="flex items-center justify-center h-64 text-gray-400">
              <div className="text-center">
                <Eye className="w-10 h-10 mx-auto mb-2 opacity-50" />
                <p className="text-sm">选择环境查看详情</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
