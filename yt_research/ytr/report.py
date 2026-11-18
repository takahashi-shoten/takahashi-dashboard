"""Markdown report + CSV exports. A dated report is written only when something notable changed."""
import csv
import json

from . import config
from .util import iso, utcnow, window_start


def _q(con, sql, *a):
    return con.execute(sql, a).fetchone()[0]


def counts(con):
    return dict(
        topics=_q(con, "SELECT COUNT(*) FROM topics"),
        topics_active=_q(con, "SELECT COUNT(*) FROM topics WHERE status='active'"),
        topics_paused=_q(con, "SELECT COUNT(*) FROM topics WHERE status='paused'"),
        searches=_q(con, "SELECT COUNT(*) FROM search_runs"),
        search_results=_q(con, "SELECT COALESCE(SUM(result_count),0) FROM search_runs"),
        duplicates_removed=_q(con, "SELECT COALESCE(SUM(duplicate_videos),0) FROM search_runs"),
        videos=_q(con, "SELECT COUNT(*) FROM videos"),
        video_snapshots=_q(con, "SELECT COUNT(*) FROM video_snapshots"),
        hits_in_window=_q(con, "SELECT COUNT(*) FROM v_latest WHERE view_count>=? AND published_at>=? AND category_id!='10'",
                          config.MIN_VIEWS, iso(window_start(config.WINDOW_DAYS))),
        channels=_q(con, "SELECT COUNT(*) FROM channels"),
        channels_audited=_q(con, "SELECT COUNT(*) FROM channel_metrics WHERE audited=1"),
        channels_unaudited_with_hits=_q(con, "SELECT COUNT(*) FROM channel_metrics WHERE audited=0 AND hits_n>0"),
        api_units_total=_q(con, "SELECT COALESCE(SUM(units),0) FROM api_calls"),
        errors_total=_q(con, "SELECT COUNT(*) FROM errors"),
    )


FIELD_STATUS = """| 項目 | 状態 | 根拠 |
|---|---|---|
| タイトル/ID/チャンネル/公開日時/尺/再生数/取得日時 | 確認済み | YouTube Data API v3 videos.list (取得時点値) |
| 登録者数 | 確認済み(取得時点の現在値のみ) | channels.list。公開時点の登録者数は取得不能 → 未確認 |
| 投稿頻度・直近90日投稿・中央値・5万以上割合 | 監査済みチャンネルのみ確認済み | uploads再生リスト全件 (上限200本、超過時は範囲を記録) |
| Shorts判定 | 推定 | APIにShortsフラグ無し。≤60秒=Shorts濃厚、61-180秒=判定保留 |
| AI制作の可能性 | 推定(シグナルのみ) | status.containsSyntheticMedia(本人申告、返らない場合多い)+タイトル/説明/タグのキーワード |
| 収益化状況 | 未確認 | 公式APIに第三者チャンネルの収益化情報は無い |
| 市場全体の成功確率 | 算出しない | 検索は上位結果の抽出サンプルであり母集団ではない |
"""


def fmt(x, pct=False):
    if x is None:
        return "—"
    if pct:
        return f"{x:.0%}"
    if isinstance(x, float):
        return f"{x:,.1f}" if x < 1000 else f"{x:,.0f}"
    return f"{x:,}" if isinstance(x, int) else str(x)


