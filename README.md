# 📖 Markdown 静态书斋

一个极简的静态站点生成器，专为中文小说创作者设计。将 Markdown 文件自动转换为精美的 HTML 页面，通过 GitHub Pages 免费托管。

**零依赖** · **纯 Python** · **自动部署** · **中文排版优化**

## 快速开始

### 1. 创建 GitHub 仓库

在 GitHub 上新建一个仓库（如 `my-novel`），将本项目的所有文件推送上去：

```bash
git init
git add .
git commit -m "初始化书斋"
git branch -M main
git remote add origin https://github.com/你的用户名/my-novel.git
git push -u origin main
```

### 2. 启用 GitHub Pages

进入仓库 → **Settings** → **Pages**：

- **Source** 选择 **GitHub Actions**

完成后，每次 push 到 main 分支都会自动构建并部署。

### 3. 开始写作

在 `posts/` 目录下创建 `.md` 文件。推荐在文件头部添加元信息（frontmatter）：

```markdown
---
title: 第一章 风起云涌
date: 2025-06-15
category: novel
description: 少年陈昭踏雪远行，江湖的序幕就此拉开……
---

# 第一章 风起云涌

正文内容……
```

### 4. 发布

```bash
git add posts/新文章.md
git commit -m "新增：第一章"
git push
```

推送后 GitHub Actions 会在 1-2 分钟内自动构建部署，访问 `https://你的用户名.github.io/my-novel/` 即可查看。

## 项目结构

```
├── posts/                  # 📝 你的 Markdown 文章（放在这里）
│   ├── 01-第一章.md
│   ├── 02-人物小传.md
│   └── ...
├── assets/                 # 🎨 自定义资源（图片等，可选）
├── site.config.json        # ⚙️  站点配置
├── build.py                # 🔧 构建脚本
├── markdown_parser.py      # 📐 Markdown 解析器
├── .github/workflows/
│   └── deploy.yml          # 🚀 自动部署配置
└── _site/                  # 📦 构建输出（自动生成，不要手动修改）
```

## 站点配置

编辑 `site.config.json`：

```json
{
  "site_name": "赤霞书斋",
  "subtitle": "小说创作与笔记",
  "author": "你的名字",
  "description": "个人小说创作空间",
  "base_url": "",
  "footer_text": "纸上得来终觉浅，绝知此事要躬行",
  "categories": {
    "novel":     "小说正文",
    "outline":   "大纲设定",
    "character": "人物小传",
    "world":     "地理设定",
    "notes":     "创作笔记"
  }
}
```

> **关于 base_url**：如果仓库名不是 `你的用户名.github.io`，需要设置为 `/仓库名`，例如 `/my-novel`。如果使用自定义域名或 `用户名.github.io` 仓库，留空即可。

## Frontmatter 字段

| 字段 | 必填 | 说明 |
|:-----|:----:|:-----|
| `title` | 否 | 文章标题。未填则取正文第一个 `#` 标题，再无则用文件名 |
| `date` | 否 | 发布日期（`YYYY-MM-DD`）。未填则用文件修改时间 |
| `category` | 否 | 分类标识，对应 config 中的 categories |
| `description` | 否 | 摘要。未填则自动提取正文首段 |

## 本地预览

```bash
python build.py --serve
```

会在 `localhost:8000` 启动预览服务器。

## 支持的 Markdown 语法

标题（1-6级）、**粗体**、*斜体*、~~删除线~~、`行内代码`、围栏代码块、
[链接](url)、![图片](url)、有序/无序列表、引用块、表格（含对齐）、水平线

## 阅读功能

- 🌙 暗色/亮色主题切换（记忆偏好）
- 🔤 四级字号调节（小/中/大/特大）
- 📑 自动生成侧边目录
- 📊 顶部阅读进度条
- ⬆️ 回到顶部按钮
- 📱 移动端自适应（工具栏自动隐藏）
- 🖨️ 打印优化

## License

MIT
