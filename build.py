#!/usr/bin/env python3
"""
静态站点构建脚本
================
扫描 posts/ 目录下的 .md 文件，转换为 HTML 并生成索引页。
输出到 _site/ 目录，直接部署到 GitHub Pages。

用法：
    python build.py              # 构建站点
    python build.py --serve      # 构建并启动本地预览（localhost:8000）

Markdown 文件头部可添加 YAML 风格的 frontmatter：
    ---
    title: 第一章 风起云涌
    date: 2025-06-01
    category: novel
    description: 少年陈昭踏雪远行，江湖的序幕就此拉开……
    ---
"""

import json
import os
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from markdown_parser import MarkdownParser

# ══════════════════════════════════════════════════════
#  配置
# ══════════════════════════════════════════════════════

ROOT       = Path(__file__).parent
POSTS_DIR  = ROOT / 'posts'
ASSETS_DIR = ROOT / 'assets'
OUTPUT_DIR = ROOT / '_site'
CONFIG_FILE= ROOT / 'site.config.json'


def load_config() -> Dict[str, Any]:
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        "site_name": "我的书斋",
        "subtitle": "",
        "author": "",
        "description": "",
        "base_url": "",
        "footer_text": "",
        "categories": {}
    }


# ══════════════════════════════════════════════════════
#  Frontmatter 解析
# ══════════════════════════════════════════════════════

def parse_frontmatter(text: str) -> tuple:
    """从 Markdown 文本中提取 frontmatter 元信息和正文"""
    meta = {}
    body = text

    m = re.match(r'^---\s*\n(.*?)\n---\s*\n', text, re.DOTALL)
    if m:
        for line in m.group(1).strip().split('\n'):
            if ':' in line:
                key, val = line.split(':', 1)
                meta[key.strip().lower()] = val.strip()
        body = text[m.end():]

    return meta, body


def extract_title_from_body(md_body: str) -> str:
    """从正文中提取第一个 # 标题作为 fallback"""
    m = re.search(r'^#\s+(.+)$', md_body, re.MULTILINE)
    return m.group(1).strip() if m else ''


def extract_description(md_body: str, max_len: int = 120) -> str:
    """从正文中提取第一个段落文本作为摘要"""
    for line in md_body.split('\n'):
        line = line.strip()
        if not line:
            continue
        if line.startswith(('#', '>', '```', '|', '-', '*', '!')):
            continue
        if re.match(r'^\d+\.', line):
            continue
        # 去除行内标记
        clean = re.sub(r'[*_~`\[\]()]', '', line)
        if len(clean) > max_len:
            clean = clean[:max_len] + '……'
        return clean
    return ''


# ══════════════════════════════════════════════════════
#  文章数据收集
# ══════════════════════════════════════════════════════

def collect_posts(config: dict) -> List[Dict]:
    """扫描 posts/ 目录，收集所有 .md 文件的元信息"""
    posts = []
    if not POSTS_DIR.exists():
        return posts

    for md_file in sorted(POSTS_DIR.rglob('*.md')):
        with open(md_file, 'r', encoding='utf-8') as f:
            raw = f.read()

        meta, body = parse_frontmatter(raw)

        # 相对路径（保留子目录结构）
        rel = md_file.relative_to(POSTS_DIR)
        html_name = rel.with_suffix('.html')

        title = meta.get('title') or extract_title_from_body(body) or rel.stem
        date_str = meta.get('date', '')
        category = meta.get('category', 'other')
        description = meta.get('description') or extract_description(body)

        # 尝试解析日期
        date_obj = None
        if date_str:
            for fmt in ('%Y-%m-%d', '%Y/%m/%d', '%Y.%m.%d', '%Y-%m-%d %H:%M'):
                try:
                    date_obj = datetime.strptime(date_str, fmt)
                    break
                except ValueError:
                    pass

        # 如果没写日期，取文件修改时间
        if not date_obj:
            mtime = md_file.stat().st_mtime
            date_obj = datetime.fromtimestamp(mtime)

        posts.append({
            'source': md_file,
            'rel_path': str(rel),
            'html_path': str(html_name),
            'title': title,
            'date': date_obj,
            'date_str': date_obj.strftime('%Y-%m-%d'),
            'category': category,
            'category_label': config.get('categories', {}).get(category, category),
            'description': description,
            'body': body,
        })

    # 按日期降序
    posts.sort(key=lambda p: p['date'], reverse=True)
    return posts


