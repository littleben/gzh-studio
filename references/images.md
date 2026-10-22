# 配图

## 原则：能截真实的，就不画

后台、产品界面、数据看板、仓库页，凡是有真实页面的地方都用截图。自己画的「数字卡片」看起来像编的，真实截图本身就是证据。

只有数据库里的数字、没有现成页面的统计，才画成图表。图表的配色要和主题一致。

优先级：

1. 数据后台截图：GA4、公众号后台「用户分析」、Stripe、Vercel 这类
2. 产品真实界面：登录页、弹窗、手机上的样子
3. 代码仓库、文档页
4. 图表（只在没有页面可截时用）
5. 插画、AI 生成图（只放封面或氛围图）

## 怎么截

`scripts/shot.py` 截 2 倍清晰度的图：

```bash
# 公开页面
python3 scripts/shot.py out.png --url https://example.com --width 1280 --clip 0,0,1280,900

# 手机，模拟微信内置浏览器
python3 scripts/shot.py out.png --url https://example.com --mobile --wechat

# 需要登录的后台：先用已登录的 Chrome 开调试端口
#   Chrome --remote-debugging-port=9222 --user-data-dir=<一份已登录的配置副本>
python3 scripts/shot.py out.png --cdp http://localhost:9222 --url https://analytics.google.com/... --clip 340,78,1130,610
python3 scripts/shot.py out.png --cdp http://localhost:9222 --tab mp.weixin.qq.com --selector ".chart"
```

几个实测下来的细节：

- **Playwright 连到已有 Chrome 时，截图是 1 倍。** `shot.py` 走 CDP 的 `Emulation.setDeviceMetricsOverride` + `Page.captureScreenshot`，才能拿到 2 倍。
- **GA4 的日期参数写在 URL 里不生效。** 要点开日期选择器，再点 `button[aria-label="2026年9月28日"]` 这样的日历格子；直接往输入框里打字也不生效。
- **公众号后台要扫码登录**，地址里的 `token=` 每次登录都会变。用户分析在 `/misc/useranalysis?token=…`，「渠道构成」里有扫码关注的占比。
- **截图前先在线上确认现状。** 本地代码可能落后线上，文章里写的功能要以线上为准。
- **裁剪到正文说的那一块。** 整页宽屏截图在手机上字太小；单日数字、无关侧栏都裁掉，免得读者误读。
- 涉及账号的截图，发布前检查有没有 AppID、手机号、邮箱、密钥。

## 封面

公众号封面比例是 2.35:1。`scripts/cover.py` 生成 1880×800 的封面：左边放文字，右边放图。

```bash
python3 scripts/cover.py cover.png --title "网站 → 公众号" --lines "三周近 10 万用户" "粉丝 6.7k → 29.4k" \
  --pill "附开源 Skill" --foot example.com --image hero.jpg --theme latepost
```

标题控制在 10 个字左右，信息流里封面显示得很小。

## 格式

- 正文图和封面都会在发布时转成 JPEG，宽度不超过 1080，单张不超过 1 MB（`publish.py` 自动处理）。
- 微信不收 webp。原图是 webp 也没关系，脚本会转换。
