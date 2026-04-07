import { useEffect, useState } from 'react';
import {
  CheckCircle2,
  FileText,
  TrendingUp,
  Activity,
  Play,
  BarChart3,
} from 'lucide-react';
import { reportsApi, casesApi, executionApi } from '../api/client';

interface SummaryData {
  total_executions: number;
  completed: number;
  failed: number;
  total_cases: number;
  passed_cases: number;
  failed_cases: number;
  pass_rate: number;
}

interface CaseItem {
  file: string;
  name: string;
  tags: string[];
  steps_count: number;
}

interface ExecutionRecord {
  id: string;
  case_file: string;
  status: string;
  started_at: string | null;
  finished_at: string | null;
}

function StatCard({
  icon: Icon,
  label,
  value,
  sub,
  color,
}: {
  icon: React.ElementType;
  label: string;
  value: string | number;
  sub?: string;
  color: string;
}) {
  const colors: Record<string, string> = {
    indigo: 'bg-indigo-50 text-indigo-600',
    green: 'bg-green-50 text-green-600',
    red: 'bg-red-50 text-red-600',
    amber: 'bg-amber-50 text-amber-600',
    blue: 'bg-blue-50 text-blue-600',
  };
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6 hover:shadow-md transition-shadow">
      <div className="flex items-center gap-4">
        <div className={`p-3 rounded-lg ${colors[color]}`}>
          <Icon className="w-6 h-6" />
        </div>
        <div>
          <div className="text-2xl font-bold text-gray-900">{value}</div>
          <div className="text-sm text-gray-500">{label}</div>
          {sub && <div className="text-xs text-gray-400 mt-0.5">{sub}</div>}
        </div>
      </div>
    </div>
  );
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
    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${map[status] || map.pending}`}>
      {labelMap[status] || status}
    </span>
  );
}

export default function Dashboard() {
  const [summary, setSummary] = useState<SummaryData | null>(null);
  const [cases, setCases] = useState<CaseItem[]>([]);
  const [executions, setExecutions] = useState<ExecutionRecord[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      reportsApi.summary().catch(() => ({ data: null })),
      casesApi.list().catch(() => ({ data: { cases: [] } })),
      executionApi.history({ limit: 10 }).catch(() => ({ data: { records: [] } })),
    ]).then(([summaryRes, casesRes, execRes]) => {
      setSummary(summaryRes.data);
      setCases(casesRes.data.cases || []);
      setExecutions(execRes.data.records || []);
      setLoading(false);
    });
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600" />
      </div>
    );
  }

  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">仪表盘</h1>
        <p className="text-gray-500 mt-1">SmartAPI-Test 测试平台概览</p>
      </div>

      {/* 统计卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <StatCard
          icon={FileText}
          label="测试用例"
          value={cases.length}
          sub="YAML 声明式用例"
          color="indigo"
        />
        <StatCard
          icon={Play}
          label="执行次数"
          value={summary?.total_executions || 0}
          color="blue"
        />
        <StatCard
          icon={CheckCircle2}
          label="通过率"
          value={`${summary?.pass_rate || 0}%`}
          sub={`${summary?.passed_cases || 0} 通过 / ${summary?.failed_cases || 0} 失败`}
          color="green"
        />
        <StatCard
          icon={TrendingUp}
          label="用例总步骤"
          value={cases.reduce((sum, c) => sum + c.steps_count, 0)}
          color="amber"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* 用例列表 */}
        <div className="bg-white rounded-xl border border-gray-200">
          <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
            <h2 className="font-semibold text-gray-900 flex items-center gap-2">
              <FileText className="w-5 h-5 text-gray-400" />
              测试用例
            </h2>
            <span className="text-xs text-gray-400">{cases.length} 个用例</span>
          </div>
          <div className="divide-y divide-gray-100 max-h-80 overflow-auto">
            {cases.length === 0 ? (
              <div className="p-8 text-center text-gray-400">暂无测试用例</div>
            ) : (
              cases.map((c) => (
                <div key={c.file} className="px-6 py-3 hover:bg-gray-50 transition-colors">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="text-sm font-medium text-gray-900">{c.name}</div>
                      <div className="text-xs text-gray-400 mt-0.5">{c.file}</div>
                    </div>
                    <div className="flex items-center gap-2">
                      {c.tags.map((t) => (
                        <span
                          key={t}
                          className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded"
                        >
                          {t}
                        </span>
                      ))}
                      <span className="text-xs text-gray-400">{c.steps_count} 步骤</span>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* 最近执行 */}
        <div className="bg-white rounded-xl border border-gray-200">
          <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
            <h2 className="font-semibold text-gray-900 flex items-center gap-2">
              <Activity className="w-5 h-5 text-gray-400" />
              最近执行
            </h2>
            <span className="text-xs text-gray-400">{executions.length} 条记录</span>
          </div>
          <div className="divide-y divide-gray-100 max-h-80 overflow-auto">
            {executions.length === 0 ? (
              <div className="p-8 text-center text-gray-400">暂无执行记录</div>
            ) : (
              executions.map((e) => (
                <div key={e.id} className="px-6 py-3 hover:bg-gray-50 transition-colors">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="text-sm font-medium text-gray-900">{e.case_file}</div>
                      <div className="text-xs text-gray-400 mt-0.5">
                        {e.started_at
                          ? new Date(e.started_at).toLocaleString('zh-CN')
                          : '-'}
                      </div>
                    </div>
                    {statusBadge(e.status)}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* 通过率进度条 */}
      {summary && summary.total_cases > 0 && (
        <div className="mt-8 bg-white rounded-xl border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-semibold text-gray-900 flex items-center gap-2">
              <BarChart3 className="w-5 h-5 text-gray-400" />
              总体通过率
            </h2>
            <span className="text-sm font-bold text-gray-700">{summary.pass_rate}%</span>
          </div>
          <div className="w-full bg-gray-100 rounded-full h-4 overflow-hidden">
            <div
              className="h-full rounded-full transition-all duration-700 ease-out"
              style={{
                width: `${summary.pass_rate}%`,
                background:
                  summary.pass_rate >= 80
                    ? 'linear-gradient(90deg, #10b981, #34d399)'
                    : summary.pass_rate >= 50
                    ? 'linear-gradient(90deg, #f59e0b, #fbbf24)'
                    : 'linear-gradient(90deg, #ef4444, #f87171)',
              }}
            />
          </div>
          <div className="flex justify-between mt-2 text-xs text-gray-400">
            <span>通过: {summary.passed_cases}</span>
            <span>失败: {summary.failed_cases}</span>
            <span>总计: {summary.total_cases}</span>
          </div>
        </div>
      )}
    </div>
  );
}
