import importlib.util
import io
import json
import os
import time
import urllib.error
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location("yt_oauth_local", Path(__file__).resolve().parents[2] / "tools" / "yt_oauth_local.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def _write_client(d, name, secret, project="meta-micron-515404-j5", age=0):
    p = d / name
    p.write_text(json.dumps({"web": {"client_id": "123-abc.apps.googleusercontent.com", "client_secret": secret, "project_id": project}}))
    t = time.time() - age
    os.utime(p, (t, t))
    return p


def test_newest_client_json_is_chosen_and_project_is_checked(tmp_path):
    _write_client(tmp_path, "client_secret_old.json", "OLD", age=3600)
    new = _write_client(tmp_path, "client_secret_new.json", "NEW", age=10)
    assert m.find_client_json(str(tmp_path)) == str(new)
    assert m.load_client(str(new), "meta-micron-515404-j5")["client_secret"] == "NEW"
    with pytest.raises(m.SetupError):
        m.load_client(str(new), "another-project")
    with pytest.raises(m.SetupError):
        m.find_client_json(str(tmp_path / "empty"))


def test_auth_url_is_offline_with_three_scopes_and_state_is_verified():
    u = m.build_auth_url("cid", "STATE1", "a@example.com")
    assert "access_type=offline" in u and "prompt=consent" in u and "login_hint=a%40example.com" in u and u.count("scope=") == 1
    assert all(s.rsplit("/", 1)[-1] in u for s in ("youtube.upload", "yt-analytics.readonly"))
    ok = "https://developers.google.com/oauthplayground/?code=4%2FABC&state=STATE1&scope=x"
    assert m.extract_code(ok, "STATE1") == "4/ABC"
    with pytest.raises(m.SetupError):
        m.extract_code(ok.replace("STATE1", "OTHER"), "STATE1")
    with pytest.raises(m.SetupError):
        m.extract_code("https://developers.google.com/oauthplayground/?error=access_denied", "S")
    with pytest.raises(m.SetupError):
        m.extract_code("hello", "S")


class _Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _opener(payload):
    return lambda req, timeout=30: _Resp(json.dumps(payload).encode())


def test_exchange_requires_refresh_token_and_all_scopes():
    client = dict(client_id="c", client_secret="s")
    good = {"access_token": "A", "refresh_token": "R", "scope": " ".join(m.SCOPES)}
    assert m.exchange_code(client, "code", _opener(good))["refresh_token"] == "R"
    with pytest.raises(m.SetupError):
        m.exchange_code(client, "code", _opener({"access_token": "A", "scope": " ".join(m.SCOPES)}))
    with pytest.raises(m.SetupError):
        m.exchange_code(client, "code", _opener({"access_token": "A", "refresh_token": "R", "scope": m.SCOPES[0]}))

    def boom(req, timeout=30):
        raise urllib.error.HTTPError("u", 400, "bad", {}, io.BytesIO(b'{"error":"invalid_client"}'))
    with pytest.raises(m.SetupError) as e:
        m.exchange_code(client, "code", boom)
    assert "invalid_client" in str(e.value)


def test_wrong_channel_is_refused_and_nothing_is_stored():
    other = {"items": [{"id": "UC_OTHER", "snippet": {"title": "別のチャンネル"}, "statistics": {}}]}
    with pytest.raises(m.SetupError):
        m.verify_channel("tok", "静かなる逆転劇", _opener(other))
    with pytest.raises(m.SetupError):
        m.verify_channel("tok", "静かなる逆転劇", _opener({"items": []}))
    right = {"items": [{"id": "UC1", "snippet": {"title": "静かなる逆転劇"}, "statistics": {"subscriberCount": "0", "videoCount": "0"}}]}
    assert m.verify_channel("tok", "静かなる逆転劇", _opener(right))["id"] == "UC1"


class _Run:
    def __init__(self, existing=()):
        self.calls, self.existing = [], list(existing)

    def __call__(self, cmd, **kw):
        self.calls.append((cmd, kw.get("input")))
        class R:  # noqa
            returncode, stderr = 0, ""
        R.stdout = "\n".join(f"{n}\t2026-11-25" for n in self.existing) if cmd[:3] == ["gh", "secret", "list"] else ""
        return R


def test_secrets_go_through_stdin_never_arguments_and_existing_ones_are_not_overwritten():
    vals = {"YT_OAUTH_CLIENT_ID": "id", "YT_OAUTH_CLIENT_SECRET": "SECRET-VALUE", "YT_OAUTH_REFRESH_TOKEN": "TOKEN-VALUE"}
    run = _Run()
    assert m.store_secrets(vals, "o/r", False, run) == list(vals)
    sets = [c for c in run.calls if c[0][:3] == ["gh", "secret", "set"]]
    assert len(sets) == 3 and all("SECRET-VALUE" not in " ".join(c[0]) and "TOKEN-VALUE" not in " ".join(c[0]) for c in sets)
    assert {c[1] for c in sets} == set(vals.values())
    run2 = _Run(existing=["YT_OAUTH_REFRESH_TOKEN"])
    with pytest.raises(m.SetupError):
        m.store_secrets(vals, "o/r", False, run2)
    assert not [c for c in run2.calls if c[0][:3] == ["gh", "secret", "set"]]                  # nothing was written
    assert m.store_secrets(vals, "o/r", True, _Run(existing=["YT_OAUTH_REFRESH_TOKEN"]))
