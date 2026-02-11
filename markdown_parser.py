"""
Markdown → HTML 解析器（中文阅读优化版）
用法：作为模块被 build.py 导入
"""

import re
from typing import List, Tuple


class MarkdownParser:

    INLINE_RULES = [
        (re.compile(r'!\[([^\]]*)\]\(([^)]+)\)'),      r'<img src="\2" alt="\1">'),
        (re.compile(r'\[([^\]]+)\]\(([^)]+)\)'),        r'<a href="\2">\1</a>'),
        (re.compile(r'`([^`]+)`'),                      r'<code>\1</code>'),
        (re.compile(r'\*{3}(.+?)\*{3}'),                r'<strong><em>\1</em></strong>'),
        (re.compile(r'_{3}(.+?)_{3}'),                  r'<strong><em>\1</em></strong>'),
        (re.compile(r'\*{2}(.+?)\*{2}'),                r'<strong>\1</strong>'),
        (re.compile(r'_{2}(.+?)_{2}'),                  r'<strong>\1</strong>'),
        (re.compile(r'\*(.+?)\*'),                      r'<em>\1</em>'),
        (re.compile(r'(?<![a-zA-Z0-9])_(.+?)_(?![a-zA-Z0-9])'), r'<em>\1</em>'),
        (re.compile(r'~~(.+?)~~'),                      r'<del>\1</del>'),
    ]

    def __init__(self):
        self.headings: List[Tuple[int, str, str]] = []

    def parse_inline(self, text: str) -> str:
        for pattern, repl in self.INLINE_RULES:
            text = pattern.sub(repl, text)
        return text

    def parse(self, markdown: str) -> str:
        markdown = markdown.replace('\r\n', '\n').replace('\r', '\n')
        lines = markdown.split('\n')
        html_parts: List[str] = []
        i = 0
        self.headings = []

        while i < len(lines):
            line = lines[i]
            if line.strip() == '':
                i += 1
                continue
            if line.strip().startswith('```'):
                h, i = self._code_block(lines, i)
                html_parts.append(h); continue
            m = re.match(r'^(#{1,6})\s+(.+)$', line)
            if m:
                lv = len(m.group(1)); raw = m.group(2).strip()
                content = self.parse_inline(raw)
                slug = re.sub(r'[^\w\u4e00-\u9fff-]', '', raw).lower() or f'h-{len(self.headings)}'
                base = slug; c = 1; ids = {h[1] for h in self.headings}
                while slug in ids: slug = f'{base}-{c}'; c += 1
                self.headings.append((lv, slug, raw))
                html_parts.append(f'<h{lv} id="{slug}">{content}</h{lv}>')
                i += 1; continue
            if re.match(r'^(\s*[-*_]\s*){3,}$', line):
                html_parts.append('<hr>'); i += 1; continue
            if line.strip().startswith('>'):
                h, i = self._blockquote(lines, i)
                html_parts.append(h); continue
            if re.match(r'^(\s*)([-*+])\s+', line):
                h, i = self._ul(lines, i)
                html_parts.append(h); continue
            if re.match(r'^(\s*)\d+\.\s+', line):
                h, i = self._ol(lines, i)
                html_parts.append(h); continue
            if '|' in line and i+1 < len(lines) and re.match(r'^[\s|:-]+$', lines[i+1]):
                h, i = self._table(lines, i)
                html_parts.append(h); continue
            h, i = self._paragraph(lines, i)
            html_parts.append(h)

        return '\n'.join(html_parts)

    # ── block parsers ──

    def _code_block(self, lines, s):
        lang = lines[s].strip()[3:].strip()
        attr = f' class="language-{lang}"' if lang else ''
        i, out = s+1, []
        while i < len(lines):
            if lines[i].strip() == '```': i += 1; break
            out.append(self._esc(lines[i])); i += 1
        return f'<pre><code{attr}>{chr(10).join(out)}</code></pre>', i

    def _blockquote(self, lines, s):
        i, ql = s, []
        while i < len(lines) and lines[i].strip().startswith('>'):
            ql.append(re.sub(r'^>\s?', '', lines[i])); i += 1
        inner = MarkdownParser().parse('\n'.join(ql))
        return f'<blockquote>\n{inner}\n</blockquote>', i

    def _ul(self, lines, s):
        i, items = s, []
        while i < len(lines) and re.match(r'^(\s*)([-*+])\s+', lines[i]):
            items.append(self.parse_inline(re.sub(r'^(\s*)([-*+])\s+', '', lines[i]))); i += 1
        li = '\n'.join(f'  <li>{x}</li>' for x in items)
        return f'<ul>\n{li}\n</ul>', i

    def _ol(self, lines, s):
        i, items = s, []
        while i < len(lines) and re.match(r'^(\s*)\d+\.\s+', lines[i]):
            items.append(self.parse_inline(re.sub(r'^(\s*)\d+\.\s+', '', lines[i]))); i += 1
        li = '\n'.join(f'  <li>{x}</li>' for x in items)
        return f'<ol>\n{li}\n</ol>', i

    def _table(self, lines, s):
        def sr(l): return [c.strip() for c in l.strip().strip('|').split('|')]
        def al(l):
            return ['center' if c.strip().startswith(':') and c.strip().endswith(':')
                    else 'right' if c.strip().endswith(':') else 'left' for c in sr(l)]
        hdr, aligns = sr(lines[s]), al(lines[s+1])
        i = s+2
        ths = '\n'.join(f'      <th style="text-align:{aligns[j] if j<len(aligns) else "left"}">'
                        f'{self.parse_inline(h)}</th>' for j,h in enumerate(hdr))
        rows = []
        while i < len(lines) and '|' in lines[i] and lines[i].strip():
            cells = sr(lines[i])
            tds = '\n'.join(f'      <td style="text-align:{aligns[j] if j<len(aligns) else "left"}">'
                           f'{self.parse_inline(c)}</td>' for j,c in enumerate(cells))
            rows.append(f'    <tr>\n{tds}\n    </tr>'); i += 1
        return (f'<table>\n  <thead>\n    <tr>\n{ths}\n    </tr>\n  </thead>\n'
                f'  <tbody>\n{chr(10).join(rows)}\n  </tbody>\n</table>'), i

    def _paragraph(self, lines, s):
        i, pl = s, []
        while i < len(lines) and lines[i].strip():
            if (lines[i].strip().startswith(('#','>','```')) or
                re.match(r'^(\s*)([-*+])\s+', lines[i]) or
                re.match(r'^(\s*)\d+\.\s+', lines[i]) or
                re.match(r'^(\s*[-*_]\s*){3,}$', lines[i])): break
            pl.append(lines[i]); i += 1
        return f'<p>{self.parse_inline(" ".join(pl))}</p>', i

    @staticmethod
    def _esc(t):
        return t.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;').replace('"','&quot;')

    def generate_toc(self) -> str:
        if not self.headings: return ''
        items = []
        for lv, slug, text in self.headings:
            items.append(f'{"  "*(lv-1)}<li class="toc-h{lv}"><a href="#{slug}">{text}</a></li>')
        return '<ul class="toc-list">\n' + '\n'.join(items) + '\n</ul>'
