import { useEffect, useState } from 'react';
import {
  Database,
  FileText,
  Eye,
  Search,
} from 'lucide-react';
import { mockApi } from '../api/client';

interface MockConfig {
  file: string;
  routes_count: number;
}

export default function Mock() {
  const [configs, setConfigs] = useState<MockConfig[]>([]);
  const [dataTypes, setDataTypes] = useState<string[]>([]);
  const [configDetail, setConfigDetail] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [tab, setTab] = useState<'configs' | 'factory'>('configs');

  useEffect(() => {
    Promise.all([
      mockApi.configs().catch(() => ({ data: { configs: [] } })),
      mockApi.dataTypes().catch(() => ({ data: { types: [] } })),
    ]).then(([configsRes, typesRes]) => {
      setConfigs(configsRes.data.configs || []);
      setDataTypes(typesRes.data.types || []);
      setLoading(false);
    });
  }, []);

  const viewConfig = (file: string) => {
    mockApi.getConfig(file).then((res) => setConfigDetail(res.data));
  };

  const filteredTypes = dataTypes.filter((t: any) =>
    (typeof t === 'string' ? t : t.name || '').toLowerCase().includes(search.toLowerCase())
  );

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600" />
      </div>
    );
  }

  return (
    <div className="p-8">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Mock 管理</h1>
        <p className="text-gray-500 mt-1">Mock 接口配置和数据工厂</p>
      </div>

      {/* 标签切换 */}
      <div className="flex gap-1 bg-gray-100 rounded-lg p-1 w-fit mb-6">
        <button
          onClick={() => setTab('configs')}
          className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
            tab === 'configs' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'
          }`}
        >
          Mock 配置
        </button>
        <button
          onClick={() => setTab('factory')}
          className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
            tab === 'factory' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'
          }`}
        >
          数据工厂
        </button>
      </div>

      {tab === 'configs' ? (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* 配置列表 */}
          <div className="bg-white rounded-xl border border-gray-200">
            <div className="px-6 py-4 border-b border-gray-200">
              <h2 className="font-semibold text-gray-900 flex items-center gap-2">
                <FileText className="w-5 h-5 text-gray-400" />
                配置文件
              </h2>
            </div>
            <div className="divide-y divide-gray-100">
              {configs.length === 0 ? (
                <div className="p-8 text-center text-gray-400">暂无 Mock 配置</div>
              ) : (
                configs.map((c) => (
                  <div
                    key={c.file}
                    className="px-6 py-3 flex items-center justify-between hover:bg-gray-50 cursor-pointer"
                    onClick={() => viewConfig(c.file)}
                  >
                    <div>
                      <div className="text-sm font-medium text-gray-900">{c.file}</div>
                      <div className="text-xs text-gray-400">{c.routes_count} 个路由</div>
                    </div>
                    <Eye className="w-4 h-4 text-gray-400" />
                  </div>
                ))
              )}
            </div>
          </div>

          {/* 配置详情 */}
          <div className="bg-white rounded-xl border border-gray-200">
            <div className="px-6 py-4 border-b border-gray-200">
              <h2 className="font-semibold text-gray-900">
                {configDetail ? configDetail.file : '配置详情'}
              </h2>
            </div>
            {configDetail ? (
              <div className="p-6">
                {configDetail.routes?.map((r: any, i: number) => (
                  <div key={i} className="border border-gray-100 rounded-lg p-3 mb-3">
                    <div className="flex items-center gap-2 mb-1">
                      <span className={`px-2 py-0.5 rounded text-xs font-bold ${
                        r.method === 'GET' ? 'bg-green-100 text-green-700' :
                        r.method === 'POST' ? 'bg-blue-100 text-blue-700' :
                        r.method === 'PUT' ? 'bg-amber-100 text-amber-700' :
                        r.method === 'DELETE' ? 'bg-red-100 text-red-700' :
                        'bg-gray-100 text-gray-700'
                      }`}>
                        {r.method || 'GET'}
                      </span>
                      <span className="font-mono text-sm text-gray-700">{r.path}</span>
                      <span className="text-xs text-gray-400 ml-auto">{r.status_code || 200}</span>
                    </div>
                    {r.delay > 0 && (
                      <div className="text-xs text-gray-400">延迟: {r.delay}s</div>
                    )}
                    {r.rules?.length > 0 && (
                      <div className="text-xs text-gray-500 mt-1">
                        {r.rules.length} 条动态规则
                      </div>
                    )}
                  </div>
                ))}
                <div className="mt-4">
                  <div className="text-xs text-gray-500 mb-1">原始 YAML</div>
                  <pre className="bg-gray-900 text-gray-100 rounded-lg p-3 text-xs overflow-auto font-mono leading-relaxed max-h-64">
                    {configDetail.content}
                  </pre>
                </div>
              </div>
            ) : (
              <div className="p-12 text-center text-gray-400">
                <Database className="w-10 h-10 mx-auto mb-2 opacity-50" />
                <p className="text-sm">选择配置查看详情</p>
              </div>
            )}
          </div>
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-200">
          <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
            <h2 className="font-semibold text-gray-900 flex items-center gap-2">
              <Database className="w-5 h-5 text-gray-400" />
              数据类型 ({dataTypes.length})
            </h2>
            <div className="relative w-64">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                placeholder="搜索类型..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full pl-10 pr-3 py-2 rounded-lg border border-gray-200 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>
          </div>
          <div className="p-6">
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-2">
              {filteredTypes.map((t: any, i: number) => {
                const name = typeof t === 'string' ? t : t.name || JSON.stringify(t);
                return (
                  <div
                    key={i}
                    className="px-3 py-2 bg-gray-50 rounded-lg text-xs font-mono text-gray-700 hover:bg-indigo-50 hover:text-indigo-700 transition-colors cursor-default"
                  >
                    {name}
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
