# Global Demand & AI Business Research(仮称)― 世界購買需要・AI事業化研究プロジェクト
開始: 2026-11-28(オーナー指示。`CLAUDE.md` の「2026-11-28 第9指示」)。**新規のゼロからの事業ではない**。親・子の既存資産の上に作る。

## 目的
市場調査そのものではなく、**世界中の実購買需要から商機を発見し、AIで利益を生む事業を継続的に供給する**こと。
サイクル: 市場探索 → データ取得 → 購買需要分析 → 技術調査 → 実現可能性検証 → 消去法による選別 → 事業考案 → 商業実験へ接続 → 実測結果の反映。調査件数・報告書は成果ではない。毎回「何が分かり、何を判断し、次に何をするか」を書く。

## 3つのプロジェクトの関係(互いの存在を、ここで恒久的に確認できる)
| プロジェクト | 役割 | 記録の場所 |
|---|---|---|
| 親: AI自律収益化システム構築 | 商品・コンテンツ制作、集客・販売・収益測定、実験→測定→改善の自律ループ、商業実験の実施。**作業は継続(中断・縮小・初期化しない)** | `CLAUDE.md`、`docs/PROJECT_STATE.md`、実験台帳(`experiments/`)、`studio/` |
| 子: AI美容業界SNS事業 | 美容・着付け等の小規模店舗向けInstagram集客・リール制作・運用代行 | `docs/projects/beauty_sns/` |
| **新: Global Demand & AI Business Research(本プロジェクト)** | 世界規模の購買需要調査、AI実現可能性の検証、未充足需要の発見、新規事業モデルの考案、消去法による候補選別、有望な商機の継続的な供給 | `docs/projects/global_demand/`(本ディレクトリ) |
- 重なりの整理: 親が11-26〜28に行った「世界の他市場の調査」(`docs/research/opportunity_ranking_2026-11-26.md`、ココナラ44件、議事録の検証など)は**本プロジェクトの出発点の資産**。以後、市場探索・需要分析・候補選別の主担当は本プロジェクト。親は、本プロジェクトが渡した商機を、商業実験にし、測定して返す。
- チャット間の記憶共有は前提にしない。**ファイルとGitHubが唯一の共有手段**。

## 双方が参照できる情報(新しい連携システムは作らない。既存の場所を指す)
| 情報 | 場所 |
|---|---|
| 名称・目的・経営原則 | `CLAUDE.md`、`docs/MANAGEMENT_PRINCIPLES.md`、`docs/projects/README.md`、本ファイル |
| リポジトリ・データの保存場所 | 本リポジトリ(`takahashi-shoten/takahashi-dashboard`、作業ブランチ `claude/epic-albattani-qohzgb`)。DB: `knowledge/marketing_knowledge.db`、実験台帳。生データ: `docs/research/commerce_data/`。Actionsの出力: ブランチ `studio-samples` |
| 現在の進捗 | `docs/PROJECT_STATE.md`(親)、`docs/SESSION_LOG.md`、本プロジェクトの `CANDIDATES.md` の更新履歴 |
| 利用可能な技術資産 | `studio/`(音声・画像・動画・Gemini解析・文字起こし評価 `minutes_eval.py`・動画編集 `footage_short.py`)、`yt_research/`、`knowledge/`、`commerce_research/`(ココナラ調査 `coconala_listing_probe.py` ほか)、`.github/workflows/key-check.yml`(実行基盤。タスクを足して使う) |
| 調査済みの市場・商品、購買需要の結果 | `docs/research/`(`commerce_data_survey`、`opportunity_ranking`、`productization_audit`、`demand_first_products`、`reel_editing_market` ほか)、`docs/research/commerce_data/*.csv` |
| AI技術の検証結果 | `docs/CAPABILITY_LOG.md`、`products/eval/`、`opportunity_ranking` 末尾の技術検証(議事録ほか) |
| **有望な事業候補・除外した事業とその理由** | **`docs/projects/global_demand/CANDIDATES.md`(本プロジェクトの中心台帳)** |
| 商業実験の結果 | `experiments/`(台帳・計画・基準値)、親の `docs/PROJECT_STATE.md`、子の `RETURN_TO_PARENT.md`。**結果が出たら、CANDIDATES.md の該当行に反映する** |
| 最新の経営判断 | `docs/DECISIONS.md` |
| 予算 | `docs/BUDGET_LEDGER.md`(プロジェクト別。月3万円は全プロジェクト合計) |