# ══════════════════════════════════════════════════════
#  HTML 模板
# ══════════════════════════════════════════════════════

def post_template(title: str, toc: str, body: str, config: dict,
                  date_str: str = '', category_label: str = '') -> str:
    """生成单篇文章页面 HTML"""
    site_name = config.get('site_name', '')
    base_url = config.get('base_url', '')
    breadcrumb = f'{date_str}' + (f' · {category_label}' if category_label else '')

    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0,user-scalable=yes">
<title>{title} - {site_name}</title>
<link rel="stylesheet" href="{base_url}/assets/style.css">
</head>
<body class="font-m">
<div class="progress-bar" id="progressBar"></div>

<div class="toolbar" id="toolbar">
  <div class="toolbar-left">
    <a href="{base_url}/" class="toolbar-home" title="返回首页">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18"><path d="M3 12l9-9 9 9"/><path d="M5 10v10a1 1 0 001 1h3m10-11v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001 1h4a1 1 0 001-1v-5a1 1 0 00-1-1h-4a1 1 0 00-1 1z"/></svg>
    </a>
    <span class="toolbar-title">{title}</span>
  </div>
  <div class="toolbar-actions">
    <button class="toolbar-btn" id="tocToggle" title="目录">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 12h18M3 6h18M3 18h18"/></svg>
      <span>目录</span>
    </button>
    <button class="toolbar-btn" id="fontBtn" title="字号">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 20h6M7 20V4M14 20l3-12 3 12M15.5 16h5"/></svg>
      <span class="font-label">中</span>
    </button>
    <button class="toolbar-btn" id="themeToggle" title="主题">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>
      <span id="themeLabel">夜间</span>
    </button>
  </div>
</div>

<div class="toc-overlay" id="tocOverlay"></div>
<div class="toc-panel" id="tocPanel">
  <div class="toc-header"><h3>目 录</h3><button class="toc-close" id="tocClose">&times;</button></div>
  <div class="toc-body">{toc}</div>
</div>

<div class="content-wrapper">
  <div class="post-meta">{breadcrumb}</div>
{body}
</div>

