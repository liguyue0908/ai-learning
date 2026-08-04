#!/usr/bin/env python3
"""
AI 学习每日推送 — GitHub Actions 版
每天 UTC 0:00（北京时间 8:00）自动运行
读取 content/ → 生成 HTML → 提交到仓库 → 企微推送链接
"""

import json
import os
import re
import subprocess
import sys
import time
from datetime import date, datetime, timedelta

# === 配置 ===
WEBHOOK_URL = os.environ.get("WEIXIN_WEBHOOK", "") or "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=d6ef3e1d-74d2-4a0a-89e8-a0aa52970813"
PAGES_URL = os.environ.get("PAGES_URL", "https://liguyue0908.github.io/ai-learning")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONTENT_DIR = os.path.join(BASE_DIR, "content")
HTML_DIR = os.path.join(BASE_DIR, "html")
START_DATE = date(2026, 8, 3)

# === CSS ===
CSS = """
:root {
  --bg: #fafaf9; --card: #ffffff; --text: #1c1917; --text2: #57534e;
  --accent: #2563eb; --accent2: #eff6ff; --border: #e7e5e4;
  --tag-bg: #fef3c7; --tag-text: #92400e; --code-bg: #f5f5f4;
  --success: #16a34a; --warning: #ea580c;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #0c0a09; --card: #1c1917; --text: #fafaf9; --text2: #a8a29e;
    --accent: #60a5fa; --accent2: #0f2b4a; --border: #292524;
    --tag-bg: #422006; --tag-text: #fcd34d; --code-bg: #1c1917;
    --success: #4ade80; --warning: #fb923c;
  }
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "PingFang SC", "Microsoft YaHei", sans-serif;
  background: var(--bg); color: var(--text); line-height: 1.85; font-size: 17px;
  max-width: 720px; margin: 0 auto; padding: 24px 20px 60px; -webkit-font-smoothing: antialiased;
}
.header { text-align: center; padding: 28px 0 20px; border-bottom: 2px solid var(--border); margin-bottom: 28px; }
.header .date-tag { display: inline-block; background: var(--accent2); color: var(--accent); padding: 4px 16px; border-radius: 20px; font-size: 14px; font-weight: 600; margin-bottom: 10px; }
.header h1 { font-size: 28px; font-weight: 700; letter-spacing: -0.02em; }
.header .subtitle { color: var(--text2); font-size: 14px; margin-top: 2px; }
h2 { font-size: 22px; font-weight: 700; margin: 32px 0 10px; padding-bottom: 8px; border-bottom: 1px solid var(--border); }
h3 { font-size: 19px; font-weight: 600; margin: 24px 0 8px; color: var(--accent); }
p { margin: 12px 0; }
table { width: 100%; border-collapse: collapse; margin: 16px 0; font-size: 15px; }
th, td { padding: 10px 14px; text-align: left; border-bottom: 1px solid var(--border); }
th { background: var(--code-bg); font-weight: 600; font-size: 13px; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text2); }
blockquote { border-left: 4px solid var(--accent); padding: 12px 20px; margin: 16px 0; background: var(--accent2); border-radius: 0 8px 8px 0; font-size: 16px; }
code { background: var(--code-bg); padding: 2px 6px; border-radius: 4px; font-size: 14px; font-family: "SF Mono", "Fira Code", monospace; }
pre { background: var(--code-bg); padding: 16px 20px; border-radius: 8px; overflow-x: auto; margin: 12px 0; font-size: 14px; line-height: 1.6; border: 1px solid var(--border); }
ul, ol { padding-left: 24px; margin: 8px 0; }
li { margin: 6px 0; }
.practice-box { background: linear-gradient(135deg, var(--accent2), var(--card)); border: 2px solid var(--accent); border-radius: 16px; padding: 28px 24px; margin: 32px 0; }
.practice-box h3 { color: var(--accent); margin-top: 0; }
.tag { display: inline-block; background: var(--tag-bg); color: var(--tag-text); padding: 2px 10px; border-radius: 12px; font-size: 12px; font-weight: 600; }
.compare { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin: 16px 0; }
.compare .bad { background: #fef2f2; border: 1px solid #fecaca; border-radius: 8px; padding: 14px; }
.compare .good { background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 8px; padding: 14px; }
@media (prefers-color-scheme: dark) { .compare .bad { background: #3b1116; border-color: #7f1d1d; } .compare .good { background: #0a2e1a; border-color: #14532d; } }
.progress-bar { display: flex; gap: 4px; margin: 20px 0; }
.progress-bar .dot { flex: 1; height: 4px; border-radius: 2px; background: var(--border); }
.progress-bar .dot.done { background: var(--accent); }
.progress-bar .dot.current { background: var(--accent); box-shadow: 0 0 8px var(--accent); }
.footer { text-align: center; padding: 28px 0 0; color: var(--text2); font-size: 14px; border-top: 1px solid var(--border); margin-top: 36px; }
hr { border: none; border-top: 1px solid var(--border); margin: 24px 0; }
.font-info { color: var(--accent); font-size: 14px; }
@media (max-width: 600px) { body { font-size: 16px; padding: 16px 16px 40px; } .header h1 { font-size: 24px; } h2 { font-size: 20px; } .compare { grid-template-columns: 1fr; } table { font-size: 13px; } th, td { padding: 8px 10px; } }
"""


