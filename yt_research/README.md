# ytr — YouTube市場 自律調査システム

YouTube Data API v3 (公式) のみで、公開90日以内・5万再生以上・音楽以外の動画を起点に
「単発ヒットではなく再現性のある成功」を出しているチャンネル/ジャンルを継続観測する。

## 構成
| モジュール | 役割 |
|---|---|
| `ytr/api.py` | APIクライアント。クォータ単位を全呼び出しでDB記録、太平洋時間の日次リセット、予算上限、5xx/通信障害の指数バックオフ、quotaExceededで安全停止 |
| `ytr/db.py` | SQLite。`videos`/`channels`はID一意(重複登録なし)、`*_snapshots`は(ID, 観測日時)で時系列保持 |
| `ytr/topics.py` | 73の初期テーマ(9言語・約40ジャンル)。未実行テーマをジャンル横断で優先→以降UCB1で収穫の多いテーマに予算集中、収穫ゼロが続くテーマは自動停止。再現性チャンネルのタグから新テーマを自動生成 |
| `ytr/collect.py` | 1サイクル: ①追跡動画の再生数更新 → ②検索(100単位/回) → ③動画詳細 → ④ヒットのあるチャンネルの90日全投稿を監査(小規模・新規優先) |
| `ytr/analyze.py` | チャンネル指標(中央値・5万以上割合・投稿頻度・再生速度・集中度・AIシグナル)、ジャンル指標(再現性ch数・新規/小規模の再現・上位3占有率・HHI)、反証可能な仮説の自動判定 |
| `ytr/llm.py` | 任意。Claude APIが仮説と新テーマを提案。仮説は固定指標DSLでしか書けず、必ずデータで判定される |
| `ytr/seeds.py` | 過去ChatGPT報告の10事例を公式APIで再検証 |
| `ytr/report.py` | `reports/latest.md` とCSV。仮説状態が変化した時だけ `notable-日付.md` を出力 |

## 方法論上の制約(レポートにも明記)
- 検索結果は上位抽出サンプル。市場全体の成功確率は算出しない。
- 登録者数は取得時点の現在値のみ。公開時点の値としては扱わない。
- Shortsフラグは API に無い → 尺で推定(≤60秒=濃厚、61–180秒=保留)。
- AI制作は推定シグナル(本人申告フィールド+キーワード)。断定しない。
- 収益化状況は公式APIで取得不可 → 未確認。
- 中央値・5万以上割合は公開14日以上の投稿のみで計算(新しすぎる動画で下振れしないため)。

## クォータ
既定 10,000単位/日。search=100、videos/channels/playlistItems=1 (50件/回)。
1回の実行予算は既定8,000(検索最大40回+監査)。`--budget` で変更。

## 実行
```bash
pip install -r requirements.txt
export YOUTUBE_API_KEY=...        # 必須
export ANTHROPIC_API_KEY=...      # 任意(仮説生成)
python -m ytr verify-seeds        # 過去事例の検証(数単位)
python -m ytr run                 # 1サイクル
python -m ytr status
python -m pytest -q tests
```

## 定期実行
`.github/workflows/yt-research.yml` が毎日 08:17 UTC (クォータリセット直後) に実行し、
DBとレポートを `ytr-data` ブランチに保存して次回に引き継ぐ。
GitHubのスケジュール実行は**デフォルトブランチ上のワークフローのみ**動く点に注意。
必要なリポジトリシークレット: `YOUTUBE_API_KEY`(必須)、`ANTHROPIC_API_KEY`(任意)。