<button class="back-to-top" id="backToTop" title="回到顶部">&#8593;</button>
<script src="{base_url}/assets/reader.js"></script>
</body>
</html>'''


def index_template(posts: List[Dict], config: dict) -> str:
    """生成首页 HTML"""
    site_name   = config.get('site_name', '我的书斋')
    subtitle    = config.get('subtitle', '')
    description = config.get('description', '')
    footer_text = config.get('footer_text', '')
    base_url    = config.get('base_url', '')
    categories  = config.get('categories', {})

    # 构建分类标签
    used_cats = sorted(set(p['category'] for p in posts))
    cat_buttons = ['<button class="cat-btn active" data-cat="all">全部</button>']
    for cat in used_cats:
        label = categories.get(cat, cat)
        cat_buttons.append(f'<button class="cat-btn" data-cat="{cat}">{label}</button>')

    # 构建文章卡片
    cards = []
    for p in posts:
        cards.append(f'''
    <article class="post-card" data-category="{p['category']}">
      <a href="{base_url}/{p['html_path']}">
        <div class="card-meta">
          <span class="card-date">{p['date_str']}</span>
          <span class="card-cat">{p['category_label']}</span>
        </div>
        <h3 class="card-title">{p['title']}</h3>
        <p class="card-desc">{p['description']}</p>
      </a>
    </article>''')

    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{site_name}</title>
<meta name="description" content="{description}">
<link rel="stylesheet" href="{base_url}/assets/style.css">
<link rel="stylesheet" href="{base_url}/assets/index.css">
</head>
<body>

<header class="site-header">
  <div class="header-inner">
    <h1 class="site-title">{site_name}</h1>
    {f'<p class="site-subtitle">{subtitle}</p>' if subtitle else ''}
    {f'<p class="site-desc">{description}</p>' if description else ''}
    <button class="toolbar-btn theme-btn-index" id="themeToggle" title="切换主题">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18">
        <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>
    </button>
  </div>
</header>

<main class="index-main">
  <nav class="cat-filter">
    {''.join(cat_buttons)}
  </nav>

  <div class="post-grid">
    {''.join(cards)}
  </div>

  <p class="post-count"><span id="countNum">{len(posts)}</span> 篇文稿</p>
</main>

<footer class="site-footer">
  {f'<p>{footer_text}</p>' if footer_text else ''}
  <p class="footer-powered">Powered by Markdown · Hosted on GitHub Pages</p>
</footer>

<script>
(function(){{
  /* 主题 */
  if(localStorage.getItem('md-theme')==='dark') document.documentElement.setAttribute('data-theme','dark');
  document.getElementById('themeToggle').onclick=function(){{
    var d=document.documentElement.getAttribute('data-theme')==='dark';
    document.documentElement.setAttribute('data-theme',d?'':'dark');
    localStorage.setItem('md-theme',d?'light':'dark');
  }};
  /* 分类筛选 */
  var btns=document.querySelectorAll('.cat-btn');
  var cards=document.querySelectorAll('.post-card');
  var countEl=document.getElementById('countNum');
  btns.forEach(function(b){{
    b.onclick=function(){{
      btns.forEach(function(x){{x.classList.remove('active')}});
      b.classList.add('active');
      var cat=b.dataset.cat, n=0;
      cards.forEach(function(c){{
        var show=(cat==='all'||c.dataset.category===cat);
        c.style.display=show?'':'none';
        if(show) n++;
      }});
      countEl.textContent=n;
    }};
  }});
}})();
</script>
</body>
</html>'''


# ══════════════════════════════════════════════════════
#  CSS / JS 资源文件
# ══════════════════════════════════════════════════════

