import { useEffect, useState } from 'react';
import {
  BarChart3,
  Download,
  Eye,
  Trash2,
  FileText,
  CheckCircle2,
  XCircle,
  TrendingUp,
} from 'lucide-react';
import { reportsApi, executionApi } from '../api/client';

interface ReportItem {
  file: string;
  size: number;
  modified: number;
}

interface Summary {
  total_executions: number;
  completed: number;
  failed: number;
  total_cases: number;
  passed_cases: number;
  failed_cases: number;
  pass_rate: number;
}

export default function Reports() {
  const [reports, setReports] = useState<ReportItem[]>([]);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [loading, setLoading] = useState(true);
  const [executions, setExecutions] = useState<any[]>([]);
  const [generating, setGenerating] = useState<string | null>(null);

  const loadData = () => {
    setLoading(true);
    Promise.all([
      reportsApi.list(),
      reportsApi.summary(),
      executionApi.history({ limit: 20 }),
    ]).then(([reportsRes, summaryRes, execRes]) => {
      setReports(reportsRes.data.reports || []);
      setSummary(summaryRes.data);
      setExecutions(execRes.data.records || []);
      setLoading(false);
    }).catch(() => setLoading(false));
  };

  useEffect(() => { loadData(); }, []);

  const generateReport = (execId: string) => {
    setGenerating(execId);
    reportsApi.generate(execId).then(() => {
      setGenerating(null);
      loadData();
    }).catch(() => setGenerating(null));
  };

  const deleteReport = (fileName: string) => {
    if (!confirm(`确定删除报告 ${fileName}？`)) return;
    reportsApi.delete(fileName).then(() => loadData());
  };

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

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
        <h1 className="text-2xl font-bold text-gray-900">测试报告</h1>
        <p className="text-gray-500 mt-1">查看测试执行报告和统计数据</p>
      </div>

      {/* 统计概览 */}
      {summary && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-blue-50 rounded-lg"><BarChart3 className="w-5 h-5 text-blue-600" /></div>
              <div>
                <div className="text-xl font-bold">{summary.total_executions}</div>
                <div className="text-xs text-gray-500">总执行次数</div>
              </div>
            </div>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-green-50 rounded-lg"><CheckCircle2 className="w-5 h-5 text-green-600" /></div>
              <div>
                <div className="text-xl font-bold text-green-600">{summary.passed_cases}</div>
                <div className="text-xs text-gray-500">通过用例</div>
              </div>
            </div>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-red-50 rounded-lg"><XCircle className="w-5 h-5 text-red-600" /></div>
              <div>
                <div className="text-xl font-bold text-red-600">{summary.failed_cases}</div>
                <div className="text-xs text-gray-500">失败用例</div>
              </div>
            </div>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-indigo-50 rounded-lg"><TrendingUp className="w-5 h-5 text-indigo-600" /></div>
              <div>
                <div className="text-xl font-bold text-indigo-600">{summary.pass_rate}%</div>
                <div className="text-xs text-gray-500">通过率</div>
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* 报告列表 */}
        <div className="bg-white rounded-xl border border-gray-200">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="font-semibold text-gray-900 flex items-center gap-2">
              <FileText className="w-5 h-5 text-gray-400" />
              HTML 报告
            </h2>
          </div>
          <div className="divide-y divide-gray-100 max-h-96 overflow-auto">
            {reports.length === 0 ? (
              <div className="p-8 text-center text-gray-400">暂无报告</div>
            ) : (
              reports.map((r) => (
                <div key={r.file} className="px-6 py-3 flex items-center justify-between hover:bg-gray-50">
                  <div>
                    <div className="text-sm font-medium text-gray-900">{r.file}</div>
                    <div className="text-xs text-gray-400 mt-0.5">
                      {formatSize(r.size)} | {new Date(r.modified * 1000).toLocaleString('zh-CN')}
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <a
                      href={`/api/v1/reports/view/${r.file}`}
                      target="_blank"
                      className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-400 hover:text-gray-600"
                    >
                      <Eye className="w-4 h-4" />
                    </a>
                    <a
                      href={`/api/v1/reports/download/${r.file}`}
                      className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-400 hover:text-gray-600"
                    >
                      <Download className="w-4 h-4" />
                    </a>
                    <button
                      onClick={() => deleteReport(r.file)}
                      className="p-1.5 rounded-lg hover:bg-red-50 text-gray-400 hover:text-red-600"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* 从执行记录生成报告 */}
        <div className="bg-white rounded-xl border border-gray-200">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="font-semibold text-gray-900">从执行记录生成报告</h2>
          </div>
          <div className="divide-y divide-gray-100 max-h-96 overflow-auto">
            {executions.filter((e) => e.result).length === 0 ? (
              <div className="p-8 text-center text-gray-400">暂无可生成报告的执行记录</div>
            ) : (
              executions.filter((e) => e.result).map((e) => (
                <div key={e.id} className="px-6 py-3 flex items-center justify-between hover:bg-gray-50">
                  <div>
                    <div className="text-sm font-medium text-gray-900">{e.case_file}</div>
                    <div className="text-xs text-gray-400 mt-0.5">
                      ID: {e.id} | {e.started_at ? new Date(e.started_at).toLocaleString('zh-CN') : '-'}
                    </div>
                  </div>
                  <button
                    onClick={() => generateReport(e.id)}
                    disabled={generating === e.id}
                    className="px-3 py-1.5 bg-indigo-600 text-white rounded-lg text-xs font-medium hover:bg-indigo-700 disabled:opacity-50 transition-colors"
                  >
                    {generating === e.id ? '生成中...' : '生成报告'}
                  </button>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
