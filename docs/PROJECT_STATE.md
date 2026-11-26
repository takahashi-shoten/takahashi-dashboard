# プロジェクトの現在地と原資料の索引(生きた文書。作業のたびに更新する)

最終更新: 2026-11-26 / 更新者: Claude Code(セッション継承作業) / 公開リポジトリのため、個人情報・秘密・店舗が特定できる情報は書かない。
使い方: 新しいセッションは、まず `CLAUDE.md` → この文書 → `docs/SESSION_PROTOCOL.md` の順に読む。詳細は下の索引から原資料へ。会話の履歴を最初から読み直す必要はない。
表記: [実測]=ログ・データで確認 / [報告]=オーナー申告 / [推定] / [未確認]。状態は6段階(未実装 / 実装済み / 模擬テスト済み / 実動作確認済み / 実運用確認済み / 市場成果確認済み)。完成率は出さない。

## 1. 目的と経営思想(変わらない部分)
- 目的: AIが市場・顧客・成功/失敗事例を学び、収益機会を発見し、商品・サービスを企画し、マーケティング・集客・販売・利益測定・改善を自律で回し、継続利益を生む**仕組み**を作る。YouTubeや動画制作そのものが目的ではない。媒体・商品・人物・AIに固執しない。
- 経済目標: 5年後の純資産1億円(深い目的は経済的・時間的自由)。1年がかりの構築。月100万円は通過点。2026-12-20 は「実測データがそろった一通りの試験」の最初の区切りで、収益の期限ではない(11-25の受入基準には「実際の支払い取引を目指す」とあるが、必須条件ではなく目標)。人間の労働・管理時間も評価指標(目標: オーナーの介入 1日1時間程度)。
- 中核能力: マーケティングとセールスコピー。他者が何年もかけた試行錯誤(成功・失敗・停滞・転換点)の短縮。1つの制作物から多方向の訴求・販売を考える。制作物の価値と販売方法の問題を分けて考える。AI・既存技術・通常プログラムを適材適所で使う。AIの稼働量ではなく経済的成果と能力の向上で評価する。
- 本文: `docs/MANAGEMENT_PRINCIPLES.md`、`CLAUDE.md`(2026-11-24 / 11-25 / 11-26 の指示)。最新の有効な指示と変更の経緯は `docs/DECISIONS.md`。

## 2. 現在の事実(2026-11-26)
- 市場成果: 公開動画0本、顧客0、売上0円、利益0円。市場実験の実行0件。[実測]
- 実運用で動いているもの: 調査データの自動収集(1日2回)。それ以外の輪は閉じていない。
- YouTube OAuth: Secrets 3つ登録・同意画面「本番」・`measure check` で token ok / scopes_missing [] / analytics ok を、**Actions のログ(run 45725655099、2026-11-26 00:01)で確認**。[実測] 状態: 実動作確認済み(接続のみ)。動画0本のため、アップロード・測定の実績はない。
- 知識DB: 19件(11-24: 内田チャンネル由来13件、11-26: 保存済み結果から6件追加)。`knowledge_uses`(使用記録)は0件=**企画に一度も使われていない**。
- 予算: 月3万円。研究・学習用API費の上限 **2,000円**(承認済み)。残り3,000円は未承認。累計の推定: 約4,000円(Gemini 約3,300 + Claude 約510〜570)。研究・検証分は約224円+Shorts視聴約34円。AIサブスクが月3万円に含まれるかは未確認。
- **会話処理(Claude Code セッション)の利用記録**(11-26 に `get_session` で取得): `usage.cost_usd` はクライアントがトークン数から出した**推定の価格換算額で、請求額ではない**。旧セッション 92.64(完了)/ 続行セッション 32.33 / この継承セッション 11.02(進行中。11-26 01:10 時点)/ OAuthセッションは記録なし(Mac上のローカル実行)。3つの合計は約$136(約2.0万円@150円)。同時点の `rate_limit_info` は `isUsingOverage: false`・`five_hour`(契約プランの枠内の表示で、追加利用料金ではない)。実際の請求は未確認(契約プラン名・Extra usage・請求書は、オーナーが claude.ai の使用状況/請求の画面で確認する必要がある)。
- **Anthropic APIの制作費とは別の計測で、二重計上ではない**: 制作パイプラインのAPI費は、GitHub Actions が `ANTHROPIC_API_KEY` で呼んだ API の応答の使用量を台帳(`costs`)に記録したもの(実測。約$3.4〜3.8)。支払いは API の前払い(約$22、11-22)。Claude Code のセッションは、アカウントのログインで動き、別の計測。ただし、API前払いの残高と台帳の合計の一致は、Console を見ていないため未確認。

