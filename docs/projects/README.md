# プロジェクト構成(2026-11-27 から)
| プロジェクト | 役割 | 記録の場所 | 状態 |
|---|---|---|---|
| **親: AI自律収益化システム構築** | 世界中の収益機会の探索、市場調査、新規事業発見、自律収益化システム(調査→実験→公開→測定→改善)の構築。**特定の業界に固執しない** | `CLAUDE.md`、`docs/PROJECT_STATE.md`、`docs/DECISIONS.md`、`docs/SESSION_LOG.md`、`docs/research/` ほか | 継続 |
| **子: AI美容業界SNSマーケティング事業(仮)** | 美容・着付け・サロン等の小規模店舗向け: Instagram集客、リール制作(実写素材のAI仕上げ)、運用代行(旧P4) | `docs/projects/beauty_sns/`(引き継ぎ: `HANDOVER.md`、分離案: `SEPARATION.md`) | 分離・引き継ぎ準備完了。**開始はオーナーの指示で** |
## 共通ルール(親・子とも)
- 予算: **月3万円は、全プロジェクト合計**。費用は `docs/BUDGET_LEDGER.md` に、プロジェクト別に記録する。
- 承認条件(外部公開・出品・営業・新規契約・アカウント作成・追加課金・PRマージ)は、両方に同じく適用。
- 共通技術(`studio/`、`yt_research/`、`knowledge/`、`.github/workflows/`)は、重複開発せず再利用する。共通技術の変更は、親のテストを通す。
- 子で得た知識・実績・失敗・技術改善は、親に還元する(`docs/projects/beauty_sns/RETURN_TO_PARENT.md` に記録し、知識DBへ)。
- 顧客情報・店舗が特定できる情報・撮影素材は、公開リポジトリに入れない(`SEPARATION.md` の段階2で、非公開の置き場を用意)。

- 子セッションの開始: 2026-11-28(session_015qHeRAtiUF6hSmpjXFFQzD)。最初の報告(現在地・未承認事項・次の作業を3行ずつ)を待つ。

- 第3のプロジェクト(2026-11-28 新設): **Global Demand & AI Business Research** — 世界の購買需要とAI実現可能性の研究、消去法の候補選別、新規事業の考案、商機の供給。記録: `docs/projects/global_demand/`(README=目的・連携・規律、CANDIDATES=候補台帳、OPPORTUNITY_HANDOFF=親へ渡す商機、START_PROMPT)。親の「世界の他市場の調査」は、この新プロジェクトの出発点の資産で、以後の市場探索・候補選別の主担当は新プロジェクト。親は、商業実験・測定・自律ループに専念する(作業は継続)。