def write(con, run_summary, genre_metrics, changes, seed_results=None, llm_result=None):
    now = iso(utcnow())
    c = counts(con)
    L = [f"# YouTube市場調査レポート", f"生成: {now} (UTC) / 対象: 公開{config.WINDOW_DAYS}日以内・{config.MIN_VIEWS:,}再生以上・音楽除外", ""]
    L += ["## 重要な変化", ""]
    if changes:
        for ch in changes:
            L.append(f"- **{ch['hyp_id']}**: {ch['old']} → **{ch['new']}** — {ch['statement']} `{json.dumps(ch['evidence'], ensure_ascii=False)}`")
    else:
        L.append("- 仮説ステータスの変化なし")
    L += ["", "## 累計カウント", "", "| 指標 | 値 |", "|---|---|"]
    names = dict(topics="調査テーマ数", topics_active="稼働中テーマ", topics_paused="停止テーマ(低収穫)",
                 searches="検索実行回数", search_results="検索結果(延べ)", duplicates_removed="重複排除件数(延べ)",
                 videos="動画(ユニーク)", video_snapshots="再生数スナップショット", hits_in_window="条件該当動画",
                 channels="チャンネル(ユニーク)", channels_audited="監査済み(確認済み)チャンネル",
                 channels_unaudited_with_hits="未監査(未確認)ヒットチャンネル", api_units_total="APIクォータ消費累計",
                 errors_total="記録エラー累計")
    for k, v in c.items():
        L.append(f"| {names[k]} | {v:,} |")
    L += ["", "### 今回の実行", "", "```", json.dumps(run_summary, ensure_ascii=False, indent=1, default=str), "```", ""]
    L += ["## データ項目の確認状況", "", FIELD_STATUS, ""]
    L += ["## ジャンル別 (観測サンプル)", "",
          "| ジャンル | ヒットch | 監査済 | 再現性ch | 再現率 | 新規ch再現 | 小規模ch再現 | 上位3占有 | 長尺中央値の中央値 | 週投稿中央値 | AIシグナルch | 言語 |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for g, m in sorted(genre_metrics.items(), key=lambda x: -(x[1]["replicable_channels"] or 0)):
        L.append(f"| {g} | {m['channels_with_hits']} | {m['audited_channels']} | {m['replicable_channels']} | "
                 f"{fmt(m['replicable_rate'], True)} | {m['replicable_new_channels']} | {m['replicable_small_channels']} | "
                 f"{fmt(m['top3_share'], True)} | {fmt(m['median_long_median'])} | {fmt(m['median_uploads_per_week'])} | "
                 f"{m['ai_signal_channels']} | {m['langs']} |")
    L += ["", f"再現性の定義: 監査済み・成熟投稿(公開14日以上){config.REPL_MIN_UPLOADS}本以上・中央値{config.REPL_MIN_MEDIAN:,}以上・"
          f"{config.MIN_VIEWS:,}以上割合{config.REPL_MIN_HIT_SHARE:.0%}以上", ""]
    L += ["## 再現性のある新興・小規模チャンネル (監査済み)", "",
          "| チャンネル | ジャンル | 登録者(現在) | 開設日数 | 90日投稿 | 週投稿 | 長尺中央値 | Shorts中央値 | 5万以上割合 | 中央値再生/日 | AIシグナル | 言語 |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in con.execute("""SELECT * FROM channel_metrics WHERE replicable=1 AND (is_new=1 OR is_small=1)
                            ORDER BY median_velocity DESC LIMIT 40"""):
        L.append(f"| [{r['title']}](https://www.youtube.com/channel/{r['channel_id']}) | {r['genre']} | {fmt(r['subscribers'])} | "
                 f"{fmt(r['channel_age_days'])} | {r['uploads_90d']} | {fmt(r['uploads_per_week'])} | {fmt(r['long_median'])} | "
                 f"{fmt(r['short_median'])} | {fmt(r['hit_share'], True)} | {fmt(r['median_velocity'])} | {fmt(r['ai_signal_share'], True)} | {r['main_lang']} |")
    L += ["", "## 仮説一覧", "", "| ID | 状態 | 内容 | 根拠 |", "|---|---|---|---|"]
    for h in con.execute("SELECT * FROM hypotheses ORDER BY status, hyp_id"):
        L.append(f"| {h['hyp_id']} | {h['status']} | {h['statement']} | `{h['evidence_json'] or ''}` |")
    if seed_results:
        L += ["", "## 過去事例の公式API再検証", "", "| 動画ID | 事例 | 過去報告値 | API確認結果 |", "|---|---|---|---|"]
        for vid, label, rep, res in seed_results:
            L.append(f"| [{vid}](https://www.youtube.com/watch?v={vid}) | {label} | {rep} | {res} |")
    if llm_result is not None:
        L += ["", "## Claude API 仮説生成", "", f"`{json.dumps(llm_result, ensure_ascii=False)}`"]
    L += ["", "## 直近エラー", ""]
    errs = con.execute("SELECT ts, stage, detail FROM errors ORDER BY id DESC LIMIT 10").fetchall()
    L += [f"- {e['ts']} `{e['stage']}` {e['detail'][:200]}" for e in errs] or ["- なし"]
    text = "\n".join(L) + "\n"
    config.REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (config.REPORT_DIR / "latest.md").write_text(text, encoding="utf-8")
    if changes:
        (config.REPORT_DIR / f"notable-{now[:10]}.md").write_text(text, encoding="utf-8")
    export(con)
    return text


def export(con):
    d = config.REPORT_DIR / "exports"
    d.mkdir(parents=True, exist_ok=True)
    for name, sql, args in [
        ("channel_metrics", "SELECT * FROM channel_metrics ORDER BY replicable DESC, median_velocity DESC", ()),
        ("hit_videos", """SELECT v.video_id, 'https://www.youtube.com/watch?v='||v.video_id AS url, v.title, v.channel_id,
            c.title AS channel_title, v.published_at, v.observed_at, v.view_count, v.like_count, v.comment_count,
            v.duration_s, v.format_class, v.default_audio_language, v.synthetic_media, c.subscriber_count AS subs_at_observation
            FROM v_latest v LEFT JOIN c_latest c ON c.channel_id=v.channel_id
            WHERE v.view_count>=? AND v.published_at>=? AND v.category_id!='10' ORDER BY v.view_count DESC""",
         (config.MIN_VIEWS, iso(window_start(config.WINDOW_DAYS)))),
    ]:
        rows = con.execute(sql, args).fetchall()
        with open(d / f"{name}.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if rows:
                w.writerow(rows[0].keys())
                w.writerows([tuple(r) for r in rows])
