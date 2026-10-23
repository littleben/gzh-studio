# 发布到草稿箱

## 前提

1. 公众号后台 →「设置与开发」→「开发接口管理」：拿到 AppID 和 AppSecret。
2. 同一页的 **IP 白名单** 里，加上调用接口的那台机器的公网 IP。家里和办公室的 IP 常常会变，所以最好在一台固定 IP 的服务器上调用，用 `--ssh` 方式。
3. 个人订阅号也能调草稿箱接口（`draft/add`、`media/uploadimg`、`material/add_material`）。

## 命令

```bash
pip install pillow requests            # 远端服务器只需要 requests

# 只渲染、校验、压图，不上传
python3 scripts/publish.py article.md --dry-run --preview out.html

# 本机 IP 已在白名单
WECHAT_APP_ID=wx... WECHAT_APP_SECRET=... python3 scripts/publish.py article.md

# 通过白名单服务器（推荐）
python3 scripts/publish.py article.md --ssh myserver --config ~/.config/markdown-to-wechat.yaml
```

`--config` 文件只放两行：`app_id: wx...` 和 `app_secret: ...`。**不要提交到仓库**，`.gitignore` 已经忽略了 `*.yaml`。用 `--ssh` 时，凭据走 SSH 的 stdin，不会出现在命令行参数、日志或上传的文件里；远端的临时目录会自动删除。

## 流程（publish.py 做了什么）

1. `render.py` 渲染，按 `layout-standard.md` 打印密度提示
2. `validate.py` 校验公众号的 HTML 限制，有 ERROR 就停
3. 正文图压成 JPEG（≤1080 宽，≤1 MB），封面裁成 2.35:1
4. `media/uploadimg` 上传正文图，换成微信的图片地址
5. `material/add_material` 上传封面，拿到 `thumb_media_id`
6. `draft/add` 新建草稿；摘要默认取第一段

## 注意

- **改稿重发会新建一份草稿。** `draft/update` 用接口读回来是新内容，但网页编辑器里可能还是旧版（实测过），所以脚本只用 `draft/add`，旧草稿要手动删掉。
- 只建草稿，不群发。群发前在手机上预览一遍。
- 正文外链会被去掉，链接写成文字或「阅读原文」。

## 常见错误

| 错误码 | 原因 | 处理 |
|---|---|---|
| 40164 | 调用的 IP 不在白名单 | 加白名单，或用 `--ssh` 走白名单服务器 |
| 40001 | AppSecret 错误或已重置 | 后台重新获取 |
| 40013 | AppID 错误 | 检查配置 |
| 40113 | 图片格式不支持 | 用 publish.py，会自动转 JPEG |
| 45009 | 接口调用超过每日上限 | 第二天再试 |
| 封面上传报 -1 | 封面比例不对 | publish.py 会自动裁成 2.35:1 |