## 3. 能力の状態(6段階)
| 能力 | 状態 | 根拠・原資料 |
|---|---|---|
| 調査DB(168,763本・3,790ch、1日2回収集) | 実運用確認済み | `yt-research.yml`、`docs/research/ytr_audit_2026-11-25/AUDIT.md`。直近3か月の断面で、時系列・失敗事例は弱い |
| 制作パイプライン(台本・2社QA・画像・音声・編集・サムネ) | 実動作確認済み | 試作T1〜T5・E1(未公開)。`docs/CHATGPT_HANDOVER_2026-11-24.md` |
| 動画の映像+音声の分析 | 実動作確認済み(自社動画の短い区間で条件付き合格) | `docs/REPORT_2026-11-24_gemini_video_analysis_and_marketing_learning.md`、`docs/research/vu_verification_2026-11-24/` |
| 知識DB(SQLite、`studio/studio/knowledge.py`) | 実装済み。**企画への利用で成果物が良くなるかは、予備評価で示されなかった**(`docs/CAPABILITY_LOG.md`、`experiments/ablation/2026-11-26/RESULTS.md`)。個別監査: `docs/research/knowledge_audit_2026-11-26.md` | `knowledge/marketing_knowledge.db`、バックアップ `knowledge/snapshots/` |
| 実験台帳(チャネル非依存、`experiments.py`) | 実装済み | `experiments/plans/`、`studio-data` ブランチ。保存は追記専用に変更済み(11-26、ローカル模擬のみ確認。Actionsでの実行は未確認。mainに入るまで定期実行には反映されない) |
| 公開・測定(`youtube.py` `measure.py` `yt-measure.yml`) | 接続のみ実動作確認済み。アップロード・測定は模擬テストのみ | 上記Actionsログ |
| 追記専用の保存と復元(`snapshot.py`) | 実動作確認済み(単体) | ワークフロー未接続 |
| マーケティング文案生成(`marketing.py`) | 模擬テスト済み | — |
| 知識DB→企画への自動接続(11-26更新: **コード側の選択 `knowledge.relevant` に変更**。関連なしなら使わない。歴史ジャンルでは『関連なし』になり、以前の無条件投入を解消。再現率は低い=保守的) | **接続済み(11-26)**: `make_brief` が `knowledge.consult` で種類別に知識を引き、ラベル(状態・確信度・条件)つきで brief に載せて使用を記録。`measure register` は計画の `knowledge_terms` で知識を紐づけ。テスト合格(171件)。DBのコピーでS1→K18、S2→K14・K15を確認。**実際の制作・登録はまだ行っていない**。使用記録(`knowledge_uses`)は、Actions上で実行すると保存されない(実験台帳 `knowledge_used_json` と brief には残る)→ 使用記録の永続化は課題 | `studio/studio/knowledge.py`(`consult`)、`brief.py`、`measure.py`(`register`) |
| 予算の強制 | 部分的(動画分析と調査の上限のみ) | — |
| 経営判断エンジン、自律ループ、販売・顧客対応 | 未実装 | — |

