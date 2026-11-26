#!/usr/bin/env python3
"""One-command local helper for the YouTube OAuth setup (run on the owner's Mac; standard library only).
What it automates: find the newest client_secret*.json in ~/Downloads, check it belongs to the expected Google Cloud project, build the consent URL (offline access, the 3
YouTube scopes, a state value), open the browser, accept the pasted redirect address, exchange the code for tokens, VERIFY the signed-in channel is the expected one,
and store YT_OAUTH_CLIENT_ID / _CLIENT_SECRET / _REFRESH_TOKEN as GitHub repository secrets with the `gh` CLI (values go through stdin, never printed, never written
to the repo). If anything does not match, nothing is stored. Human steps: sign in with the channel's account, pick the channel, press Allow, paste the address.
Usage: python3 yt_oauth_local.py --login-hint <channel-account-email> [--expect-title 静かなる逆転劇] [--project meta-micron-515404-j5] [--overwrite]"""
import argparse
import glob
import json
import os
import secrets as pysecrets
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

REDIRECT = "https://developers.google.com/oauthplayground"        # the redirect URI already registered on the client
SCOPES = ["https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube", "https://www.googleapis.com/auth/yt-analytics.readonly"]
REPO = "takahashi-shoten/takahashi-dashboard"
SECRET_NAMES = ("YT_OAUTH_CLIENT_ID", "YT_OAUTH_CLIENT_SECRET", "YT_OAUTH_REFRESH_TOKEN")


class SetupError(Exception):
    pass


def find_client_json(downloads=None):
    """Newest client_secret*.json by modification time (the latest issued secret is the newest download)."""
    d = downloads or os.path.expanduser("~/Downloads")
    files = sorted(glob.glob(os.path.join(d, "client_secret*.json")), key=os.path.getmtime, reverse=True)
    if not files:
        raise SetupError(f"client_secret*.json が {d} に見つかりません")
    return files[0]


def load_client(path, expected_project=None):
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    c = raw.get("web") or raw.get("installed")
    if not c or not c.get("client_id") or not c.get("client_secret"):
        raise SetupError("JSONの形式が想定と違います(web または installed の項目がありません)")
    if expected_project and c.get("project_id") != expected_project:
        raise SetupError(f"プロジェクトが違います(JSON: {c.get('project_id')} / 期待: {expected_project})")
    return dict(client_id=c["client_id"], client_secret=c["client_secret"], project_id=c.get("project_id"))


def build_auth_url(client_id, state, login_hint=None):
    q = {"client_id": client_id, "redirect_uri": REDIRECT, "response_type": "code", "scope": " ".join(SCOPES), "access_type": "offline", "prompt": "consent select_account",
         "include_granted_scopes": "false", "state": state}
    if login_hint:
        q["login_hint"] = login_hint
    return "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(q)


def extract_code(pasted, state=None):
    """Accepts the whole redirect address (or just the code). Verifies the state when present."""
    s = pasted.strip()
    if not s.lower().startswith("http"):
        if s.startswith("4/") and " " not in s:                       # a bare authorization code
            return s
        raise SetupError("アドレスが読み取れません。ブラウザの上のアドレス全体(https:// で始まるもの)をコピーしてください")
    qs = urllib.parse.parse_qs(urllib.parse.urlparse(s).query)
    if "error" in qs:
        raise SetupError("Googleの画面でエラーになりました: " + qs["error"][0])
    if "code" not in qs:
        raise SetupError("アドレスに code= が見つかりません。許可のあとに表示されたアドレスを、全部コピーしてください")
    if state and qs.get("state") and qs["state"][0] != state:
        raise SetupError("state が一致しません(別の認証の結果です)。やり直してください")
    return qs["code"][0]


