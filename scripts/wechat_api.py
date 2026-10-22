#!/usr/bin/env python3
"""Create a WeChat Official Account draft from a prepared job directory.

Runs locally or on a whitelisted server (Python 3.8+, `requests`). Credentials
come from WECHAT_APP_ID / WECHAT_APP_SECRET in the environment, never argv.

Job directory layout (made by publish.py):
  content.html   body HTML; images referenced as src="assets/<name>"
  meta.json      {"title", "digest", "author"}
  cover.jpg      cover image (2.35:1)
  assets/        body images (jpg/png, <= 1 MB each)

Usage: wechat_api.py <job_dir>
"""
import json
import os
import re
import sys

import requests

API = "https://api.weixin.qq.com/cgi-bin"


def check(resp):
    data = resp.json()
    if data.get("errcode"):
        hint = {40164: "this IP is not in the account's IP whitelist",
                40001: "wrong AppSecret", 40013: "wrong AppID",
                40113: "unsupported image type (use jpg/png)"}.get(data["errcode"], "")
        raise RuntimeError("wechat api error %s: %s %s" % (data["errcode"], data.get("errmsg"), hint))
    return data


def run_job(job, app_id, app_secret):
    token = check(requests.get(API + "/token", timeout=20, params={
        "grant_type": "client_credential", "appid": app_id, "secret": app_secret}))["access_token"]
    with open(os.path.join(job, "content.html"), encoding="utf-8") as fh:
        content = fh.read()
    with open(os.path.join(job, "meta.json"), encoding="utf-8") as fh:
        meta = json.load(fh)

    # Body images must be on WeChat's CDN: media/uploadimg returns a URL.
    assets = os.path.join(job, "assets")
    for name in sorted(os.listdir(assets)) if os.path.isdir(assets) else []:
        with open(os.path.join(assets, name), "rb") as fh:
            url = check(requests.post(API + "/media/uploadimg", params={"access_token": token},
                                      files={"media": (name, fh)}, timeout=60))["url"]
        content = content.replace('src="assets/%s"' % name, 'src="%s"' % url)
        print("image uploaded:", name)
    left = re.findall(r'src="assets/[^"]+"', content)
    if left:
        raise RuntimeError("images not uploaded: %s" % left)

    # The cover is a permanent material; the draft references its media_id.
    with open(os.path.join(job, "cover.jpg"), "rb") as fh:
        thumb = check(requests.post(API + "/material/add_material", timeout=60,
                                    params={"access_token": token, "type": "image"},
                                    files={"media": ("cover.jpg", fh)}))["media_id"]
    print("cover uploaded")

    article = {
        "title": meta["title"], "author": meta.get("author", ""), "digest": meta.get("digest", ""),
        "content": content, "thumb_media_id": thumb,
        "need_open_comment": 1, "only_fans_can_comment": 0,
    }
    # Always add a new draft: draft/update reads back fine through the API but the
    # web editor may keep showing the old version. Delete old drafts by hand.
    body = json.dumps({"articles": [article]}, ensure_ascii=False).encode("utf-8")
    data = check(requests.post(API + "/draft/add", params={"access_token": token}, data=body, timeout=60,
                               headers={"Content-Type": "application/json; charset=utf-8"}))
    print("draft created: media_id=%s" % data.get("media_id"))
    return data.get("media_id")


if __name__ == "__main__":
    try:
        run_job(sys.argv[1], os.environ["WECHAT_APP_ID"], os.environ["WECHAT_APP_SECRET"])
    except Exception as exc:  # noqa: BLE001 - report and exit non-zero
        print("error: %s" % exc, file=sys.stderr)
        sys.exit(1)