def log(msg):
    print(f"[{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC] {msg}")


def send_markdown(content):
    payload = {"msgtype": "markdown", "markdown": {"content": content}}
    body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
    subprocess.run(
        ['curl', '-s', '-X', 'POST', WEBHOOK_URL,
         '-H', 'Content-Type: application/json', '-d', body],
        capture_output=True, text=True, timeout=30
    )
    log("Markdown sent")


def get_learning_day(today=None):
    if today is None:
        today = date.today()
    if today < START_DATE:
        return 0
    day_count = 0
    current = START_DATE
    while current <= today:
        if current.weekday() < 5:
            day_count += 1
        current += timedelta(days=1)
    return day_count


def get_week_and_day(learning_day):
    week = (learning_day - 1) // 5 + 1
    day = (learning_day - 1) % 5 + 1
    return f"W{week}D{day}"


def get_date_desc(learning_day):
    week = (learning_day - 1) // 5 + 1
    weeks = ["", "第一周", "第二周", "第三周", "第四周", "第五周", "第六周", "第七周", "第八周"]
    days = ["", "周一", "周二", "周三", "周四", "周五"]
    day = (learning_day - 1) % 5 + 1
    return f"{weeks[week]} · {days[day]}"


def markdown_to_html(md_content, date_desc, wd):
    html_body = md_content
    html_body = re.sub(r'^#### (.+)$', r'<h4>\1</h4>', html_body, flags=re.MULTILINE)
    html_body = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html_body, flags=re.MULTILINE)
    html_body = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html_body, flags=re.MULTILINE)
    html_body = re.sub(r'^---$', r'<hr>', html_body, flags=re.MULTILINE)
    html_body = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html_body)
    html_body = re.sub(r'`([^`]+)`', r'<code>\1</code>', html_body)
    html_body = re.sub(r'^> (.+)$', r'<blockquote>\1</blockquote>', html_body, flags=re.MULTILINE)
    html_body = re.sub(r'</blockquote>\n<blockquote>', '\n', html_body)
    html_body = re.sub(r'<font color="info">(.+?)</font>', r'<span class="font-info">\1</span>', html_body)

    lines = html_body.split('\n')
    result = []
    in_table = False
    table_rows = []
    in_code_block = False

    for line in lines:
        if line.startswith('```'):
            in_code_block = not in_code_block
            result.append('</pre>' if not in_code_block else '<pre>')
            continue
        if in_code_block:
            result.append(line)
            continue
        if '|' in line and line.strip().startswith('|'):
            cells = [c.strip() for c in line.split('|')[1:-1]]
            if all(c.replace('-', '').replace(':', '').replace(' ', '') == '' for c in cells):
                in_table = True
                continue
            table_rows.append(cells)
            in_table = True
            continue
        else:
            if in_table and table_rows:
                html_table = '<table>'
                for i, row in enumerate(table_rows):
                    html_table += '<tr>'
                    tag = 'th' if i == 0 else 'td'
                    for cell in row:
                        html_table += f'<{tag}>{cell}</{tag}>'
                    html_table += '</tr>'
                html_table += '</table>'
                result.append(html_table)
                table_rows = []
                in_table = False
            result.append(line)

    if table_rows:
        html_table = '<table>'
        for i, row in enumerate(table_rows):
            html_table += '<tr>'
            tag = 'th' if i == 0 else 'td'
            for cell in row:
                html_table += f'<{tag}>{cell}</{tag}>'
            html_table += '</tr>'
        html_table += '</table>'
        result.append(html_table)

    html_body = '\n'.join(result)

    final_lines = []
    for line in html_body.split('\n'):
        line = line.strip()
        if not line:
            final_lines.append('')
            continue
        if re.match(r'^<(/?(h[1-4]|table|tr|t[hd]|pre|blockquote|hr|ul|ol|li|div|p|strong|em|code|span|a|img|br))', line):
            final_lines.append(line)
        else:
            final_lines.append(f'<p>{line}</p>')

    html_body = '\n'.join(final_lines)
    html_body = re.sub(r'<p></p>', '<br>', html_body)

    m = re.match(r'W(\d+)D(\d+)', wd)
    w_num, d_num = int(m.group(1)), int(m.group(2))
    day_total = (w_num - 1) * 5 + d_num
    day_num = d_num

    progress_dots = ''
    for i in range(1, 6):
        cls = 'done' if i <= day_num else ''
        progress_dots += f'<div class="dot {cls}"></div>'

    week_num = w_num

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=yes">
<title>AI 学习之旅 · {date_desc}</title>
<style>{CSS}</style>
</head>
<body>
<div class="header">
  <div class="date-tag">{date_desc}</div>
  <h1>AI 学习之旅</h1>
  <div class="subtitle">第 {day_total} 天 · Phase {week_num} · 预计阅读 30 分钟</div>