SHARED_CSS = r'''/* ═══════ 共享主题变量 & 基础排版 ═══════ */
@import url('https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;600;700&family=ZCOOL+XiaoWei&display=swap');

:root {
  --bg-primary:#faf7f2; --bg-secondary:#f0ebe2; --bg-card:#fffdf9;
  --text-primary:#2c2418; --text-secondary:#6b5d4f; --text-muted:#9c8e7e;
  --accent:#8b5e3c; --accent-light:#c9956b;
  --border:#e6ddd0; --border-light:#efe8dd;
  --shadow-sm:0 1px 3px rgba(80,50,20,.06);
  --shadow-md:0 4px 16px rgba(80,50,20,.08);
  --shadow-lg:0 8px 32px rgba(80,50,20,.10);
  --quote-bg:#f7f1e8; --quote-border:#d4b896;
  --code-bg:#f5f0e8; --code-block-bg:#2b2520; --code-block-fg:#e8dcc8;
  --hr-color:#ddd0be; --link-color:#7a4f2c;
  --table-header:#f0e8da; --table-stripe:#faf6f0; --toc-hover:#f0e8da;
  --toolbar-bg:rgba(250,247,242,.92);
  --font-size-base:17px; --content-width:720px; --line-height:1.95; --p-indent:2em;
}
[data-theme="dark"] {
  --bg-primary:#1a1714; --bg-secondary:#231f1b; --bg-card:#252120;
  --text-primary:#d9ccbb; --text-secondary:#a89882; --text-muted:#7a6e5f;
  --accent:#c9956b; --accent-light:#daa87e;
  --border:#3a3430; --border-light:#302a26;
  --shadow-sm:0 1px 3px rgba(0,0,0,.2);
  --shadow-md:0 4px 16px rgba(0,0,0,.25);
  --shadow-lg:0 8px 32px rgba(0,0,0,.3);
  --quote-bg:#2a2420; --quote-border:#6b553e;
  --code-bg:#2a2520; --code-block-bg:#141210; --code-block-fg:#d4c8b4;
  --hr-color:#3a3430; --link-color:#daa87e;
  --table-header:#2e2924; --table-stripe:#221e1a; --toc-hover:#302a24;
  --toolbar-bg:rgba(26,23,20,.92);
}

*,*::before,*::after{box-sizing:border-box}
html{scroll-behavior:smooth;scroll-padding-top:80px}
body{
  font-family:"Noto Serif SC","Songti SC","SimSun","Source Han Serif CN",serif;
  font-size:var(--font-size-base); line-height:var(--line-height);
  color:var(--text-primary); background:var(--bg-primary);
  margin:0;padding:0; transition:background .4s,color .4s;
  text-rendering:optimizeLegibility; -webkit-font-smoothing:antialiased;
}
::selection{background:var(--accent);color:#fff}

/* ═══════ 工具栏 ═══════ */
.toolbar{
  position:fixed;top:0;left:0;right:0;z-index:1000;
  background:var(--toolbar-bg); backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px);
  border-bottom:1px solid var(--border-light); padding:10px 20px;
  display:flex;align-items:center;justify-content:space-between;gap:12px;
  transition:transform .3s,background .4s;
}
.toolbar-left{display:flex;align-items:center;gap:10px;min-width:0;flex:1}
.toolbar-home{
  color:var(--text-secondary);display:flex;align-items:center;
  text-decoration:none;border:none;flex-shrink:0;transition:color .2s;
}
.toolbar-home:hover{color:var(--accent)}
.toolbar-title{
  font-family:"ZCOOL XiaoWei","Noto Serif SC",serif;
  font-size:15px;color:var(--text-secondary);
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis;letter-spacing:1px;
}
.toolbar-actions{display:flex;gap:6px;flex-shrink:0}
.toolbar-btn{
  background:none;border:1px solid var(--border);color:var(--text-secondary);
  border-radius:8px;padding:6px 12px;cursor:pointer;font-size:13px;font-family:inherit;
  transition:all .2s;white-space:nowrap;display:flex;align-items:center;gap:4px;
}
.toolbar-btn:hover{background:var(--bg-secondary);color:var(--text-primary);border-color:var(--accent-light)}
.toolbar-btn:active{transform:scale(.96)}
.toolbar-btn svg{width:16px;height:16px;flex-shrink:0}
.font-label{display:inline-block;min-width:18px;text-align:center;font-size:11px;color:var(--accent);font-weight:600}

/* ═══════ 文章 meta ═══════ */
.post-meta{
  text-align:center;color:var(--text-muted);font-size:.9em;
  margin-bottom:1.5em;letter-spacing:.5px;
}

/* ═══════ 目录侧栏 ═══════ */
.toc-overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.3);z-index:1500}
.toc-overlay.visible{display:block}
.toc-panel{
  position:fixed;top:0;left:-320px;width:300px;max-width:80vw;height:100vh;
  background:var(--bg-card);z-index:2000;
  transition:left .35s cubic-bezier(.4,0,.2,1),background .4s;
  box-shadow:var(--shadow-lg);display:flex;flex-direction:column;
}
.toc-panel.open{left:0}
.toc-header{padding:20px 24px 16px;border-bottom:1px solid var(--border-light);display:flex;justify-content:space-between;align-items:center}
.toc-header h3{margin:0;font-family:"ZCOOL XiaoWei","Noto Serif SC",serif;font-size:18px;letter-spacing:2px}
.toc-close{background:none;border:none;font-size:22px;cursor:pointer;color:var(--text-muted);padding:4px;line-height:1}
.toc-body{flex:1;overflow-y:auto;padding:12px 0;overscroll-behavior:contain}
.toc-list{list-style:none;margin:0;padding:0}
.toc-list li a{
  display:block;padding:9px 24px;color:var(--text-secondary);text-decoration:none;
  font-size:14px;line-height:1.5;transition:all .15s;border-left:3px solid transparent;
}
.toc-list li a:hover{background:var(--toc-hover);color:var(--accent);border-left-color:var(--accent)}
.toc-h1 a{font-weight:700;font-size:15px;padding-left:24px!important}
.toc-h2 a{padding-left:38px!important}
.toc-h3 a{padding-left:52px!important;font-size:13px}
.toc-h4 a{padding-left:66px!important;font-size:13px;color:var(--text-muted)}

/* ═══════ 内容区 ═══════ */
.content-wrapper{max-width:var(--content-width);margin:0 auto;padding:80px 28px 120px}

h1,h2,h3,h4,h5,h6{font-family:"ZCOOL XiaoWei","Noto Serif SC",serif;color:var(--text-primary);line-height:1.4;margin-bottom:.6em}
h1{font-size:1.9em;margin-top:2em;padding-bottom:.4em;border-bottom:2px solid var(--accent);letter-spacing:3px;text-align:center}
h1::after{content:'';display:block;width:60px;height:2px;background:var(--accent-light);margin:12px auto 0;border-radius:1px}
h2{font-size:1.5em;margin-top:2.2em;padding-bottom:.3em;border-bottom:1px solid var(--border);letter-spacing:2px;position:relative;padding-left:16px}
h2::before{content:'';position:absolute;left:0;top:.2em;bottom:.5em;width:4px;background:var(--accent);border-radius:2px}
h3{font-size:1.25em;margin-top:1.8em;letter-spacing:1px;color:var(--accent)}
h4{font-size:1.1em;margin-top:1.5em;color:var(--text-secondary)}
h5,h6{font-size:1em;margin-top:1.3em;color:var(--text-secondary)}

p{text-indent:var(--p-indent);margin:.9em 0;text-align:justify;word-break:break-all}
h1+p,h2+p,h3+p,h4+p,h5+p,h6+p{text-indent:0}

strong{color:var(--text-primary);font-weight:700}
em{font-style:normal;text-emphasis:filled circle;text-emphasis-position:under left;-webkit-text-emphasis:filled circle;-webkit-text-emphasis-position:under left}
del{color:var(--text-muted);text-decoration:line-through}
a{color:var(--link-color);text-decoration:none;border-bottom:1px dashed var(--link-color);transition:all .2s}
a:hover{color:var(--accent-light);border-bottom-style:solid}
img{max-width:100%;height:auto;border-radius:6px;display:block;margin:1.5em auto;box-shadow:var(--shadow-md)}

blockquote{margin:1.5em 0;padding:18px 24px;background:var(--quote-bg);border-left:4px solid var(--quote-border);border-radius:0 8px 8px 0;color:var(--text-secondary);position:relative}
blockquote::before{content:'\201C';font-family:Georgia,serif;position:absolute;top:-8px;left:12px;font-size:48px;color:var(--quote-border);opacity:.4;line-height:1}
blockquote p{text-indent:0;margin:.4em 0}

ul,ol{margin:1em 0;padding-left:2em}
li{margin:.4em 0;line-height:var(--line-height)}
li::marker{color:var(--accent)}

code{font-family:"Fira Code","Source Code Pro",Menlo,monospace;background:var(--code-bg);padding:2px 7px;border-radius:4px;font-size:.88em;color:var(--accent);border:1px solid var(--border-light)}
pre{background:var(--code-block-bg);color:var(--code-block-fg);padding:20px 24px;border-radius:10px;overflow-x:auto;margin:1.5em 0;box-shadow:var(--shadow-md);line-height:1.6;-webkit-overflow-scrolling:touch}
pre code{background:none;border:none;padding:0;color:inherit;font-size:.9em}

table{width:100%;border-collapse:collapse;margin:1.5em 0;font-size:.95em;border-radius:8px;overflow:hidden;box-shadow:var(--shadow-sm)}
thead{background:var(--table-header)}
th{font-weight:600;padding:12px 16px;border-bottom:2px solid var(--border);letter-spacing:.5px}
td{padding:10px 16px;border-bottom:1px solid var(--border-light)}
tbody tr:nth-child(even){background:var(--table-stripe)}
tbody tr:hover{background:var(--toc-hover)}

hr{border:none;margin:3em auto;text-align:center;overflow:visible}
hr::before{content:'\2666\2009\2666\2009\2666';display:block;color:var(--hr-color);font-size:14px;letter-spacing:8px}

.back-to-top{position:fixed;bottom:30px;right:24px;width:44px;height:44px;border-radius:50%;background:var(--accent);color:#fff;border:none;cursor:pointer;font-size:20px;display:flex;align-items:center;justify-content:center;box-shadow:var(--shadow-md);opacity:0;visibility:hidden;transform:translateY(10px);transition:all .3s;z-index:500}
.back-to-top.visible{opacity:1;visibility:visible;transform:translateY(0)}
.back-to-top:hover{transform:translateY(-2px);box-shadow:var(--shadow-lg)}
.progress-bar{position:fixed;top:0;left:0;height:3px;background:linear-gradient(to right,var(--accent),var(--accent-light));z-index:3000;transition:width .1s linear;border-radius:0 2px 2px 0}

body.font-s{--font-size-base:15px;--line-height:1.85}
body.font-m{--font-size-base:17px;--line-height:1.95}
body.font-l{--font-size-base:19px;--line-height:2.05}
body.font-xl{--font-size-base:21px;--line-height:2.15}

@media(max-width:768px){
  :root{--content-width:100%;--font-size-base:16px}
  .toolbar-title{display:none}
  h1{font-size:1.6em;letter-spacing:2px} h2{font-size:1.3em}
  blockquote{padding:14px 18px;margin-left:0;margin-right:0}
  table{display:block;overflow-x:auto;-webkit-overflow-scrolling:touch}
  pre{padding:14px 16px;border-radius:8px}
  .content-wrapper{padding:70px 20px 100px}
}
@media(max-width:380px){.toolbar-actions{gap:4px}.toolbar-btn span{display:none}}
@media print{
  .toolbar,.toc-panel,.toc-overlay,.back-to-top,.progress-bar{display:none!important}
  body{background:#fff;color:#000;font-size:12pt}
  .content-wrapper{max-width:100%;padding:0}
  a{color:#000;border-bottom:none} pre{box-shadow:none;border:1px solid #ccc}
}
'''

