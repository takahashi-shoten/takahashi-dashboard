# 既存コード監査 (youtube_research_prototype / youtube_audit / youtube_audit_v2)

監査日: 2026-11-18。対象: 添付ZIP 3点、総計343行。

## 結論
3点とも**実データ収集は一度も行われていない**。prototypeに同梱のSQLiteは4テーブルとも0行、report.mdも「0 videos」。
設計上の欠陥が複数あり、温存せず `ytr` に置き換えた。有用な部分(検索クエリ20件、v2の分析テスト)は移植済み。

## 重複
| 項目 | 内容 |
|---|---|
| `youtube_audit/audit.py` と `youtube_audit_v2/audit.py` | **完全に同一ファイル**(diffなし)。v2の差分は analyze.py と test_analyze.py の追加のみ |
| prototype と audit | 「uploads再生リストを辿り90日分を取得」処理が別実装で2つ存在。保存スキーマも互換なし |

## 欠陥
| # | 対象 | 問題 | 影響 | ytrでの対処 |
|---|---|---|---|---|
| 1 | 全て | APIキーをURLクエリに付与 | ログ・プロキシ経由で漏洩しやすい | `X-Goog-Api-Key` ヘッダ |
| 2 | 全て | リトライ・バックオフ無し。HTTPエラー1件で全体が例外終了 | 長時間実行が途中で全損 | 5xx/通信障害は指数バックオフ、段階ごとに隔離しエラーをDB記録 |
| 3 | 全て | クォータ消費の記録・上限管理無し | 10,000単位/日超過で停止、原因不明 | 全呼び出しを単位付きで記録、太平洋時間リセット、実行予算 |
| 4 | prototype/audit | commitが最後に1回のみ | 途中失敗で収集済みデータが消える | 動画バッチ単位でcommit、中断runは次回 `aborted` として復旧 |
| 5 | prototype | **音楽カテゴリを除外していない**(categoryId未取得) | 指示書の条件違反 | categoryId=10 を除外・件数記録 |
| 6 | prototype | 同一動画が複数クエリでヒットすると、どのクエリで見つかったかは最後の1件しか残らない | ジャンル帰属・重複排除数が測れない | `discoveries(video_id, topic_id)` で全経路と出現回数を保持 |
| 7 | prototype | playlistItemsが90日の境界で止まらない | クォータ浪費 | 境界到達で停止 |
| 8 | prototype/audit | 取得上限(100/200件)到達時のカバー範囲を記録しない | 投稿頻度・ヒット率が過小/過大に | `audit_through` に実カバー範囲を記録し、満たない場合は監査済み扱いにしない |
| 9 | v2 analyze | `posts_per_30d = 件数×30/90` 固定 | 開設90日未満のチャンネルや上限到達時に誤り | チャンネル開設日と期間で補正、監査済みのみ算出 |
| 10 | prototype | ヒット率順ソートで 1/1=100% が上位に来る | 少数サンプルが過大評価 | 再現性判定に最低成熟投稿数(5本)を要求 |
| 11 | 全て | 公開直後の動画も中央値に含める | 中央値が下振れ | 公開14日以上の投稿のみで中央値・ヒット率を算出 |
| 12 | 全て | Shorts/長尺を混合 | 収益構造の異なる指標が混ざる | 尺で3分類(濃厚/保留/長尺)し長尺・Shorts中央値を分離 |
| 13 | prototype | channels を INSERT OR REPLACE | 登録者数の時系列が消える | `channel_snapshots` で時系列保持 |
| 14 | 全て | テーマ固定(20件)、自動生成・仮説検証・定期実行なし | 自律調査にならない | UCB1スケジューラ、タグ由来の自動拡張、Claude API提案、反証可能な仮説、GitHub Actions日次実行 |
| 15 | prototype/audit | テスト無し(v2のanalyzeのみ2件) | — | モックAPIでパイプライン全体をテスト(11件) |

## 再利用したもの
- prototypeの検索クエリ20件 → `ytr/topics.py` SEEDS に原文のまま追加(既存と重複するものは除く)
- audit の過去事例10件のID → `ytr/seeds.py`
- v2 test_analyze の期待値(中央値60,000・ヒット2/3) → `tests/test_pipeline.py::test_legacy_v2_analyze_case_ported`
- 各READMEの「研究上の制約」記述 → ytr のレポートの「データ項目の確認状況」表に統合
