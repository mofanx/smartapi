import { useEffect, useState } from 'react';
import {
  FileText,
  Play,
  Eye,
  Trash2,
  Search,
  Tag,
  CheckCircle2,
  XCircle,
  X,
} from 'lucide-react';
import { casesApi, executionApi } from '../api/client';

interface CaseItem {
  file: string;
  name: string;
  description: string;
  tags: string[];
  priority: string;
  steps_count: number;
  type: string;
}

interface CaseDetail {
  file: string;
  content: string;
  valid: boolean;
  parsed?: any;
  error?: string;
}

export default function Cases() {
  const [cases, setCases] = useState<CaseItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [selectedTag, setSelectedTag] = useState('');
  const [detail, setDetail] = useState<CaseDetail | null>(null);
  const [showDetail, setShowDetail] = useState(false);
  const [running, setRunning] = useState<string | null>(null);
  const [runResult, setRunResult] = useState<any>(null);

  const loadCases = () => {
    setLoading(true);
    const params: any = {};
    if (selectedTag) params.tags = selectedTag;
    casesApi.list(params).then((res) => {
      setCases(res.data.cases || []);
      setLoading(false);
    }).catch(() => setLoading(false));
  };

  useEffect(() => { loadCases(); }, [selectedTag]);

  const allTags = [...new Set(cases.flatMap((c) => c.tags))];

  const filtered = cases.filter(
    (c) =>
      c.name.toLowerCase().includes(search.toLowerCase()) ||
      c.file.toLowerCase().includes(search.toLowerCase())
  );

  const viewCase = (file: string) => {
    casesApi.get(file).then((res) => {
      setDetail(res.data);
      setShowDetail(true);
      setRunResult(null);
    });
  };

  const runCase = (file: string) => {
    setRunning(file);
    setRunResult(null);
    executionApi.runSync({ file }).then((res) => {
      setRunResult(res.data);
      setRunning(null);
    }).catch((err) => {
      setRunResult({ error: err.message });
      setRunning(null);
    });
  };

  const deleteCase = (file: string) => {
    if (!confirm(`确定删除用例 ${file}？`)) return;
    casesApi.delete(file).then(() => loadCases());
  };

  const priorityColor: Record<string, string> = {
    high: 'text-red-600 bg-red-50',
    medium: 'text-amber-600 bg-amber-50',
    low: 'text-gray-500 bg-gray-100',
  };

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">用例管理</h1>
          <p className="text-gray-500 mt-1">管理 YAML/JSON 声明式测试用例</p>
        </div>
      </div>

      {/* 筛选栏 */}
      <div className="flex items-center gap-4 mb-6">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="搜索用例名称或文件..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-10 pr-4 py-2.5 rounded-lg border border-gray-200 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
          />
        </div>
        <div className="flex items-center gap-2">
          <Tag className="w-4 h-4 text-gray-400" />
          <select
            value={selectedTag}
            onChange={(e) => setSelectedTag(e.target.value)}
            className="px-3 py-2.5 rounded-lg border border-gray-200 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="">全部标签</option>
            {allTags.map((t) => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
        </div>
      </div>

      {/* 用例列表 */}
      {loading ? (
        <div className="flex justify-center py-20">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600" />
        </div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-20 text-gray-400">
          <FileText className="w-12 h-12 mx-auto mb-3 opacity-50" />
          <p>暂无测试用例</p>
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="bg-gray-50 border-b border-gray-200">
                <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase">用例</th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase">标签</th>
                <th className="px-6 py-3 text-center text-xs font-semibold text-gray-500 uppercase">步骤</th>
                <th className="px-6 py-3 text-center text-xs font-semibold text-gray-500 uppercase">优先级</th>
                <th className="px-6 py-3 text-right text-xs font-semibold text-gray-500 uppercase">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {filtered.map((c) => (
                <tr key={c.file} className="hover:bg-gray-50 transition-colors">
                  <td className="px-6 py-4">
                    <div className="text-sm font-medium text-gray-900">{c.name}</div>
                    <div className="text-xs text-gray-400 mt-0.5">{c.file}</div>
                    {c.description && (
                      <div className="text-xs text-gray-400 mt-0.5 truncate max-w-md">
                        {c.description}
                      </div>
                    )}
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex flex-wrap gap-1">
                      {c.tags.map((t) => (
                        <span key={t} className="text-xs bg-indigo-50 text-indigo-600 px-2 py-0.5 rounded-full">
                          {t}
                        </span>
                      ))}
                    </div>
                  </td>
                  <td className="px-6 py-4 text-center text-sm text-gray-600">{c.steps_count}</td>
                  <td className="px-6 py-4 text-center">
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${priorityColor[c.priority] || priorityColor.medium}`}>
                      {c.priority}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center justify-end gap-2">
                      <button
                        onClick={() => viewCase(c.file)}
                        className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-400 hover:text-gray-600 transition-colors"
                        title="查看详情"
                      >
                        <Eye className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => runCase(c.file)}
                        disabled={running === c.file}
                        className="p-1.5 rounded-lg hover:bg-indigo-50 text-indigo-500 hover:text-indigo-700 transition-colors disabled:opacity-50"
                        title="执行"
                      >
                        {running === c.file ? (
                          <div className="w-4 h-4 border-2 border-indigo-400 border-t-transparent rounded-full animate-spin" />
                        ) : (
                          <Play className="w-4 h-4" />
                        )}
                      </button>
                      <button
                        onClick={() => deleteCase(c.file)}
                        className="p-1.5 rounded-lg hover:bg-red-50 text-gray-400 hover:text-red-600 transition-colors"
                        title="删除"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* 详情/执行结果面板 */}
      {(showDetail || runResult) && (
        <div className="fixed inset-0 bg-black/30 z-50 flex items-center justify-center p-4" onClick={() => { setShowDetail(false); setRunResult(null); }}>
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-3xl max-h-[80vh] overflow-hidden" onClick={(e) => e.stopPropagation()}>
            <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
              <h3 className="font-semibold text-gray-900">
                {runResult ? '执行结果' : '用例详情'}
              </h3>
              <button onClick={() => { setShowDetail(false); setRunResult(null); }} className="p-1 hover:bg-gray-100 rounded-lg">
                <X className="w-5 h-5 text-gray-400" />
              </button>
            </div>
            <div className="p-6 overflow-auto max-h-[calc(80vh-4rem)]">
              {runResult && (
                <div className="mb-6">
                  {runResult.error ? (
                    <div className="flex items-center gap-2 text-red-600 bg-red-50 rounded-lg p-4">
                      <XCircle className="w-5 h-5" />
                      <span>{runResult.error}</span>
                    </div>
                  ) : (
                    <div>
                      <div className={`flex items-center gap-2 rounded-lg p-4 mb-4 ${
                        runResult.status === 'completed' ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'
                      }`}>
                        {runResult.status === 'completed' ? <CheckCircle2 className="w-5 h-5" /> : <XCircle className="w-5 h-5" />}
                        <span className="font-medium">
                          {runResult.status === 'completed' ? '执行通过' : '执行失败'}
                        </span>
                        {runResult.result && (
                          <span className="text-sm ml-2">
                            通过 {runResult.result.passed}/{runResult.result.total} ({runResult.result.pass_rate}%)
                          </span>
                        )}
                      </div>
                      {runResult.result?.cases?.map((c: any, i: number) => (
                        <div key={i} className="border border-gray-200 rounded-lg p-4 mb-3">
                          <div className="font-medium text-sm mb-2">{c.case_name}</div>
                          {c.step_results?.map((s: any, j: number) => (
                            <div key={j} className={`text-xs p-2 rounded mb-1 ${s.success ? 'bg-green-50' : 'bg-red-50'}`}>
                              <span className="font-medium">{s.step_name}</span>
                              <span className="ml-2 text-gray-500">
                                {s.status_code} | {s.response_time}ms
                              </span>
                              {s.assert_results?.map((a: any, k: number) => (
                                <div key={k} className={`ml-4 mt-1 ${a.passed ? 'text-green-600' : 'text-red-600'}`}>
                                  {a.passed ? '✓' : '✗'} {a.target} {a.operator} {JSON.stringify(a.expected)}
                                  {!a.passed && a.message && <span className="text-red-500 ml-1">- {a.message}</span>}
                                </div>
                              ))}
                            </div>
                          ))}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
              {detail && showDetail && (
                <pre className="bg-gray-900 text-gray-100 rounded-lg p-4 text-sm overflow-auto font-mono leading-relaxed">
                  {detail.content}
                </pre>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