</div>
<div class="progress-bar">{progress_dots}</div>
{html_body}
<div class="footer">
  <p>💡 到公司后用 10 分钟在 Claude Code 中完成练习，效果加倍！</p>
  <p style="margin-top:8px;font-size:12px;color:var(--text2);">AI 学习之旅 · {date_desc}</p>
</div>
</body>
</html>"""
    return html


def build_summary(parts, date_desc, html_url):
    title = "今日学习"
    for part in parts:
        m = re.search(r'^## (.+)', part, re.MULTILINE)
        if m:
            title = m.group(1)
            break

    outline = []
    for part in parts:
        headers = re.findall(r'^### (.+)$', part, re.MULTILINE)
        outline.extend(headers)

    outline_md = '\n'.join([f'> {i+1}. {h}' for i, h in enumerate(outline[:10])])

    practice_title = "今日练习"
    for part in parts:
        m = re.search(r'### 🏋️ (.+)', part)
        if m:
            practice_title = m.group(1)
            break

    return f"""## 📚 {date_desc}

### {title}

{outline_md}

---
### 🏋️ {practice_title}

[📎 **点击查看完整学习内容**]({html_url})

> 💡 预计阅读 30 分钟 · 到公司后 10 分钟实操练习"""


def commit_and_push(wd):
    """将生成的 HTML 提交并推送到仓库。返回 True 表示有新的提交。"""
    try:
        subprocess.run(['git', 'config', 'user.name', 'AI Learning Bot'], check=True)
        subprocess.run(['git', 'config', 'user.email', 'bot@ai-learning.dev'], check=True)
        subprocess.run(['git', 'add', f'html/{wd}.html', 'html/index.html'], check=True)
        # 检查是否有变更
        status = subprocess.run(['git', 'diff', '--cached', '--quiet'], capture_output=True)
        if status.returncode != 0:
            subprocess.run(['git', 'commit', '-m', f'Add {wd} [{date.today().isoformat()}]'], check=True)
            subprocess.run(['git', 'push'], check=True)
            log(f"Committed and pushed {wd}")
            return True
        else:
            log("No changes to commit (already pushed earlier)")
            return False
    except Exception as e:
        log(f"Git error: {e}")
        return False


def generate_index_html():
    """生成索引页"""
    lessons = []
    for f in sorted(os.listdir(HTML_DIR)):
        if f.endswith('.html') and re.match(r'W\d+D\d+\.html', f):
            lessons.append(f.replace('.html', ''))

    items = ''
    for wd in sorted(lessons):
        m = re.match(r'W(\d+)D(\d+)', wd)
        w, d = int(m.group(1)), int(m.group(2))
        items += f'<li><a href="{wd}.html">第{w}周 第{d}天</a></li>\n'

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AI 学习之旅</title>
<style>
body{{font-family:-apple-system,"PingFang SC",sans-serif;max-width:640px;margin:40px auto;padding:20px;background:#fafaf9;color:#1c1917}}
h1{{font-size:28px}}li{{margin:14px 0}}a{{color:#2563eb;font-size:18px;text-decoration:none}}
a:hover{{text-decoration:underline}}p{{color:#57534e}}
@media(prefers-color-scheme:dark){{body{{background:#0c0a09;color:#fafaf9}}a{{color:#60a5fa}}p{{color:#a8a29e}}}}
</style>
</head>
<body>
<h1>📚 AI 学习之旅</h1>
<p>每天早 8:00 企微推送 · 地铁 30 分钟学习 · 到公司 10 分钟实操</p>
<ul>{items if items else '<li>内容即将上线...</li>'}</ul>
</body>
</html>"""