INDEX_CSS = r'''/* ═══════ 首页样式 ═══════ */
.site-header{
  text-align:center; padding:60px 20px 40px;
  background:var(--bg-secondary); border-bottom:1px solid var(--border);
  position:relative;
}
.header-inner{max-width:600px;margin:0 auto}
.site-title{
  font-family:"ZCOOL XiaoWei","Noto Serif SC",serif;
  font-size:2.2em; margin:0 0 .3em; letter-spacing:4px;
  color:var(--text-primary);
}
.site-subtitle{
  font-size:1.05em; color:var(--accent); margin:.2em 0;
  letter-spacing:2px; font-family:"ZCOOL XiaoWei",serif;
}
.site-desc{font-size:.92em;color:var(--text-muted);margin:.8em 0 0;line-height:1.6}

.theme-btn-index{
  position:absolute; top:20px; right:20px;
  border-radius:50%; width:40px; height:40px;
  padding:0; display:flex; align-items:center; justify-content:center;
}

.index-main{max-width:820px;margin:0 auto;padding:30px 24px 60px}

/* 分类筛选 */
.cat-filter{
  display:flex; flex-wrap:wrap; gap:8px;
  justify-content:center; margin-bottom:30px;
}
.cat-btn{
  background:none; border:1px solid var(--border);
  color:var(--text-secondary); padding:6px 16px;
  border-radius:20px; cursor:pointer; font-size:14px;
  font-family:"Noto Serif SC",serif;
  transition:all .2s; letter-spacing:.5px;
}
.cat-btn:hover{border-color:var(--accent-light);color:var(--accent)}
.cat-btn.active{background:var(--accent);color:#fff;border-color:var(--accent)}

/* 文章卡片 */
.post-grid{display:flex;flex-direction:column;gap:1px}

.post-card a{
  display:block; padding:22px 24px;
  text-decoration:none; color:inherit;
  border-bottom:1px solid var(--border-light);
  transition:background .2s;
}
.post-card a:hover{background:var(--bg-secondary)}

.card-meta{
  display:flex; gap:12px; align-items:center;
  margin-bottom:6px; font-size:.82em;
}
.card-date{color:var(--text-muted)}
.card-cat{
  color:var(--accent); background:var(--bg-secondary);
  padding:2px 10px; border-radius:10px; font-size:.85em;
}
.card-title{
  margin:0 0 6px; font-size:1.15em;
  font-family:"ZCOOL XiaoWei","Noto Serif SC",serif;
  letter-spacing:1px; color:var(--text-primary);
}
.card-desc{margin:0;font-size:.9em;color:var(--text-muted);line-height:1.6}

.post-count{text-align:center;color:var(--text-muted);font-size:.85em;margin-top:30px}

/* 页脚 */
.site-footer{
  text-align:center; padding:30px 20px;
  border-top:1px solid var(--border-light);
  color:var(--text-muted); font-size:.85em;
}
.site-footer p{margin:.4em 0}
.footer-powered{font-size:.8em;opacity:.6}

@media(max-width:768px){
  .site-header{padding:40px 16px 30px}
  .site-title{font-size:1.7em;letter-spacing:3px}
  .index-main{padding:20px 16px 50px}
  .post-card a{padding:18px 16px}
  .theme-btn-index{top:14px;right:14px;width:36px;height:36px}
}
'''