def _post(url, data, opener=None):
    opener = opener or urllib.request.urlopen
    req = urllib.request.Request(url, data=urllib.parse.urlencode(data).encode(), headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        with opener(req, timeout=30) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            err = json.loads(e.read().decode()).get("error", "")
        except Exception:
            err = ""
        raise SetupError(f"Googleがトークンの交換を拒否しました: HTTP {e.code} {err}")


def exchange_code(client, code, opener=None):
    t = _post("https://oauth2.googleapis.com/token", dict(code=code, client_id=client["client_id"], client_secret=client["client_secret"], redirect_uri=REDIRECT, grant_type="authorization_code"), opener)
    if not t.get("refresh_token"):
        raise SetupError("リフレッシュトークンが返りませんでした(以前の許可が残っている可能性。画面で『許可』をもう一度押してください)")
    granted = set((t.get("scope") or "").split())
    missing = [s for s in SCOPES if s not in granted]
    if missing:
        raise SetupError("許可された権限が足りません: " + ", ".join(m.rsplit("/", 1)[-1] for m in missing))
    return t


def verify_channel(access_token, expect_title, opener=None):
    opener = opener or urllib.request.urlopen
    req = urllib.request.Request("https://www.googleapis.com/youtube/v3/channels?part=snippet,statistics&mine=true", headers={"Authorization": "Bearer " + access_token})
    with opener(req, timeout=30) as r:
        items = json.loads(r.read().decode()).get("items", [])
    if not items:
        raise SetupError("このGoogleアカウントにはYouTubeチャンネルがありません(別のアカウント、または別のチャンネルを選んだ可能性)")
    titles = [i["snippet"]["title"] for i in items]
    if expect_title not in titles:
        raise SetupError(f"期待したチャンネル『{expect_title}』ではありません(接続先: {titles})。保存せずに中止します")
    ch = next(i for i in items if i["snippet"]["title"] == expect_title)
    return dict(title=ch["snippet"]["title"], id=ch["id"], subscribers=ch["statistics"].get("subscriberCount"), videos=ch["statistics"].get("videoCount"))


def existing_secret_names(repo=REPO, runner=None):
    runner = runner or subprocess.run
    r = runner(["gh", "secret", "list", "--repo", repo], capture_output=True, text=True)
    if r.returncode != 0:
        raise SetupError("gh(GitHub CLI)が使えません。`gh auth login` を済ませてください: " + (r.stderr or "").strip()[:200])
    return {line.split()[0] for line in r.stdout.splitlines() if line.strip()}


def store_secrets(values, repo=REPO, overwrite=False, runner=None):
    runner = runner or subprocess.run
    have = existing_secret_names(repo, runner)
    clash = [n for n in values if n in have]
    if clash and not overwrite:
        raise SetupError("すでに登録済みのため、上書きしません: " + ", ".join(clash) + "(上書きするなら --overwrite)")
    for name, val in values.items():
        r = runner(["gh", "secret", "set", name, "--repo", repo], input=val, capture_output=True, text=True)   # value via stdin only
        if r.returncode != 0:
            raise SetupError(f"{name} の登録に失敗しました: " + (r.stderr or "").strip()[:200])
    return list(values)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--login-hint")
    ap.add_argument("--expect-title", default="静かなる逆転劇")
    ap.add_argument("--project", default="meta-micron-515404-j5")
    ap.add_argument("--downloads")
    ap.add_argument("--overwrite", action="store_true")
    a = ap.parse_args(argv)
    try:
        path = find_client_json(a.downloads)
        client = load_client(path, a.project)
        print(f"1/5 JSONを確認: {os.path.basename(path)}(更新: {__import__('time').strftime('%m/%d %H:%M', __import__('time').localtime(os.path.getmtime(path)))}) / project {client['project_id']} / client {client['client_id'][:14]}…")
        state = pysecrets.token_urlsafe(16)
        url = build_auth_url(client["client_id"], state, a.login_hint)
        print("2/5 ブラウザを開きます。チャンネルの持ち主のアカウントでログインし、『静かなる逆転劇』を選んで、『許可』を押してください。")
        try:
            subprocess.run(["open", url], check=False)
        except FileNotFoundError:
            print(url)
        print("   (開かない場合は、次のアドレスを自分で開いてください)\n   " + url)
        pasted = input("3/5 許可のあと、ブラウザの上のアドレス(https://developers.google.com/oauthplayground/?code=… で始まるもの)を全部コピーして、ここに貼って Enter: ")
        code = extract_code(pasted, state)
        tokens = exchange_code(client, code)
        info = verify_channel(tokens["access_token"], a.expect_title)
        print(f"4/5 チャンネルを確認: {info['title']}(ID {info['id']}、登録者 {info['subscribers']}、動画 {info['videos']})")
        names = store_secrets({"YT_OAUTH_CLIENT_ID": client["client_id"], "YT_OAUTH_CLIENT_SECRET": client["client_secret"], "YT_OAUTH_REFRESH_TOKEN": tokens["refresh_token"]}, overwrite=a.overwrite)
        print("5/5 GitHubに登録しました(値は表示していません): " + ", ".join(names))
        print("完了。Claudeに『登録できた』と伝えてください。")
        return 0
    except SetupError as e:
        print("中止: " + str(e))
        return 1


if __name__ == "__main__":
    sys.exit(main())