def main():
    if not WEBHOOK_URL:
        log("ERROR: WEIXIN_WEBHOOK not set")
        sys.exit(1)

    today = date.today()
    log(f"Running for {today} (weekday={today.weekday()})")

    if today.weekday() >= 5:
        log("Weekend, skipping.")
        return

    learning_day = get_learning_day(today)
    if learning_day == 0:
        log("Not started yet.")
        return

    wd = get_week_and_day(learning_day)
    date_desc = get_date_desc(learning_day)
    log(f"Day {learning_day} → {wd} → {date_desc}")

    content_file = os.path.join(CONTENT_DIR, f"{wd}.md")
    if not os.path.exists(content_file):
        log(f"ERROR: {content_file} not found")
        send_markdown(f"## ⏰ {date_desc} 内容准备中...")
        return

    with open(content_file, "r") as f:
        raw = f.read()

    parts = [p.strip() for p in raw.split('---PART---') if p.strip()]

    # 生成 HTML
    md_for_html = raw.replace('---PART---', '\n\n')
    html_content = markdown_to_html(md_for_html, date_desc, wd)

    os.makedirs(HTML_DIR, exist_ok=True)
    html_path = os.path.join(HTML_DIR, f"{wd}.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    log(f"HTML: {len(html_content)} bytes")

    # 更新索引页
    index_path = os.path.join(HTML_DIR, "index.html")
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(generate_index_html())

    # 提交到仓库（best-effort，网络不通时跳过）
    commit_and_push(wd)

    # 发送企微摘要（含链接）
    html_url = f"{PAGES_URL}/html/{wd}.html"
    summary = build_summary(parts, date_desc, html_url)
    send_markdown(summary)
    log(f"Done! URL: {html_url}")


if __name__ == "__main__":
    main()