READER_JS = r'''(function(){
  /* 主题 */
  var tl=document.getElementById('themeLabel'),fl=document.querySelector('.font-label');
  if(localStorage.getItem('md-theme')==='dark'){
    document.documentElement.setAttribute('data-theme','dark');
    if(tl)tl.textContent='日间';
  }
  var tb=document.getElementById('themeToggle');
  if(tb) tb.onclick=function(){
    var d=document.documentElement.getAttribute('data-theme')==='dark';
    document.documentElement.setAttribute('data-theme',d?'':'dark');
    localStorage.setItem('md-theme',d?'light':'dark');
    if(tl)tl.textContent=d?'夜间':'日间';
  };
  /* 字号 */
  var sizes=['font-s','font-m','font-l','font-xl'],labels=['小','中','大','特大'];
  var fi=parseInt(localStorage.getItem('md-font-idx')||'1');
  document.body.className=sizes[fi];
  if(fl)fl.textContent=labels[fi];
  var fb=document.getElementById('fontBtn');
  if(fb) fb.onclick=function(){
    fi=(fi+1)%sizes.length;
    document.body.className=sizes[fi];
    localStorage.setItem('md-font-idx',fi);
    if(fl)fl.textContent=labels[fi];
  };
  /* 目录 */
  var tp=document.getElementById('tocPanel'),to=document.getElementById('tocOverlay');
  if(tp&&to){
    function openToc(){tp.classList.add('open');to.classList.add('visible')}
    function closeToc(){tp.classList.remove('open');to.classList.remove('visible')}
    var tt=document.getElementById('tocToggle');if(tt)tt.onclick=openToc;
    var tc=document.getElementById('tocClose');if(tc)tc.onclick=closeToc;
    to.onclick=closeToc;
    tp.querySelectorAll('a').forEach(function(a){a.onclick=function(){setTimeout(closeToc,150)}});
  }
  /* 进度 + 回顶 + 工具栏隐藏 */
  var pb=document.getElementById('progressBar'),bb=document.getElementById('backToTop'),bar=document.getElementById('toolbar'),ls=0;
  window.addEventListener('scroll',function(){
    if(pb){var st=window.scrollY,dh=document.documentElement.scrollHeight-window.innerHeight;pb.style.width=(dh>0?st/dh*100:0)+'%'}
    if(bb)bb.classList.toggle('visible',window.scrollY>400);
    if(bar&&window.innerWidth<=768){var cs=window.scrollY;bar.style.transform=(cs>ls&&cs>200)?'translateY(-100%)':'translateY(0)';ls=cs}
  },{passive:true});
  if(bb)bb.onclick=function(){window.scrollTo({top:0,behavior:'smooth'})};
})();
'''


