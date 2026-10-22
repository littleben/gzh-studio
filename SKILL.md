---
name: gzh-studio
description: 微信公众号文章的配图、排版、发布一条龙。把 Markdown 排成可直接进公众号的 HTML（6 套主题、12 种组件：引言卡、本文看点、数据卡片、时间线、表格、提示条、踩坑提示、编号章节等），按「组件都用、但不密集」的标准自动检查；配图优先截真实后台和产品页面（2 倍清晰度、可连已登录的 Chrome），自动生成 2.35:1 封面；一条命令压图、上传、建草稿（支持通过 IP 白名单服务器发布）。凡是要写公众号、排版公众号文章、给公众号配图做封面、把 Markdown 发到公众号草稿箱、公众号文章太朴素或太花，都用这个 skill。
---

# gzh-studio：公众号配图、排版、发布

一篇公众号文章，从 Markdown 到草稿箱：

```
写 Markdown → 配图（真实截图 + 封面）→ 标记组件 → 预览检查密度 → 发布到草稿箱 → 人工预览后群发
```

所有脚本都在 `scripts/`，依赖：Python 3.9+、Pillow；截图和预览截图需要 playwright；调用接口需要 requests。

## 1. 起稿：从模板开始

`templates/` 里有 5 种文章骨架，组件已经按标准放好，注释写着每处放什么：

| 模板 | 适合 | 默认主题 |
|---|---|---|
| `review.md` | 复盘、数据型案例 | latepost 晚点红 |
| `tutorial.md` | 教程、操作指南 | emerald 摸鱼绿 |
| `roundup.md` | 工具盘点、清单 | ocean 科技蓝 |
| `opinion.md` | 观点、分析 | graphite 石墨极简 |
| `launch.md` | 产品发布、新功能 | olive 橄榄手记 |

主题还有 zen 留白禅意（随笔、生活）。在 frontmatter 写 `theme:`，或者发布时加 `--theme` 指定，效果见 `assets/previews/`。

写作规则：只写真实发生的事和能查到来源的数据，不编时间线、不编心理活动；标点用「」，不用英文引号和破折号。

## 2. 配图：能截真实的就不画

读 `references/images.md`。要点：

- 优先截真实页面：数据后台（GA4、公众号后台）、产品界面、仓库页。只有数据库里的数字才画图表。
- `scripts/shot.py` 截 2 倍图。需要登录的后台，连一个已登录的 Chrome（`--cdp`）。
- 截图裁到正文说的那一块；单日数字、无关侧栏要裁掉，免得读者误读。
- 写到网站现状前，先在线上确认，本地代码可能已经过时。
- `scripts/cover.py` 生成 2.35:1 封面，标题 10 个字左右。

## 3. 排版：组件都用，但要分散

写法见 `references/markup.md`，标准见 `references/layout-standard.md`。核心规则：

- 每种组件挑最合适的内容用：开头引言卡 + 本文看点，对比用表格，数字用数据卡片，迭代用时间线，提醒用提示条，补充说明用灰色旁注。
- **一屏最多一个容器组件**，两个容器之间至少隔一句正文；列表项不要每条都加粗。
- 加粗 5～8 处、下划线 4～6 处（每段最多 1 处）、底色高亮 3～4 处、提示条和金句各 1～2 处。

`render.py` 超过这些用量、或者容器紧挨着时会打印 WARN。**WARN 清零再交付。**

## 4. 预览

```bash
python3 scripts/preview.py article.md --shots ./shots     # 390 px 手机截图，逐屏看
```

逐屏检查：有没有一屏全是主色、图片里的字能不能看清、组件有没有挤在一起。预览页右上角的按钮可以把正文复制下来，粘进公众号编辑器。

## 5. 发布到草稿箱

读 `references/publish.md`。

```bash
python3 scripts/publish.py article.md --dry-run                       # 渲染 + 校验 + 压图，不上传
python3 scripts/publish.py article.md --ssh myserver --config cfg.yaml # 通过白名单服务器建草稿
```

- 凭据来自环境变量 `WECHAT_APP_ID` / `WECHAT_APP_SECRET`，或 `--config` 文件。不要写进仓库、命令参数或日志。
- 只建草稿，不群发。**改稿重发会新建一份**，提醒用户删掉旧草稿。
- `validate.py` 报 ERROR 时脚本会停下，先修好再发。

## 交付时告诉用户

- 草稿标题、用了哪套主题、各组件放在哪里
- 哪些图是真实截图，哪些是图表或生成的
- 还有哪些需要用户在后台确认（旧草稿要删、封面要不要换）

## 致谢

组件设计和公众号 HTML 校验器来自 [gzh-design](https://github.com/isjiamu/gzh-design-skill)（甲木 × 摸鱼小李，AGPL-3.0）。本仓库同样以 AGPL-3.0 发布。