## 4. 原資料の索引
- 比較試験の原因分析: `docs/research/knowledge_ablation_cause_analysis_2026-11-26.md`。第2回(方式A/B/C/D): `experiments/ablation/2026-11-26-round2/`。マーケ学習の計画: `docs/research/marketing_learning_plan_2026-11-26.md`。市場実験の準備: `experiments/ablation/2026-11-26/MARKET_PREP.md`、`experiments/plans/D1_digital_checklist.json`
- 能力の試験記録: `docs/CAPABILITY_LOG.md`。知識の個別監査: `docs/research/knowledge_audit_2026-11-26.md`。比較試験(事前登録・出力・評価・集計): `experiments/ablation/2026-11-26/`
- プロジェクト前史(11-18〜11-24)と、会話の原文への行き方・セッションID: `docs/HISTORY_2026-11-18_to_11-24.md`
- 方針・原則: `CLAUDE.md` / `docs/MANAGEMENT_PRINCIPLES.md` / `docs/DECISIONS.md` / `docs/SESSION_PROTOCOL.md`
- 全作業の報告: `docs/CHATGPT_HANDOVER_2026-11-24.md`(制作・調査・失敗と学び)、`docs/REPORT_2026-11-24_...`(動画解析とマーケ学習)、`docs/REPORT_FOR_CHATGPT_2026-11-25_overall.md`、`docs/AUDIT_REPORT_2026-11-25.md`(現状監査)、`docs/INTEGRATED_REPORT_2026-11-25.md`(統合指示への対応・21項目の検証・経路比較)、`docs/REPORT_FOR_CHATGPT_2026-11-26.md`
- 内田博史チャンネルの分析(6本の原文・サムネ・全動画の数字): `docs/research/uchida_analysis_2026-11-24/`(研究対象の一例。今後の優先対象ではない)
- Shorts20本の視聴: `docs/research/shorts_watch_2026-11-25/`(SUMMARY.md と1本ずつの原文)
- 調査DBの監査・再現できる分析: `docs/research/ytr_audit_2026-11-25/`(`yt_research/audit_db.py`、`analyses_2026-11-25.py`)
- 先行事例: `docs/research/precedents_2026-11-25.md`(一次資料はProject Vendのみ。Felixは二次)、`docs/research/ai_autonomous_businesses_2026-11-24.md`
- 収益機会の比較: `docs/research/revenue_opportunities_v0_2026-11-25.md`
- 実験計画: `experiments/plans/E1〜E3.json`(YouTube)、`S1_salon_receiving_surface.json`・`S2_salon_real_footage_short.json`(サロン)。基準値: `experiments/baselines/salon_2026-11-25.json`(匿名)
- アンケート(奥さんの店): `docs/survey/`(回答の生データと読み取りツール)
- OAuth: `tools/yt_oauth_local.py`、`yt_research/docs/oauth_setup_pc_2026-11-23.md`、`oauth/`(公開ページ)
- ブランチ(リモートは `git ls-remote --heads origin` で確認。ローカルの `git branch` には出ない): `origin/main`(PR #17〜#19まで。ローカルの `main` は古い)/ `claude/funny-allen-4qkj7d`(11-25までの作業。`epic-albattani` に**取り込み済み**)/ `claude/epic-albattani-qohzgb`(main + funny-allen + 11-26の作業。**最新。mainより27コミット先行、未マージ**。PRを出すならこのブランチ1本)/ `exp-E-20261124-01`(E1の成果物)/ `ytr-data`(調査DB)/ `studio-data`(実験台帳)/ `studio-output`(直近の制作物。上書きされる)/ `studio-samples` `voice-samples` `title-anatomy-reports` `visual-style-reports`(各レポート)
- 実行: `key-check.yml`(診断・制作・動画解析のハブ。`task=produce|vugt|vudiag|vustab|vumk|vubatch|vustats|vushorts|…`)、`yt-research.yml`、`yt-measure.yml`(`cmd=check`)

### 古くなった文書(読むときの注意)
`docs/CHATGPT_HANDOVER_2026-11-24.md` と `docs/SESSION_HANDOVER_2026-11-24.md` は11-24時点で、次が古い: 「12/20=構築期限」(→最初の区切り)、「OAuth未設定」(→接続済み)、「PR #17未統合」(→マージ済み)、「ショートはまだ作るな」(→承認不要の範囲は解除)、「技術検証上限1,000円」(→研究・学習2,000円)。最新は `docs/DECISIONS.md`。

### 公開リポジトリにある、扱いの判断が要る情報(場所のみ。対処はオーナー承認待ち)
店舗の防犯・職場環境に関する記述: `docs/SESSION_HANDOVER_2026-11-24.md`、`docs/INTEGRATED_REPORT_2026-11-25.md`、`docs/REPORT_FOR_CHATGPT_2026-11-25_overall.md`、`docs/survey/`、`survey/index.html`、`docs/PROJECT_STATE.md` `docs/REPORT_FOR_CHATGPT_2026-11-26.md`(一般的な言及)。店舗の数字(匿名): `experiments/baselines/salon_2026-11-25.json`、`experiments/plans/S1_*.json`、知識DBの1件。実在の連絡先メール: `oauth/` の2ページのみ(オーナー承認済み。テスト内は `example.com` のダミー)。APIキー・トークンの形式は全ブランチの全履歴で検出0件(限定的なパターン)。履歴には、削除後も残る。

## 5. 過去の主な失敗と解決(再発防止)
- 動画解析の初回不合格 → 原因は判定基準の誤り(音声ぶんがVIDEOに混ざる)。再現性テストで条件付き合格。再検証が必要なのは、長尺・他言語・他モデルのとき。
- E1の初回QAでWeb検索上限により事実確認0件 → 4場面ずつ分割して再実行。E1の7件の表現は未確認のまま(公開前に弱める修正が必要)。
- Gemini TTS の429 → 原因はモデルごとの1日100回上限。予備モデルへの切替とキャッシュ。
- OAuth: プログラムの引数渡し忘れ(31c158c で修正)、同意画面「テスト中」ではトークンが7日で失効 → 「本番」に公開(ホームページとプライバシーポリシーを公開、Search Consoleでドメイン確認)。
- アンケート: 長すぎる / リンクの公開設定 / 非公開の壁 → 要点だけの短い版を、LINEで送れる形に。
- Anthropic APIキーの事故(11-22): キーがスクリーンショット・メモに残り再発行。新キーが401になったのは、GitHub Secret に古いキーが残っていたため。教訓: キーは写さない・メモに貼らない。詳細は前史の文書。
- 私(Claude)の判断ミス: YouTube だけに話を狭める / 人に操作を丸投げする / 見ていないものを分析済みと扱う / 売れている型を外して独自性を優先する。

## 6. 未完了・保留・承認待ち
- **承認待ち(最優先)**: 公開リポジトリに店舗の防犯情報があること → 対処 A(非公開化)/ B(AI事業を別の非公開リポジトリに分離。推奨)/ C(文書から削除)。選択はオーナー。詳細は `docs/INTEGRATED_REPORT_2026-11-25.md` 第10章。
- 承認待ち: `claude/epic-albattani-qohzgb` の main への反映(PR 1本。`funny-allen` は取り込み済みなので別PRは不要)。予算の引き上げ(研究費2,000円→、サブスクの扱い)。サロンの安全方針(女性専用にするか)・撮影と出演の同意。初回公開、外部へのアウトリーチ、新規契約。
- **OAuth の残課題・注意**(OAuthセッションの全文とツールログで確認。11-26): ①アプリは「本番環境」だが、Googleの正式な「検証」は未提出で、ログイン時に「未確認アプリ」警告が出る(新規ユーザー上限100人。オーナー1人なので現状問題なし)。②**新しいリフレッシュトークンが7日で失効しないかは未実証**(約12/2以降に `cmd=check` で確認)。③同意画面の「本番環境」・Search Consoleの所有権・古いクライアントシークレットの削除は、**画面を見たAIの記述が根拠で、独立したログはない**(その後の `check` 成功が、削除の影響がないことを間接的に示す)。④Mac の `~/Downloads` に、使用中のクライアントシークレットを含むJSONが残っている(削除・保管の判断は未実施)。⑤認証コードが1度チャットに貼られた(単一用途・使用済み)。以後、コード・長い文字列が写る画面は貼らない。⑥Search Consoleの操作で、AIがオーナーの個人のメインGoogleアカウントを使った(パスワードはオーナーが入力)。以後、個人アカウントの操作はオーナーの明示の許可を得る。⑦公開ページ(`oauth/`)に事業用の連絡先メールが載っている(オーナー承認済み)。⑧`yt-measure cmd=check` の成功実行: 45646208619(15:32)・45724961378(23:55)・45725655099(00:01、UTC換算の日時はActions画面参照)。
- 未完了: 台帳の保存を追記専用に変更した `yt-measure.yml` を、Actionsで実行して確認すること(手動実行 `cmd=check` で足りる。mainへの反映は承認待ち)、`snapshot` による知識DBの定期バックアップ、予算ガードのコード、知識DBの企画接続、実験カード1サイクルの実行、OAuthアプリの「検証」(Googleの正式審査)は未提出(オーナー1人の利用なので現状問題なし)。

## 7. 次の具体的な仕事(優先順位と理由。変更したら理由を `DECISIONS.md` に記録)
注: (2)永続化のうち台帳の追記専用保存は実装済み(Actions実行で確認が残る)。残る最大の欠落は「知識が使われない」ことなので、4を先に進め、S1の準備を並行する。
1. 引き継ぎ基盤(この文書群)の維持と独立検証 — チャットが変わるたびに能力が初期化されるのを防ぐ。
2. 永続化: 台帳の追記専用保存(実装済み、Actions実行で確認が残る)、知識DBの定期バックアップ → 台帳・知識DBを失わない。
3. 予算ガードのコード化 → 承認範囲の逸脱を防ぐ。
4. 知識の利用方式(11-26 第2回の最終結果・評価者4名: **D(企画後の点検にだけ使う)が最良で、元のAに16/16で勝つ。B(企画前に丸ごと)は最も弱い。ただし生成のばらつきが大きく、点検項目と評価基準が重なる**)。実運用の使用記録の永続化は**Actions実行で確認済み**(`studio-data/knowledge_uses.jsonl`)。S1・S2は台帳に登録済み(E-20261126-01・02。実行は承認後)。D1(デジタル商品)の実験カード作成済み(未登録)。次(旧): ①適用条件で絞った関連知識だけを渡す(`consult` に条件フィルタ)②関連知識3〜5件のBを3回以上生成して再比較(位置の入れ替えを事前登録に含める)③自己啓発以外の一次的な知識を増やす ④S1/S2を台帳に登録して市場で測る(採用案: `experiments/ablation/2026-11-26/ADOPTED_DRAFTS.md`、実行は承認後)。
5. 実験S1(サロンの受け皿の整備)の実行準備: 文案(Googleマップ・Instagram・予約導線)をAIが作り、反映はオーナー/奥さん。AI費用はほぼ0円で、予約数という市場データが最も早く取れる。
