"""HTML 报告生成器 - 美化版测试报告"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Optional

from jinja2 import Template
from loguru import logger

from smartapi.core.models import TestCaseResult


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SmartAPI-Test 测试报告</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f7fa; color: #333; }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 12px; margin-bottom: 24px; }
        .header h1 { font-size: 28px; margin-bottom: 8px; }
        .header .meta { opacity: 0.9; font-size: 14px; }

        .summary { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 24px; }
        .summary-card { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); text-align: center; }
        .summary-card .number { font-size: 36px; font-weight: bold; }
        .summary-card .label { color: #666; margin-top: 4px; }
        .total .number { color: #333; }
        .passed .number { color: #52c41a; }
        .failed .number { color: #ff4d4f; }
        .skipped .number { color: #faad14; }
        .time .number { color: #1890ff; font-size: 24px; }

        .progress-bar { height: 8px; background: #eee; border-radius: 4px; margin: 16px 0; overflow: hidden; }
        .progress-fill { height: 100%; border-radius: 4px; transition: width 0.5s; }
        .progress-pass { background: #52c41a; }
        .progress-fail { background: #ff4d4f; }

        .case-list { margin-top: 24px; }
        .case-item { background: white; border-radius: 10px; margin-bottom: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); overflow: hidden; }
        .case-header { padding: 16px 20px; cursor: pointer; display: flex; justify-content: space-between; align-items: center; border-left: 4px solid; }
        .case-header.pass { border-left-color: #52c41a; }
        .case-header.fail { border-left-color: #ff4d4f; }
        .case-header.skip { border-left-color: #faad14; }
        .case-header h3 { font-size: 16px; }
        .case-header .badge { padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: bold; color: white; }
        .badge-pass { background: #52c41a; }
        .badge-fail { background: #ff4d4f; }
        .badge-skip { background: #faad14; }

        .case-body { padding: 0 20px 16px; display: none; }
        .case-item.active .case-body { display: block; }
        .step { border: 1px solid #f0f0f0; border-radius: 8px; margin: 8px 0; padding: 12px; }
        .step-header { display: flex; justify-content: space-between; margin-bottom: 8px; }
        .step-name { font-weight: 600; }
        .step-status { font-size: 13px; }
        .step-detail { font-size: 13px; color: #666; }
        .step-detail .label { color: #999; }

        .assert-list { margin-top: 8px; }
        .assert-item { padding: 4px 8px; margin: 2px 0; border-radius: 4px; font-size: 13px; }
        .assert-pass { background: #f6ffed; color: #52c41a; }
        .assert-fail { background: #fff2f0; color: #ff4d4f; }

        .detail-block { margin-top: 8px; background: #fafafa; padding: 10px; border-radius: 6px; }
        .detail-block pre { font-size: 12px; overflow-x: auto; white-space: pre-wrap; word-break: break-all; }
        .detail-title { font-size: 12px; color: #999; margin-bottom: 4px; }

        .footer { text-align: center; padding: 20px; color: #999; font-size: 13px; }
    </style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>SmartAPI-Test 测试报告</h1>
        <div class="meta">
            <span>生成时间: {{ generated_at }}</span>
            {% if title %}<span> | {{ title }}</span>{% endif %}
        </div>
    </div>

    <div class="summary">
        <div class="summary-card total"><div class="number">{{ total }}</div><div class="label">总用例</div></div>
        <div class="summary-card passed"><div class="number">{{ passed }}</div><div class="label">通过</div></div>
        <div class="summary-card failed"><div class="number">{{ failed }}</div><div class="label">失败</div></div>
        <div class="summary-card skipped"><div class="number">{{ skipped }}</div><div class="label">跳过</div></div>
        <div class="summary-card time"><div class="number">{{ total_time }}s</div><div class="label">总耗时</div></div>
    </div>

    <div class="progress-bar">
        <div class="progress-fill progress-pass" style="width: {{ pass_rate }}%; float: left;"></div>
        <div class="progress-fill progress-fail" style="width: {{ fail_rate }}%; float: left;"></div>
    </div>
    <div style="text-align: center; color: #666; font-size: 14px; margin-bottom: 16px;">
        通过率: {{ pass_rate }}%
    </div>

    <div class="case-list">
        {% for case in cases %}
        <div class="case-item">
            <div class="case-header {{ 'pass' if case.success else 'fail' }}" onclick="this.parentElement.classList.toggle('active')">
                <h3>{{ case.case_name }}</h3>
                <div>
                    <span style="color:#999;font-size:13px;">{{ case.total_time }}ms</span>
                    <span class="badge {{ 'badge-pass' if case.success else 'badge-fail' }}">
                        {{ '通过' if case.success else '失败' }}
                    </span>
                </div>
            </div>
            <div class="case-body">
                {% for step in case.step_results %}
                <div class="step">
                    <div class="step-header">
                        <span class="step-name">
                            {{ '✅' if step.success else ('⏭️' if step.skipped else '❌') }}
                            {{ step.step_name }}
                        </span>
                        <span class="step-status">
                            {% if step.status_code %}{{ step.status_code }} | {% endif %}
                            {% if step.response_time %}{{ step.response_time }}ms{% endif %}
                        </span>
                    </div>
                    {% if step.request_url %}
                    <div class="step-detail">
                        <span class="label">请求:</span> {{ step.request_method }} {{ step.request_url }}
                    </div>
                    {% endif %}
                    {% if step.error %}
                    <div class="step-detail" style="color:#ff4d4f;">
                        <span class="label">错误:</span> {{ step.error }}
                    </div>
                    {% endif %}
                    {% if step.skipped %}
                    <div class="step-detail" style="color:#faad14;">
                        <span class="label">跳过原因:</span> {{ step.skip_reason }}
                    </div>
                    {% endif %}
                    {% if step.assert_results %}
                    <div class="assert-list">
                        {% for ar in step.assert_results %}
                        <div class="assert-item {{ 'assert-pass' if ar.passed else 'assert-fail' }}">
                            {{ '✅' if ar.passed else '❌' }}
                            {{ ar.target }}{% if ar.expression %}[{{ ar.expression }}]{% endif %}
                            {{ ar.operator }} {{ ar.expected }}
                            {% if not ar.passed %} (实际: {{ ar.actual }}){% endif %}
                        </div>
                        {% endfor %}
                    </div>
                    {% endif %}
                    {% if step.request_body or step.response_body %}
                    <details>
                        <summary style="font-size:12px;color:#999;cursor:pointer;margin-top:8px;">查看详情</summary>
                        {% if step.request_body %}
                        <div class="detail-block">
                            <div class="detail-title">请求体</div>
                            <pre>{{ step.request_body | tojson_pretty }}</pre>
                        </div>
                        {% endif %}
                        {% if step.response_body %}
                        <div class="detail-block">
                            <div class="detail-title">响应体</div>
                            <pre>{{ step.response_body | tojson_pretty }}</pre>
                        </div>
                        {% endif %}
                    </details>
                    {% endif %}
                </div>
                {% endfor %}
            </div>
        </div>
        {% endfor %}
    </div>

    <div class="footer">
        SmartAPI-Test v0.1.0 | Powered by Python + pytest
    </div>
</div>
</body>
</html>"""