## 連携の手順(双方向)
- **本プロジェクト → 親**: 十分な根拠のある候補は `OPPORTUNITY_HANDOFF.md` に、次の8項目で書く: 対象顧客 / 購買需要の証拠 / 具体的な商品仕様 / 競合との差別化 / 販売価格 / 制作・提供原価 / 利益構造 / 利用技術 / 集客方法 / 販売先 / 実験方法 / 成功・失敗の判定条件。親は、これを見て、商業実験を準備する(承認が要るものは承認待ち)。
- **親・子 → 本プロジェクト**: 実験結果・失敗・技術の検証結果は、各自の記録に書き、本プロジェクトは、`CANDIDATES.md` の「実験結果」列と判定を更新する。各セッションは、開始時に `CANDIDATES.md` と `OPPORTUNITY_HANDOFF.md` を読む。
- セッション開始時の読む順: `CLAUDE.md` → `docs/MANAGEMENT_PRINCIPLES.md` → `docs/PROJECT_STATE.md` → `docs/DECISIONS.md` → `docs/SESSION_PROTOCOL.md` → 本ディレクトリ(README、CANDIDATES、OPPORTUNITY_HANDOFF)→ `docs/SESSION_LOG.md` の末尾。

## 研究の規律(指示の要点。破らない)
1. 業種・媒体を限定しない。日本・北米・欧州・中国・韓国・台湾・東南アジア・インド・中南米。物理商品、デジタル商品、サービス、専門家、教育、娯楽、ソフト、サブスク、生活問題、趣味、感情価値、時短、情報・判断支援。**一般個人が日常的に払う市場を重視**。公開データセット・公式API・既存プログラム・公開コード・調査機関資料を最大限使う。利用規約・ライセンス・個人情報を確認(`docs/research/commerce_data_survey_2026-11-26.md` の方針を引き継ぐ)。
2. 購買需要(誰が、何に、なぜ、価格、実販売、市場規模、成長、頻度、リピート、不満、未解決の問題、集客方法、競合)と、AI実現可能性(同等以上の価値、効率化、原価、品質、速度、量産、集客・販売・納品の自動化、人間介入の削減、技術の組み合わせ、利益構造)を**同時に**調べる。AIだけで完結する必要はない(通常のプログラム、公開コード、API、複数AI、既存サービス、最小限の人間作業)。
3. **消去法**。思いつきの少数選定は禁止。候補数を固定しない。判定は4段階: 継続検討 / 条件付き継続検討 / 証拠不足による保留 / 根拠に基づく除外。
   - 「今のシステムに機能がない」≠「AIでできない」。未調査・未実装・未検証だけを理由に除外しない。
   - 直接の代替が難しくても、**工程に分解**して部分的な代替・効率化・新しい提供方法を検討する。
   - 除外の前に、AI技術・公開コード・API・代替手段・組み合わせを調べ、可能な範囲で、実際の動作・制作・品質比較・処理時間・原価を**測る**。
   - 除外した候補も記録し、技術・市場の変化で再検討する(「再検討の条件」列)。
4. **新しいビジネスの発明**: 模倣・価格競争だけを目的にしない。需要・不満・AI技術・異業種の成功モデルの組み合わせで、新しい商品・提供方法・収益構造を考案。顧客がお金を払う理由を検証する。
5. 市場調査の完了を待たず、根拠が十分な候補は、親に渡して商業実験につなげる。
6. 測定値/公開表示/申告/推定/未確認を分ける。ステータス語彙(未実装〜市場成果確認済み)を使う。完了率は使わない。
7. 制約: 月3万円は全プロジェクト合計。無断で追加課金・契約・外部公開をしない。承認事項(外部公開・出品・営業・アカウント作成・追加課金・契約・PRマージ・研究用APIの上限2,000円超)は承認待ち。人の介入時間を最小に。既存データ・コードを不用意に移動・複製しない(参照・再利用)。公開リポジトリに個人・店舗・顧客を特定する情報を入れない。

## セッション記録
- 2026-11-28 起動: session_015qHeRB2rcPoj1DvZaowMEq(`START_PROMPT.md` を送信。最初の実調査 = `CANDIDATES.md` の「次の作業」1)。
