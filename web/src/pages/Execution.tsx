import { useEffect, useState } from 'react';
import {
  Play,
  Clock,
  CheckCircle2,
  XCircle,
  RefreshCw,
  Filter,
} from 'lucide-react';
import { executionApi, casesApi } from '../api/client';

interface ExecutionRecord {
  id: string;
  case_file: string;
  status: string;
  started_at: string | null;
  finished_at: string | null;
  result: any;
  error: string | null;
}

interface CaseItem {
  file: string;
  name: string;
}

function statusBadge(status: string) {
  const map: Record<string, string> = {
    completed: 'bg-green-100 text-green-700',
    failed: 'bg-red-100 text-red-700',
    running: 'bg-blue-100 text-blue-700',
    pending: 'bg-gray-100 text-gray-600',
  };
  const labelMap: Record<string, string> = {
    completed: '通过',
    failed: '失败',
    running: '执行中',
    pending: '等待中',
  };
  return (
    <span className={`px-2.5 py-1 rounded-full text-xs font-medium ${map[status] || map.pending}`}>
      {labelMap[status] || status}
    </span>
  );
}

export default function Execution() {
  const [records, setRecords] = useState<ExecutionRecord[]>([]);
  const [cases, setCases] = useState<CaseItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterStatus, setFilterStatus] = useState('');
  const [selectedCase, setSelectedCase] = useState('');
  const [running, setRunning] = useState(false);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const loadData = () => {
    setLoading(true);
    Promise.all([
      executionApi.history({ limit: 50, status: filterStatus || undefined }),
      casesApi.list(),
    ]).then(([execRes, casesRes]) => {
      setRecords(execRes.data.records || []);
      setCases(casesRes.data.cases || []);
      setLoading(false);
    }).catch(() => setLoading(false));
  };

  useEffect(() => { loadData(); }, [filterStatus]);

  const executeCase = () => {
    if (!selectedCase) return;
    setRunning(true);
    executionApi.run({ file: selectedCase }).then(() => {
      setRunning(false);
      setTimeout(loadData, 1000);
    }).catch(() => setRunning(false));
  };

  const batchExecute = () => {
    setRunning(true);
    executionApi.batch({}).then(() => {
      setRunning(false);
      setTimeout(loadData, 2000);
    }).catch(() => setRunning(false));
  };

  const durationStr = (r: ExecutionRecord) => {
    if (!r.started_at || !r.finished_at) return '-';
    const ms = new Date(r.finished_at).getTime() - new Date(r.started_at).getTime();
    return ms < 1000 ? `${ms}ms` : `${(ms / 1000).toFixed(1)}s`;
  };

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">执行管理</h1>
          <p className="text-gray-500 mt-1">执行测试用例并查看历史记录</p>
        </div>
        <button
          onClick={loadData}
          className="p-2 rounded-lg hover:bg-gray-100 text-gray-400 hover:text-gray-600 transition-colors"
          title="刷新"
        >
          <RefreshCw className="w-5 h-5" />
        </button>
      </div>

      {/* 执行面板 */}
      <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
        <h2 className="text-sm font-semibold text-gray-700 mb-4">执行用例</h2>
        <div className="flex items-center gap-4">
          <select
            value={selectedCase}
            onChange={(e) => setSelectedCase(e.target.value)}
            className="flex-1 max-w-md px-4 py-2.5 rounded-lg border border-gray-200 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="">选择用例文件...</option>
            {cases.map((c) => (
              <option key={c.file} value={c.file}>{c.name} ({c.file})</option>
            ))}
          </select>
          <button
            onClick={executeCase}
            disabled={!selectedCase || running}
            className="px-5 py-2.5 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
          >
            {running ? (
              <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
            ) : (
              <Play className="w-4 h-4" />
            )}
            执行
          </button>
          <button
            onClick={batchExecute}
            disabled={running}
            className="px-5 py-2.5 bg-white border border-gray-200 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-50 disabled:opacity-50 transition-colors"
          >
            批量执行全部
          </button>
        </div>
      </div>

      {/* 筛选 */}
      <div className="flex items-center gap-3 mb-4">
        <Filter className="w-4 h-4 text-gray-400" />
        {['', 'completed', 'failed', 'running', 'pending'].map((s) => (
          <button
            key={s}
            onClick={() => setFilterStatus(s)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
              filterStatus === s
                ? 'bg-indigo-100 text-indigo-700'
                : 'bg-gray-100 text-gray-500 hover:bg-gray-200'
            }`}
          >
            {s === '' ? '全部' : s === 'completed' ? '通过' : s === 'failed' ? '失败' : s === 'running' ? '执行中' : '等待中'}
          </button>
        ))}
      </div>

      {/* 执行历史 */}
      {loading ? (
        <div className="flex justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600" />
        </div>
      ) : records.length === 0 ? (
        <div className="text-center py-20 text-gray-400">
          <Clock className="w-12 h-12 mx-auto mb-3 opacity-50" />
          <p>暂无执行记录</p>
        </div>
      ) : (
        <div className="space-y-3">
          {records.map((r) => (
            <div key={r.id} className="bg-white rounded-xl border border-gray-200 overflow-hidden">
              <div
                className="px-6 py-4 flex items-center justify-between cursor-pointer hover:bg-gray-50 transition-colors"
                onClick={() => setExpandedId(expandedId === r.id ? null : r.id)}
              >
                <div className="flex items-center gap-4">
                  {r.status === 'completed' ? (
                    <CheckCircle2 className="w-5 h-5 text-green-500" />
                  ) : r.status === 'failed' ? (
                    <XCircle className="w-5 h-5 text-red-500" />
                  ) : (
                    <Clock className="w-5 h-5 text-gray-400" />
                  )}
                  <div>
                    <div className="text-sm font-medium text-gray-900">{r.case_file}</div>
                    <div className="text-xs text-gray-400 mt-0.5">
                      ID: {r.id} | {r.started_at ? new Date(r.started_at).toLocaleString('zh-CN') : '-'}
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  <span className="text-xs text-gray-400">{durationStr(r)}</span>
                  {statusBadge(r.status)}
                  {r.result && (
                    <span className="text-xs text-gray-500">
                      {r.result.passed}/{r.result.total}
                    </span>
                  )}
                </div>
              </div>

              {expandedId === r.id && r.result && (
                <div className="px-6 pb-4 border-t border-gray-100 pt-4">
                  <div className="grid grid-cols-4 gap-4 mb-4">
                    <div className="text-center p-3 bg-gray-50 rounded-lg">
                      <div className="text-lg font-bold text-gray-900">{r.result.total}</div>
                      <div className="text-xs text-gray-500">总用例</div>
                    </div>
                    <div className="text-center p-3 bg-green-50 rounded-lg">
                      <div className="text-lg font-bold text-green-600">{r.result.passed}</div>
                      <div className="text-xs text-gray-500">通过</div>
                    </div>
                    <div className="text-center p-3 bg-red-50 rounded-lg">
                      <div className="text-lg font-bold text-red-600">{r.result.failed}</div>
                      <div className="text-xs text-gray-500">失败</div>
                    </div>
                    <div className="text-center p-3 bg-indigo-50 rounded-lg">
                      <div className="text-lg font-bold text-indigo-600">{r.result.pass_rate}%</div>
                      <div className="text-xs text-gray-500">通过率</div>
                    </div>
                  </div>
                  {r.result.cases?.map((c: any, i: number) => (
                    <div key={i} className="border border-gray-100 rounded-lg p-3 mb-2">
                      <div className="text-sm font-medium mb-2 flex items-center gap-2">
                        {c.success ? <CheckCircle2 className="w-4 h-4 text-green-500" /> : <XCircle className="w-4 h-4 text-red-500" />}
                        {c.case_name}
                        <span className="text-xs text-gray-400">({c.total_time?.toFixed(0)}ms)</span>
                      </div>
                      {c.step_results?.map((s: any, j: number) => (
                        <div key={j} className={`text-xs p-2 rounded mb-1 flex items-center justify-between ${s.success ? 'bg-green-50' : 'bg-red-50'}`}>
                          <span>{s.step_name}</span>
                          <span className="text-gray-500">{s.status_code} | {s.response_time}ms</span>
                        </div>
                      ))}
                    </div>
                  ))}
                  {r.error && (
                    <div className="bg-red-50 text-red-700 rounded-lg p-3 text-sm">{r.error}</div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