def _tojson_pretty(value):
    """Jinja2 过滤器：美化 JSON 输出"""
    try:
        if isinstance(value, str):
            return value
        return json.dumps(value, indent=2, ensure_ascii=False, default=str)
    except Exception:
        return str(value)


class HtmlReportGenerator:
    """HTML 报告生成器"""

    def __init__(self, title: str = ""):
        self.title = title
        self.results: list[TestCaseResult] = []

    def add_result(self, result: TestCaseResult):
        """添加用例结果"""
        self.results.append(result)

    def generate(self, output_path: str | Path = "reports/report.html") -> Path:
        """生成 HTML 报告"""
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        total = len(self.results)
        passed = sum(1 for r in self.results if r.success)
        failed = total - passed
        skipped = sum(1 for r in self.results for s in r.step_results if s.skipped)
        total_time = round(sum(r.total_time for r in self.results) / 1000, 2)
        pass_rate = round(passed / total * 100, 1) if total > 0 else 0
        fail_rate = round(failed / total * 100, 1) if total > 0 else 0

        template = Template(HTML_TEMPLATE)
        template.globals["tojson_pretty"] = _tojson_pretty
        # 注册过滤器
        env = template.environment
        env.filters["tojson_pretty"] = _tojson_pretty

        html = template.render(
            title=self.title,
            generated_at=time.strftime("%Y-%m-%d %H:%M:%S"),
            total=total,
            passed=passed,
            failed=failed,
            skipped=skipped,
            total_time=total_time,
            pass_rate=pass_rate,
            fail_rate=fail_rate,
            cases=[r.model_dump() for r in self.results],
        )

        output.write_text(html, encoding="utf-8")
        logger.info(f"HTML 报告已生成: {output}")
        return output