# ══════════════════════════════════════════════════════
#  构建流程
# ══════════════════════════════════════════════════════

def build():
    config = load_config()
    print(f'📖 站点: {config.get("site_name", "")}')

    # 清理输出目录
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True)

    # 写入资源文件
    assets_out = OUTPUT_DIR / 'assets'
    assets_out.mkdir()
    (assets_out / 'style.css').write_text(SHARED_CSS, encoding='utf-8')
    (assets_out / 'index.css').write_text(INDEX_CSS, encoding='utf-8')
    (assets_out / 'reader.js').write_text(READER_JS, encoding='utf-8')
    print(f'  ✅ 资源文件已写入 _site/assets/')

    # 复制用户自定义资源（图片等）
    if ASSETS_DIR.exists():
        for f in ASSETS_DIR.rglob('*'):
            if f.is_file():
                dest = assets_out / f.relative_to(ASSETS_DIR)
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, dest)
        print(f'  ✅ 用户资源已复制')

    # 收集文章
    posts = collect_posts(config)
    print(f'  📝 找到 {len(posts)} 篇文章')

    # 转换每篇文章
    for p in posts:
        parser = MarkdownParser()
        body = parser.parse(p['body'])
        toc = parser.generate_toc()

        html = post_template(
            title=p['title'],
            toc=toc,
            body=body,
            config=config,
            date_str=p['date_str'],
            category_label=p['category_label'],
        )

        out_path = OUTPUT_DIR / p['html_path']
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(html, encoding='utf-8')
        print(f'     → {p["html_path"]}')

    # 生成首页
    index_html = index_template(posts, config)
    (OUTPUT_DIR / 'index.html').write_text(index_html, encoding='utf-8')
    print(f'  ✅ index.html 已生成')

    # 生成 .nojekyll（告诉 GitHub Pages 不要用 Jekyll 处理）
    (OUTPUT_DIR / '.nojekyll').write_text('', encoding='utf-8')

    print(f'\n🎉 构建完成！输出目录: _site/')
    print(f'   共 {len(posts)} 篇文章，可直接部署到 GitHub Pages')


def serve():
    """启动本地预览服务器"""
    import http.server
    import functools

    build()
    os.chdir(OUTPUT_DIR)
    port = 8000
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(OUTPUT_DIR))
    with http.server.HTTPServer(('', port), handler) as httpd:
        print(f'\n🌐 本地预览: http://localhost:{port}')
        print('   按 Ctrl+C 停止')
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print('\n已停止')


if __name__ == '__main__':
    if '--serve' in sys.argv:
        serve()
    else:
        build()
