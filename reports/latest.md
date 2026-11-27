# YouTube市場調査レポート
生成: 2026-11-27T21:22:32Z (UTC) / 対象: 公開90日以内・50,000再生以上・音楽除外

## 重要な変化

- **drama_story:llm:2026-11-27T21:22:32Z:0**: untested → **insufficient_data** — Drama story's 16k baseline median comes from hit-skewed Japanese narration queries. With 250 or more baseline videos, including Spanish and Portuguese narrated stories, the baseline median falls to 5,000 views or below. That would mean a typical new drama upload earns little even though the hit rate looks high. `{"base_median": 16114, "base_videos": 149}`
- **trivia:llm:2026-11-27T21:22:32Z:1**: untested → **insufficient_data** — Trivia's 0.26 video-level base hit rate (248 videos) is inflated by popular Japanese 雑学 queries. With 350 or more baseline videos, including Hindi and English fact content, the base hit rate falls to 0.15 or below. `{"base_hit_rate": 0.25806451612903225, "base_videos": 248}`
- **asset_building:llm:2026-11-27T21:22:32Z:2**: untested → **insufficient_data** — Japanese asset-building looks open today (top-3 share 0.27), but NISA-era demand is consolidating. With 200 or more hit channels sampled, the top-3 share rises to 0.35 or above. `{"top3_share": 0.26843369854721194, "channels_with_hits": 163}`
- **ai_film:llm:2026-11-27T21:22:32Z:3**: untested → **insufficient_data** — AI film hits are shrinking as generation tools flood the space. With 260 or more hit channels sampled, the median long-form hit median falls to 30,000 views or below, down from about 67k. `{"median_long_median": 67010.5, "channels_with_hits": 205}`
- **history:llm:2026-11-27T21:22:32Z:4**: untested → **insufficient_data** — History's 259 replicable channels overstate repeatability. With 550 or more audited channels, including Spanish and obscure-topic queries, the replicable rate falls to 0.45 or below, down from 0.58. That would mean many history hits are one-offs. `{"replicable_rate": 0.5807174887892377, "audited_channels": 446}`
- **biology_nature:llm:2026-11-27T21:22:32Z:5**: untested → **insufficient_data** — Biology/nature's 21 replicable new channels are survivors. With 300 or more baseline channels, the channel-level hit rate falls to 0.10 or below, down from 0.15. `{"base_channel_hit_rate": 0.15178571428571427, "base_channels": 224}`

## 累計カウント

| 指標 | 値 |
|---|---|
| 調査テーマ数 | 330 |
| 稼働中テーマ | 330 |
| 停止テーマ(低収穫) | 0 |
| 検索実行回数 | 386 |
| 検索結果(延べ) | 17,409 |
| 重複排除件数(延べ) | 3,780 |
| 動画(ユニーク) | 306,335 |
| 再生数スナップショット | 352,857 |
| 条件該当動画 | 137,543 |
| チャンネル(ユニーク) | 6,444 |
| 監査済み(確認済み)チャンネル | 4,106 |
| 未監査(未確認)ヒットチャンネル | 413 |
| APIクォータ消費累計 | 61,020 |
| 記録エラー累計 | 1 |

### 今回の実行

```
{
 "searches": 0,
 "search_results": 0,
 "new_videos": 0,
 "duplicate_videos": 28,
 "new_channels": 0,
 "channels_audited": 0,
 "audit_videos": 0,
 "refreshed": 2500,
 "music_excluded": 0,
 "date_samples": 3,
 "date_sample_videos": 150,
 "errors": 0,
 "stopped_by": null,
 "units_this_run": 353,
 "quota_remaining_today": 1542,
 "expanded_topics": 4
}
```

## データ項目の確認状況

| 項目 | 状態 | 根拠 |
|---|---|---|
| タイトル/ID/チャンネル/公開日時/尺/再生数/取得日時 | 確認済み | YouTube Data API v3 videos.list (取得時点値) |
| 登録者数 | 確認済み(取得時点の現在値のみ) | channels.list。公開時点の登録者数は取得不能 → 未確認 |
| 投稿頻度・直近90日投稿・中央値・5万以上割合 | 監査済みチャンネルのみ確認済み | uploads再生リスト全件 (上限200本、超過時は範囲を記録) |
| Shorts判定 | 推定 | APIにShortsフラグ無し。≤60秒=Shorts濃厚、61-180秒=判定保留 |
| AI制作の可能性 | 推定(シグナルのみ) | status.containsSyntheticMedia(本人申告、返らない場合多い)+タイトル/説明/タグのキーワード |
| 収益化状況 | 未確認 | 公式APIに第三者チャンネルの収益化情報は無い |
| 市場全体の成功確率 | 算出しない | 検索は上位結果の抽出サンプルであり母集団ではない |


## ジャンル別の調査の進み具合(判定には監査済みチャンネル8以上が必要)

| ジャンル | テーマ数 | 実行済み検索 | 監査済みチャンネル | 判定可能まで |
|---|---|---|---|---|
| side_income | 1 | 1 | 3 | あと5チャンネル |
| aga_hair | 1 | 1 | 4 | あと4チャンネル |
| grooming_men | 3 | 3 | 9 | 判定可能 |
| midlife_men | 3 | 3 | 10 | 判定可能 |
| philosophy | 1 | 1 | 10 | 判定可能 |
| relaxing_visual | 1 | 1 | 12 | 判定可能 |
| sports_story | 1 | 1 | 15 | 判定可能 |
| asmr_process | 1 | 1 | 16 | 判定可能 |
| de_misc | 1 | 1 | 16 | 判定可能 |
| cars_machines | 1 | 1 | 22 | 判定可能 |
| economics | 3 | 3 | 25 | 判定可能 |
| sleep_health | 2 | 2 | 26 | 判定可能 |
| korea_misc | 1 | 1 | 31 | 判定可能 |
| personal_finance | 2 | 2 | 32 | 判定可能 |
| math_logic | 2 | 2 | 33 | 判定可能 |
| health_body | 2 | 2 | 38 | 判定可能 |
| psychology | 2 | 2 | 44 | 判定可能 |
| fr_misc | 2 | 2 | 45 | 判定可能 |
| relationships_dating | 6 | 6 | 45 | 判定可能 |
| infrastructure | 3 | 3 | 47 | 判定可能 |
| tech_explain | 3 | 3 | 51 | 判定可能 |
| sex_trivia_edu | 12 | 11 | 55 | 判定可能 |
| kids_edu | 3 | 3 | 59 | 判定可能 |
| space | 2 | 2 | 59 | 判定可能 |
| comparison_data | 3 | 3 | 62 | 判定可能 |
| ai_news_tools | 2 | 2 | 70 | 判定可能 |
| mens_sexual_health | 8 | 8 | 81 | 判定可能 |
| travel_culture | 8 | 8 | 86 | 判定可能 |
| biology_nature | 5 | 4 | 96 | 判定可能 |
| true_crime | 9 | 8 | 97 | 判定可能 |
| language_learning | 5 | 5 | 101 | 判定可能 |
| science | 5 | 5 | 103 | 判定可能 |
| religion_myth | 16 | 9 | 106 | 判定可能 |
| diy_craft | 4 | 4 | 113 | 判定可能 |
| scifi_story | 5 | 5 | 120 | 判定可能 |
| drama_story | 30 | 9 | 123 | 判定可能 |
| maps_geo | 9 | 9 | 144 | 判定可能 |
| horror_mystery | 7 | 7 | 145 | 判定可能 |
| asset_building | 21 | 12 | 148 | 判定可能 |
| trivia | 16 | 11 | 171 | 判定可能 |
| cozy_life | 8 | 8 | 172 | 判定可能 |
| aviation_military | 8 | 8 | 173 | 判定可能 |
| gaming_lore | 9 | 9 | 187 | 判定可能 |
| indonesia_misc | 23 | 9 | 191 | 判定可能 |
| ai_film | 9 | 9 | 199 | 判定可能 |
| cooking | 14 | 10 | 240 | 判定可能 |
| history | 47 | 46 | 446 | 判定可能 |

## ジャンル別 (観測サンプル)

| ジャンル | ヒットch | 監査済 | 再現性ch | 再現率 | 新規ch再現 | 小規模ch再現 | 上位3占有 | 長尺中央値の中央値 | 週投稿中央値 | AIシグナルch | 新着標本ch | 新着標本で5万到達ch率 | 新着標本中央値 | 言語 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| history | 483 | 446 | 259 | 58% | 63 | 107 | 29% | 38,343 | 3.0 | 3 | 446 | 22% | 1,154 | {'en': 234, 'ja': 108, 'es': 70, 'pt': 33, 'hi': 25} |
| cooking | 249 | 240 | 182 | 76% | 15 | 35 | 19% | 69,351 | 3.5 | 0 | 48 | 40% | 28,993 | {'en': 90, 'ja': 88, 'id': 24, 'hi': 23, 'es': 13} |
| indonesia_misc | 206 | 191 | 147 | 77% | 34 | 28 | 15% | 199,566 | 3.9 | 1 | 0 | — | — | {'id': 154, 'en': 34, 'hi': 7, 'ms': 4, 'ne': 2} |
| gaming_lore | 202 | 187 | 136 | 73% | 17 | 57 | 22% | 105,836 | 3.0 | 0 | 0 | — | — | {'en': 94, 'ja': 86, 'es': 19, 'zxx': 1, 'pt': 1} |
| trivia | 188 | 171 | 129 | 75% | 16 | 49 | 17% | 81,790 | 4.0 | 1 | 186 | 30% | 1,712 | {'ja': 97, 'en': 65, 'hi': 7, 'es': 5, 'ko': 5} |
| cozy_life | 192 | 172 | 114 | 66% | 42 | 43 | 18% | 64,152 | 2.4 | 2 | 280 | 18% | 1,467 | {'en': 124, 'zh': 32, 'hi': 14, 'ja': 8, 'zxx': 3} |
| maps_geo | 173 | 144 | 104 | 72% | 28 | 63 | 32% | 17,316 | 4.1 | 0 | 68 | 12% | 1,296 | {'en': 116, 'hi': 30, 'ja': 10, 'te': 3, 'ur': 3} |
| drama_story | 136 | 123 | 104 | 85% | 35 | 50 | 38% | 76,035 | 3.8 | 1 | 104 | 39% | 16,114 | {'ja': 70, 'en': 26, 'es': 19, 'pt': 13, 'bn': 2} |
| ai_film | 205 | 199 | 103 | 52% | 43 | 62 | 19% | 67,010 | 1.6 | 74 | 82 | 21% | 1,340 | {'en': 121, 'ja': 48, 'hi': 17, 'ru': 3, 'id': 2} |
| asset_building | 163 | 148 | 102 | 69% | 22 | 46 | 27% | 76,110 | 2.8 | 1 | 251 | 23% | 1,518 | {'ja': 144, 'en': 6, 'de': 4, 'id': 3, 'zxx': 2} |
| horror_mystery | 157 | 145 | 89 | 61% | 23 | 36 | 51% | 109,098 | 2.2 | 0 | 135 | 10% | 318.0 | {'en': 68, 'ja': 42, 'hi': 38, 'ur': 2, 'bn': 2} |
| aviation_military | 204 | 173 | 88 | 51% | 17 | 35 | 16% | 47,656 | 2.5 | 1 | 0 | — | — | {'en': 148, 'hi': 29, 'es': 11, 'id': 4, 'ur': 4} |
| true_crime | 135 | 97 | 71 | 73% | 8 | 10 | 22% | 316,590 | 2.5 | 1 | 0 | — | — | {'en': 109, 'hi': 10, 'es': 4, 'fil': 2, 'fr': 2} |
| diy_craft | 116 | 113 | 64 | 57% | 17 | 20 | 24% | 55,062 | 2.5 | 1 | 83 | 20% | 941 | {'en': 107, 'hi': 7, 'vi': 1, 'zxx': 1} |
| religion_myth | 109 | 106 | 57 | 54% | 14 | 26 | 52% | 54,466 | 2.5 | 0 | 0 | — | — | {'en': 44, 'ja': 36, 'hi': 16, 'es': 6, 'bn': 3} |
| science | 107 | 103 | 55 | 53% | 15 | 13 | 40% | 13,363 | 3.6 | 0 | 287 | 13% | 1,029 | {'en': 60, 'hi': 28, 'ja': 14, 'ml': 1, 'ta': 1} |
| travel_culture | 96 | 86 | 52 | 60% | 20 | 38 | 45% | 25,172 | 3.0 | 1 | 0 | — | — | {'ja': 62, 'en': 25, 'de': 2, 'zxx': 2, 'da': 1} |
| scifi_story | 122 | 120 | 47 | 39% | 22 | 24 | 43% | 19,043 | 3.5 | 13 | 106 | 9% | 328 | {'en': 110, 'hi': 6, 'ja': 2, 'ta': 2, 'ur': 1} |
| language_learning | 108 | 101 | 46 | 46% | 18 | 17 | 61% | 22,421 | 3.7 | 1 | 45 | 7% | 802.5 | {'en': 73, 'ja': 22, 'hi': 5, 'zxx': 2, 'ar': 2} |
| biology_nature | 105 | 96 | 45 | 47% | 21 | 32 | 27% | 14,259 | 4.4 | 1 | 224 | 15% | 1,062 | {'en': 54, 'ja': 34, 'hi': 8, 'zh': 4, 'bn': 2} |
| kids_edu | 63 | 59 | 44 | 75% | 8 | 8 | 45% | 285,168 | 3.1 | 0 | 0 | — | — | {'en': 55, 'hi': 5, 'ar': 2, 'zxx': 1} |
| ai_news_tools | 74 | 70 | 40 | 57% | 1 | 9 | 61% | 60,396 | 2.6 | 13 | 47 | 19% | 1,084 | {'en': 32, 'ja': 30, 'hi': 9, 'ta': 2, 'te': 1} |
| mens_sexual_health | 96 | 81 | 36 | 44% | 3 | 7 | 31% | 55,579 | 3.7 | 0 | 228 | 4% | 307 | {'en': 57, 'hi': 12, 'ja': 11, 'ur': 3, 'pt': 3} |
| space | 60 | 59 | 35 | 59% | 5 | 15 | 39% | 68,029 | 2.5 | 2 | 179 | 7% | 877.5 | {'en': 30, 'ja': 22, 'hi': 7, 'zxx': 1} |
| comparison_data | 66 | 62 | 34 | 55% | 10 | 22 | 76% | 28,809 | 1.6 | 0 | 0 | — | — | {'en': 65, 'zxx': 1} |
| fr_misc | 50 | 45 | 33 | 73% | 6 | 11 | 33% | 94,768 | 2.5 | 0 | 0 | — | — | {'fr': 40, 'en': 9, 'ur': 1} |
| tech_explain | 56 | 51 | 24 | 47% | 7 | 14 | 45% | 7,392 | 4.1 | 2 | 41 | 7% | 110.5 | {'en': 46, 'hi': 4, 'ta': 1, 'de': 1, 'te': 1} |
| infrastructure | 52 | 47 | 23 | 49% | 8 | 11 | 35% | 14,040 | 3.3 | 0 | 65 | 12% | 1,527 | {'en': 37, 'hi': 7, 'ja': 5, 'te': 2, 'bn': 1} |
| sex_trivia_edu | 67 | 55 | 23 | 42% | 4 | 7 | 37% | 18,494 | 3.0 | 1 | 131 | 4% | 669.5 | {'ja': 24, 'en': 22, 'hi': 8, 'zh': 4, 'ta': 2} |
| psychology | 47 | 44 | 19 | 43% | 6 | 4 | 59% | 55,734 | 4.2 | 0 | 155 | 7% | 548 | {'en': 29, 'ja': 14, 'hi': 2, 'te': 1, 'zxx': 1} |
| sleep_health | 34 | 26 | 16 | 62% | 2 | 10 | 66% | 35,548 | 4.3 | 0 | 64 | 2% | 219 | {'ja': 32, 'zh': 1, 'en': 1} |
| math_logic | 49 | 33 | 16 | 48% | 1 | 2 | 50% | 27,981 | 5.7 | 1 | 40 | 22% | 1,694 | {'en': 26, 'hi': 22, 'zxx': 1} |
| health_body | 42 | 38 | 16 | 42% | 6 | 9 | 43% | 8,750 | 4.3 | 0 | 0 | — | — | {'en': 27, 'ja': 13, 'tr': 1, 'hi': 1} |
| relationships_dating | 52 | 45 | 15 | 33% | 9 | 10 | 35% | 13,993 | 4.0 | 0 | 182 | 12% | 565 | {'ja': 27, 'en': 20, 'hi': 3, 'ml': 1, 'ur': 1} |
| personal_finance | 36 | 32 | 15 | 47% | 0 | 0 | 40% | 59,315 | 4.0 | 0 | 46 | 2% | 181.5 | {'en': 20, 'hi': 11, 'ta': 2, 'te': 2, 'ml': 1} |
| economics | 31 | 25 | 13 | 52% | 0 | 2 | 38% | 92,583 | 2.6 | 1 | 53 | 6% | 86 | {'ja': 24, 'en': 5, 'hi': 2} |
| korea_misc | 33 | 31 | 13 | 42% | 7 | 9 | 63% | 21,429 | 3.2 | 0 | 0 | — | — | {'ko': 32, 'en': 1} |
| cars_machines | 24 | 22 | 12 | 55% | 6 | 7 | 58% | 1,374 | 4.7 | 0 | 0 | — | — | {'en': 24} |
| sports_story | 17 | 15 | 11 | 73% | 2 | 4 | 54% | 96,640 | 6.0 | 0 | 0 | — | — | {'en': 14, 'de': 1, 'hi': 1, 'ur': 1} |
| de_misc | 19 | 16 | 9 | 56% | 1 | 3 | 52% | 62,585 | 4.0 | 0 | 0 | — | — | {'de': 16, 'en': 2, 'hi': 1} |
| midlife_men | 10 | 10 | 6 | 60% | 0 | 3 | 81% | 55,102 | 1.2 | 0 | 60 | 8% | 1,301 | {'ja': 10} |
| asmr_process | 19 | 16 | 5 | 31% | 1 | 1 | 82% | 2,309 | 4.8 | 0 | 0 | — | — | {'en': 18, 'gu': 1} |
| grooming_men | 9 | 9 | 4 | 44% | 0 | 2 | 64% | 55,865 | 4.4 | 0 | 77 | 6% | 720.0 | {'ja': 4, 'es': 3, 'en': 2} |
| relaxing_visual | 12 | 12 | 4 | 33% | 0 | 1 | 79% | 15,578 | 2.0 | 0 | 0 | — | — | {'en': 12} |
| aga_hair | 5 | 4 | 3 | 75% | 0 | 0 | 98% | 76,561 | 3.0 | 0 | 31 | 6% | 355 | {'ja': 5} |
| side_income | 3 | 3 | 1 | 33% | 0 | 0 | 100% | 59,988 | 0.3 | 0 | 25 | 0% | 325.0 | {'ja': 3} |
| philosophy | 12 | 10 | 1 | 10% | 0 | 1 | 70% | 1,070 | 2.5 | 0 | 0 | — | — | {'en': 12} |

再現性の定義: 監査済み・成熟投稿(公開14日以上)5本以上・中央値20,000以上・50,000以上割合30%以上
新着標本: 検索の25%を新着順(公開14〜60日)に充て、伸びなかった投稿も含む典型的な成果を観測(人気順検索だけでは成功例しか見えないため)。

## 再現性のある新興・小規模チャンネル (監査済み)

| チャンネル | ジャンル | 登録者(現在) | 開設日数 | 90日投稿 | 週投稿 | 長尺中央値 | Shorts中央値 | 5万以上割合 | 中央値再生/日 | AIシグナル | 言語 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| [Custki](https://www.youtube.com/channel/UCieWWOnmFlS6HGIz9vz0fOg) | drama_story | 1,060,000 | 231.5 | 136 | 10.6 | 889,824 | — | 100% | 231,583 | 0% | pt |
| [OXPRESS](https://www.youtube.com/channel/UCbYbjEHqUII2-QTG-bboOpg) | trivia | 140,000 | 90.9 | 33 | 2.6 | 3,010 | 9,593,332 | 89% | 211,271 | 0% | en |
| [Itik Films](https://www.youtube.com/channel/UCvsf_fhzRRhyV4e6lWeTgAA) | indonesia_misc | 91,600 | 570.1 | 42 | 3.3 | — | 94,265 | 100% | 196,543 | 0% | id |
| [Farming Friends ](https://www.youtube.com/channel/UCHSCFGxhRWbiEK_Z2NatwrQ) | history | 477,000 | 256.3 | 13 | 1.0 | — | 5,279,518 | 100% | 123,694 | 0% | en |
| [Joaquin](https://www.youtube.com/channel/UCghCDxrKdIemWrVXYqRqNSA) | trivia | 25,600 | 1,868 | 29 | 2.3 | — | 200,861 | 87% | 118,078 | 0% | en |
| [Cine Drop ](https://www.youtube.com/channel/UC4SxGZTAzPFbllLRL5ANrzw) | ai_film | 170,000 | 193.4 | 9 | 0.7 | 3,310,226 | — | 100% | 104,150 | 11% | en |
| [konon](https://www.youtube.com/channel/UChlXXJxfcdo5CEg77T-miFw) | indonesia_misc | 101,000 | 24.3 | 76 | 21.9 | 453,086 | — | 100% | 101,849 | 0% | id |
| [𝐏𝐀𝐑𝐈𝐁𝐇𝐑𝐀𝐌𝐀𝐍
](https://www.youtube.com/channel/UC3FBVOptsNFzWvGQUJPiFGQ) | history | 46,300 | 60.3 | 10 | 1.2 | — | 48,651 | 75% | 83,026 | 0% | en |
| [duly](https://www.youtube.com/channel/UC4vPEeVdWnA4Al_qqP3P3zg) | trivia | 86,700 | 401.3 | 12 | 0.9 | — | 3,232,336 | 100% | 76,074 | 0% | ja |
| [War From Above](https://www.youtube.com/channel/UC8fHc_-udAcgXP03OaWmxAw) | history | 7,720 | 23.9 | 7 | 2.0 | — | 569,637 | 80% | 71,132 | 0% | en |
| [Milyty](https://www.youtube.com/channel/UC4KFqHylsvG4heP9L8YUbFQ) | indonesia_misc | 45,700 | 3,995 | 9 | 0.7 | — | — | 100% | 71,002 | 0% | id |
| [Anant Gatha](https://www.youtube.com/channel/UCs4f9NfsDd0RLwzu9Of0hYA) | ai_film | 65,400 | 259.1 | 5 | 0.4 | 3,104,936 | — | 100% | 68,264 | 0% | hi |
| [Nona Film](https://www.youtube.com/channel/UCJoREhqNTbsYGhv96dDHIuA) | indonesia_misc | 745,000 | 361.3 | 73 | 5.7 | — | — | 100% | 59,549 | 0% | id |
| [MapLore](https://www.youtube.com/channel/UC6SMANr0NH7I8wsHGkF-oKw) | aviation_military | 103,000 | 232.2 | 14 | 1.1 | 13,851 | — | 85% | 54,869 | 0% | en |
| [Neural Pictures](https://www.youtube.com/channel/UCS97ctTfb7CxQvUGCAfbu2g) | ai_film | 44,200 | 658.2 | 11 | 0.9 | 885,344 | — | 100% | 54,502 | 9% | en |
| [sci sky](https://www.youtube.com/channel/UCLBwTFiWcpkEdu9VZp6rHPg) | history | 30,200 | 149.3 | 6 | 0.5 | — | 8,200,926 | 67% | 53,931 | 0% | en |
| [Street Food Records](https://www.youtube.com/channel/UCDQmK9db_mvSs7wE6DFnSbQ) | cooking | 448,000 | 361.2 | 105 | 8.2 | 1,936,891 | 1,080 | 97% | 52,866 | 0% | zh |
| [BoNaNu Kids Show Indonesia](https://www.youtube.com/channel/UCIQPlMOqVdfGIdWwI6W-5BQ) | indonesia_misc | 16,500 | 60.6 | 13 | 1.5 | 1,144,576 | — | 100% | 48,786 | 0% | id |
| [Verzen](https://www.youtube.com/channel/UCaLi86B4gWe0f_eoQJtf9Bg) | gaming_lore | 59,700 | 321.0 | 185 | 14.4 | — | 995,962 | 93% | 48,536 | 0% | en |
| [じんわり劇場](https://www.youtube.com/channel/UCFncJjz2MDCCbBgm-uaZVlA) | drama_story | 72,400 | 126.6 | 31 | 2.4 | 2,944 | 91,767 | 96% | 47,867 | 3% | ja |
| [Born in Lore](https://www.youtube.com/channel/UCBV6H_ZzQHW8O1h7NoiaW_w) | gaming_lore | 50,800 | 30.9 | 10 | 2.3 | 877,270 | — | 83% | 46,802 | 0% | en |
| [Bang Bang Monkey Song](https://www.youtube.com/channel/UCH8VMfAr2k7R8xVpla10V0w) | kids_edu | 191,000 | 223.5 | 28 | 2.2 | 177,410 | — | 96% | 45,013 | 0% | en |
| [pio the platypus](https://www.youtube.com/channel/UC9WD7bBsWR1r6qwiazpNw3g) | indonesia_misc | 560,000 | 318.7 | 85 | 6.6 | — | 1,907,035 | 100% | 42,981 | 0% | en |
| [manishpedia](https://www.youtube.com/channel/UCvg9dw7JbzQJ34pFQPRbEEg) | history | 223,000 | 168.2 | 32 | 2.5 | — | — | 100% | 42,934 | 0% | en |
| [DSP WCNM](https://www.youtube.com/channel/UCPEli8cAabN8Y9dpNMSsURA) | scifi_story | 954,000 | 329.3 | 45 | 3.5 | — | — | 97% | 42,072 | 0% | en |
| [Glowey / جلوي](https://www.youtube.com/channel/UCxPfD5eFKqZAC2mTxB5eDCA) | horror_mystery | 253,000 | 332.2 | 176 | 13.7 | — | 1,818,163 | 99% | 41,843 | 0% | ar |
| [Upin & Ipin Indonesia](https://www.youtube.com/channel/UCWaLBLeUqzZGC8EmGVDkkUg) | indonesia_misc | 176,000 | 116.8 | 49 | 3.8 | 1,801,312 | — | 100% | 37,846 | 0% | ms |
| [JejakBaik](https://www.youtube.com/channel/UC1rdhbuffhk-SUeyiRg6awQ) | indonesia_misc | 32,800 | 102.6 | 37 | 2.9 | — | — | 79% | 37,615 | 0% | id |
| [NontonAja](https://www.youtube.com/channel/UCj4MhwP0DxeupPuhzRnoNUw) | indonesia_misc | 20,600 | 577.1 | 26 | 2.0 | — | — | 95% | 37,504 | 0% | id |
| [Maizen Buddies](https://www.youtube.com/channel/UCB8asM8oQ7OA0vCNOXvknlA) | trivia | 193,000 | 246.4 | 39 | 3.0 | — | 236,671 | 96% | 36,242 | 0% | en |
| [Lam Studio](https://www.youtube.com/channel/UCu0QY539In5OLbkhnouFmBA) | indonesia_misc | 108,000 | 35.0 | 61 | 12.2 | — | 19,486 | 84% | 35,962 | 0% | id |
| [Why Guy](https://www.youtube.com/channel/UC5epkgKdOu7NolxXuj2yylQ) | aviation_military | 237,000 | 333.2 | 27 | 2.1 | — | 1,680,404 | 100% | 35,387 | 0% | en |
| [World Ji Ke](https://www.youtube.com/channel/UCJHc62QVT61jSG07fjfswWg) | maps_geo | 90,600 | 202.4 | 17 | 1.3 | — | 1,328,056 | 100% | 34,658 | 0% | en |
| [RazoGames](https://www.youtube.com/channel/UCg_YbcTvBpnkHhoaHHOY4Pw) | true_crime | 5,810,000 | 193.0 | 32 | 2.5 | 1,763,036 | 5,037,171 | 100% | 33,780 | 0% | es |
| [Hidden Ops India](https://www.youtube.com/channel/UCRKosUcTVIsh5_-tQOynHSg) | ai_film | 118,000 | 251.2 | 11 | 0.9 | 1,466,262 | — | 100% | 32,974 | 0% | hi |
| [Kacaurus](https://www.youtube.com/channel/UCDZ3rFCPlQt4LtoAP-DECfw) | indonesia_misc | 167,000 | 25.9 | 111 | 30.0 | 26,737 | 103,718 | 84% | 32,227 | 0% | id |
| [ゲームの真実](https://www.youtube.com/channel/UCgQNAtZPmqgQeEo1vEVPcjA) | gaming_lore | 27,900 | 288.8 | 43 | 3.3 | — | 187,405 | 89% | 31,498 | 0% | ja |
| [Pointy](https://www.youtube.com/channel/UCELxG3jPs5m76TSU02qhBFg) | gaming_lore | 78,000 | 1,166 | 10 | 0.8 | — | 692,054 | 100% | 29,035 | 0% | en |
| [ゲームの裏話](https://www.youtube.com/channel/UCSKNX_MkXbD1buHb37pGReA) | gaming_lore | 56,300 | 1,379 | 58 | 4.5 | — | 446,102 | 96% | 28,777 | 0% | ja |
| [napon](https://www.youtube.com/channel/UCcudXpyoi1NJNB9zpa4uwNw) | indonesia_misc | 82,500 | 293.4 | 63 | 4.9 | 1,839,715 | — | 96% | 28,026 | 0% | id |

## 仮説一覧

| ID | 状態 | 内容 | 根拠 |
|---|---|---|---|
| aga_hair:entry | insufficient_data | 新規チャンネル(開設365日以内)でも再現性ある成功が複数存在する | `{"replicable_new_channels": 0, "audited_channels": 4}` |
| aga_hair:open | insufficient_data | 上位3チャンネルがヒット再生の60%未満(寡占ではない) | `{"top3_share": 0.9791560839107217, "channels_with_hits": 5}` |
| aga_hair:repl | insufficient_data | 監査済みヒットチャンネルの25%以上が単発でなく再現性を持つ | `{"replicable_rate": 0.75, "audited_channels": 4}` |
| ai_film:llm:2026-11-22T19:44:52Z:4 | insufficient_data | AI film is saturating as AI generation tools spread. With a baseline of 200 or more videos, the base hit rate drops to 10% or less, from 0.19. | `{"base_hit_rate": 0.19387755102040816, "base_videos": 98}` |
| ai_film:llm:2026-11-23T08:34:44Z:1 | insufficient_data | AI film is saturating as generation tools spread. Once the baseline covers 150 or more channels, the channel-level hit rate falls to 0.10 or below, so the 23 replicable new channels are survivors. | `{"base_channel_hit_rate": 0.2073170731707317, "base_channels": 82}` |
| ai_film:llm:2026-11-23T20:18:13Z:5 | insufficient_data | AI film is saturating: with 150 or more baseline channels, the channel-level hit rate falls to 0.10 or lower. | `{"base_channel_hit_rate": 0.2073170731707317, "base_channels": 82}` |
| ai_film:llm:2026-11-23T23:57:43Z:3 | insufficient_data | AI film is flooded with low-performing AI uploads. With 200 or more baseline videos, the baseline median falls to 800 views or fewer, so typical uploads do not monetise. | `{"base_median": 1340.5, "base_videos": 98}` |
| ai_film:llm:2026-11-24T08:17:19Z:5 | insufficient_data | AI film is saturating. With 150 or more baseline channels, the channel-level hit rate falls to 0.10 or below, so its 23 replicable new channels are survivors. | `{"base_channel_hit_rate": 0.2073170731707317, "base_channels": 82}` |
| ai_film:llm:2026-11-24T19:33:10Z:3 | insufficient_data | AI film's typical upload does not monetise. With 150 or more baseline videos, the baseline median falls to 800 views or fewer, down from about 1,340. | `{"base_median": 1340.5, "base_videos": 98}` |
| ai_film:llm:2026-11-25T18:50:32Z:5 | insufficient_data | AI film's replicability is fading as generation tools flood the space. With 200 or more channels audited, the replicable rate falls to 0.40 or below, down from 0.52. | `{"replicable_rate": 0.5175879396984925, "audited_channels": 199}` |
| ai_film:llm:2026-11-26T18:36:22Z:4 | insufficient_data | AI film is flooded with low-effort uploads. With 160 or more baseline videos, the baseline median falls to 800 views or below, down from about 1,340, so typical AI film uploads do not monetise. | `{"base_median": 1340.5, "base_videos": 98}` |
| ai_film:llm:2026-11-26T21:38:51Z:5 | insufficient_data | AI film is flooding with generated uploads. With 180 or more baseline videos, including Japanese and Hindi AI short films, the base hit rate falls to 0.12 or below, down from 0.19. | `{"base_hit_rate": 0.19387755102040816, "base_videos": 98}` |
| ai_film:llm:2026-11-27T21:22:32Z:3 | insufficient_data | AI film hits are shrinking as generation tools flood the space. With 260 or more hit channels sampled, the median long-form hit median falls to 30,000 views or below, down from about 67k. | `{"median_long_median": 67010.5, "channels_with_hits": 205}` |
| asmr_process:base | insufficient_data | 新着投稿の標本(生存者バイアス補正)でも、5万再生に届くチャンネルが10%以上ある | `{"base_channel_hit_rate": null, "base_channels": 0}` |
| asset_building:llm:2026-11-26T21:38:51Z:3 | insufficient_data | Japanese asset-building's typical upload is too small to monetise. With 400 or more baseline videos, the baseline median falls to 800 views or below, down from about 1,130. | `{"base_median": 1518, "base_videos": 327}` |
| asset_building:llm:2026-11-27T21:22:32Z:2 | insufficient_data | Japanese asset-building looks open today (top-3 share 0.27), but NISA-era demand is consolidating. With 200 or more hit channels sampled, the top-3 share rises to 0.35 or above. | `{"top3_share": 0.26843369854721194, "channels_with_hits": 163}` |
| aviation_military:base | insufficient_data | 新着投稿の標本(生存者バイアス補正)でも、5万再生に届くチャンネルが10%以上ある | `{"base_channel_hit_rate": null, "base_channels": 0}` |
| aviation_military:llm:2026-11-22T19:44:52Z:0 | insufficient_data | Aviation/military's 40 replicable hit channels are survivorship bias. In a random baseline of recent uploads, 8% or fewer reach 50k views in 90 days. | `{"base_hit_rate": null, "base_videos": 0}` |
| aviation_military:llm:2026-11-23T08:32:16Z:4 | insufficient_data | Aviation/military's low concentration and 59 replicable channels are survivorship bias. A random baseline gives a base hit rate of 0.07 or less. | `{"base_hit_rate": null, "base_videos": 0}` |
| aviation_military:llm:2026-11-23T20:18:13Z:3 | insufficient_data | Aviation/military's low concentration hides poor odds for typical uploaders: with 60 or more baseline videos, the base hit rate is 0.07 or lower. | `{"base_hit_rate": null, "base_videos": 0}` |
| biology_nature:llm:2026-11-27T21:22:32Z:5 | insufficient_data | Biology/nature's 21 replicable new channels are survivors. With 300 or more baseline channels, the channel-level hit rate falls to 0.10 or below, down from 0.15. | `{"base_channel_hit_rate": 0.15178571428571427, "base_channels": 224}` |
| cars_machines:base | insufficient_data | 新着投稿の標本(生存者バイアス補正)でも、5万再生に届くチャンネルが10%以上ある | `{"base_channel_hit_rate": null, "base_channels": 0}` |
| comparison_data:base | insufficient_data | 新着投稿の標本(生存者バイアス補正)でも、5万再生に届くチャンネルが10%以上ある | `{"base_channel_hit_rate": null, "base_channels": 0}` |
| cooking:llm:2026-11-23T23:57:43Z:0 | insufficient_data | Cooking's strong baseline (0.40 channel-level hit rate from only 48 channels) is a small-sample artifact driven by incumbents. With 100 or more baseline channels, the channel-level hit rate falls to 0.20 or lower. | `{"base_channel_hit_rate": 0.3958333333333333, "base_channels": 48}` |
| cooking:llm:2026-11-24T08:17:19Z:1 | insufficient_data | Cooking's 0.40 channel-level hit rate, measured on only 48 channels, is a small-sample artifact. With 100 or more baseline channels, it falls to 0.20 or below. | `{"base_channel_hit_rate": 0.3958333333333333, "base_channels": 48}` |
| cooking:llm:2026-11-25T18:50:32Z:2 | insufficient_data | Cooking's roughly 29k baseline median comes from a 49-video sample tilted toward incumbents. With 150 or more baseline videos, the baseline median falls to 5,000 views or below. | `{"base_median": 28993, "base_videos": 49}` |
| cooking:llm:2026-11-25T21:45:41Z:0 | insufficient_data | Cooking's 0.39 video-level base hit rate rests on only 49 videos, likely drawn from incumbent-heavy queries. With 150 or more baseline videos, the base hit rate falls to 0.20 or below, so typical new cooking uploads rarely reach 50k views. | `{"base_hit_rate": 0.3877551020408163, "base_videos": 49}` |
| cooking:llm:2026-11-26T18:36:22Z:1 | insufficient_data | Cooking's roughly 29k baseline median rests on 49 incumbent-tilted videos. With 150 or more baseline videos, the baseline median falls to 5,000 views or below. | `{"base_median": 28993, "base_videos": 49}` |
| cooking:llm:2026-11-26T21:38:51Z:1 | insufficient_data | Cooking's 0.39 base hit rate rests on only 49 videos. With 150 or more baseline videos from generic recipe queries, it falls to 0.20 or below, so typical new cooking uploads rarely reach 50k views. | `{"base_hit_rate": 0.3877551020408163, "base_videos": 49}` |
| cooking:llm:2026-11-27T18:23:43Z:1 | insufficient_data | Cooking's 0.39 base hit rate rests on only 49 incumbent-tilted videos. With 150 or more baseline videos from generic recipe queries, it falls to 0.20 or below. | `{"base_hit_rate": 0.3877551020408163, "base_videos": 49}` |
| de_misc:base | insufficient_data | 新着投稿の標本(生存者バイアス補正)でも、5万再生に届くチャンネルが10%以上ある | `{"base_channel_hit_rate": null, "base_channels": 0}` |
| diy_craft:llm:2026-11-24T22:30:39Z:3 | insufficient_data | DIY/craft's 0.20 base hit rate is a small-sample artifact from 97 videos. With 180 or more baseline videos, it falls to 0.12 or below. | `{"base_hit_rate": 0.1958762886597938, "base_videos": 97}` |
| diy_craft:llm:2026-11-25T18:50:32Z:4 | insufficient_data | DIY/craft's typical upload performs weakly, even though 59 hit channels are replicable. With 180 or more baseline videos, the baseline median falls to 600 views or below. | `{"base_median": 941, "base_videos": 97}` |
| drama_story:llm:2026-11-22T16:20:55Z:3 | insufficient_data | Drama story's 0.46 baseline hit rate is inflated by the small sample (100 videos). With more baseline videos, the rate falls to 30% or less. | `{"base_hit_rate": 0.38926174496644295, "base_videos": 149}` |
| drama_story:llm:2026-11-22T19:44:52Z:2 | insufficient_data | Drama story's 0.49 channel-level hit rate comes from a small, hit-skewed baseline. With 120 or more baseline channels, it falls to 0.30 or below. | `{"base_channel_hit_rate": 0.3942307692307692, "base_channels": 104}` |
| drama_story:llm:2026-11-23T08:32:16Z:0 | insufficient_data | Drama story's 0.46 baseline hit rate comes from a small, hit-skewed sample. With 200 or more baseline videos, the base hit rate falls to 0.25 or below, refuting its status as the most accessible niche. | `{"base_hit_rate": 0.38926174496644295, "base_videos": 149}` |
| drama_story:llm:2026-11-23T08:34:44Z:0 | insufficient_data | Drama story's 0.46 baseline hit rate is inflated by a small, hit-skewed sample. With 200 or more baseline videos, the base hit rate falls to 0.25 or below, removing its status as the most accessible niche. | `{"base_hit_rate": 0.38926174496644295, "base_videos": 149}` |
| drama_story:llm:2026-11-23T20:18:13Z:1 | insufficient_data | Drama story's 0.46 base hit rate comes from a small, hit-skewed sample: with 200 or more baseline videos, it falls to 0.25 or lower. | `{"base_hit_rate": 0.38926174496644295, "base_videos": 149}` |
| drama_story:llm:2026-11-24T08:17:19Z:0 | insufficient_data | Drama story's 0.46 base hit rate comes from a small sample that skews toward hits. With 200 or more baseline videos, the base hit rate falls to 0.25 or below, refuting its status as the most accessible niche. | `{"base_hit_rate": 0.38926174496644295, "base_videos": 149}` |
| drama_story:llm:2026-11-24T19:33:10Z:0 | insufficient_data | Drama story's 0.39 channel-level hit rate (104 channels) is inflated by hit-skewed queries. With 150 or more baseline channels, it falls to 0.25 or below. | `{"base_channel_hit_rate": 0.3942307692307692, "base_channels": 104}` |
| drama_story:llm:2026-11-26T18:36:22Z:0 | insufficient_data | Drama story's 0.39 channel-level hit rate (104 channels) comes from hit-skewed queries. With 180 or more baseline channels, it falls to 0.25 or below, so drama is not the most accessible niche. | `{"base_channel_hit_rate": 0.3942307692307692, "base_channels": 104}` |
| drama_story:llm:2026-11-26T21:38:51Z:0 | insufficient_data | Drama story's 0.39 base hit rate comes from 149 videos drawn by hit-skewed queries. Adding neutral Spanish and Portuguese narrated-story queries to reach 250 or more baseline videos pushes the base hit rate to 0.25 or below, so drama is not reliably accessible to a new channel. | `{"base_hit_rate": 0.38926174496644295, "base_videos": 149}` |
| drama_story:llm:2026-11-27T18:23:43Z:0 | insufficient_data | Drama story's 0.39 channel-level hit rate comes from hit-skewed Japanese narration queries. With 180 or more baseline channels, it falls to 0.25 or below, so drama is not reliably accessible to a new channel. | `{"base_channel_hit_rate": 0.3942307692307692, "base_channels": 104}` |
| drama_story:llm:2026-11-27T21:22:32Z:0 | insufficient_data | Drama story's 16k baseline median comes from hit-skewed Japanese narration queries. With 250 or more baseline videos, including Spanish and Portuguese narrated stories, the baseline median falls to 5,000 views or below. That would mean a typical new drama upload earns little even though the hit rate looks high. | `{"base_median": 16114, "base_videos": 149}` |
| fr_misc:base | insufficient_data | 新着投稿の標本(生存者バイアス補正)でも、5万再生に届くチャンネルが10%以上ある | `{"base_channel_hit_rate": null, "base_channels": 0}` |
| fr_misc:llm:2026-11-22T19:44:52Z:5 | insufficient_data | French content's 0.84 replicable rate reflects established creators only. In a random baseline of recent French uploads, 8% or fewer reach 50k views. | `{"base_hit_rate": null, "base_videos": 0}` |
| gaming_lore:base | insufficient_data | 新着投稿の標本(生存者バイアス補正)でも、5万再生に届くチャンネルが10%以上ある | `{"base_channel_hit_rate": null, "base_channels": 0}` |
| gaming_lore:llm:2026-11-22T09:49:53Z:0 | insufficient_data | Gaming lore's strong replicability (51 channels, 27 small) holds up in an unbiased baseline: at least 12% of randomly sampled recent gaming-lore uploads reach 50k views in 90 days. If the rate is lower, the hit-channel sample is survivorship bias. | `{"base_hit_rate": null, "base_videos": 0}` |
| gaming_lore:llm:2026-11-22T16:20:55Z:0 | insufficient_data | Gaming lore's replicability among hit channels is survivorship bias. In a random baseline sample of recent uploads, fewer than 10% of videos reach 50k views in 90 days. | `{"base_hit_rate": null, "base_videos": 0}` |
| gaming_lore:llm:2026-11-23T08:32:16Z:2 | insufficient_data | Gaming lore's strong hit-channel replicability (58 channels) is survivorship bias. A random baseline of recent uploads yields a base hit rate of 0.08 or less. | `{"base_hit_rate": null, "base_videos": 0}` |
| gaming_lore:llm:2026-11-23T08:34:44Z:3 | insufficient_data | Gaming lore's 58 replicable hit channels are survivorship bias. A random baseline of at least 60 recent uploads gives a base hit rate of 0.08 or less. | `{"base_hit_rate": null, "base_videos": 0}` |
| gaming_lore:llm:2026-11-23T20:18:13Z:0 | insufficient_data | Gaming lore's 58 replicable hit channels (31 small) are survivorship bias: in a random baseline of at least 60 recent uploads, the base hit rate is 0.08 or lower. | `{"base_hit_rate": null, "base_videos": 0}` |
| gaming_lore:llm:2026-11-24T08:17:19Z:2 | insufficient_data | Gaming lore's 57 replicable hit channels reflect survivorship bias. In a random baseline of 60 or more recent uploads, the base hit rate is 0.08 or below. | `{"base_hit_rate": null, "base_videos": 0}` |
| gaming_lore:llm:2026-11-25T21:45:41Z:1 | insufficient_data | Gaming lore's 70 replicable hit channels (39 small) may be survivors. With 50 or more baseline channels, the channel-level hit rate is 0.10 or below, meaning most lore uploaders never get a hit. | `{"base_channel_hit_rate": null, "base_channels": 0}` |
| gaming_lore:llm:2026-11-26T18:36:22Z:2 | insufficient_data | Gaming lore's 85 replicable hit channels (43 small) are survivors. With 60 or more baseline videos from neutral lore queries, the base hit rate is 0.08 or below. | `{"base_hit_rate": null, "base_videos": 0}` |
| gaming_lore:llm:2026-11-27T18:23:43Z:2 | insufficient_data | Gaming lore's 136 replicable hit channels are survivors. In a baseline of 60 or more recent uploads from neutral lore queries, the base hit rate is 0.08 or below. | `{"base_hit_rate": null, "base_videos": 0}` |
| health_body:base | insufficient_data | 新着投稿の標本(生存者バイアス補正)でも、5万再生に届くチャンネルが10%以上ある | `{"base_channel_hit_rate": null, "base_channels": 0}` |
| history:llm:2026-11-25T21:45:41Z:5 | insufficient_data | History's 66 replicable new channels are survivors of a crowded field. With 450 or more baseline channels, the channel-level hit rate falls to 0.12 or below. | `{"base_channel_hit_rate": 0.2219730941704036, "base_channels": 446}` |
| history:llm:2026-11-26T18:36:22Z:3 | insufficient_data | History's 0.20 base hit rate is inflated by popular-topic queries. With 550 or more baseline videos, including obscure-topic and non-English queries, it falls to 0.12 or below. | `{"base_hit_rate": 0.21369294605809128, "base_videos": 482}` |
| history:llm:2026-11-27T21:22:32Z:4 | insufficient_data | History's 259 replicable channels overstate repeatability. With 550 or more audited channels, including Spanish and obscure-topic queries, the replicable rate falls to 0.45 or below, down from 0.58. That would mean many history hits are one-offs. | `{"replicable_rate": 0.5807174887892377, "audited_channels": 446}` |
| indonesia_misc:base | insufficient_data | 新着投稿の標本(生存者バイアス補正)でも、5万再生に届くチャンネルが10%以上ある | `{"base_channel_hit_rate": null, "base_channels": 0}` |
| indonesia_misc:llm:2026-11-22T16:20:55Z:1 | insufficient_data | Indonesian content's 0.87 replicable rate reflects only established channels. Unbiased baseline uploads rarely hit, giving a base hit rate of 8% or less. | `{"base_hit_rate": null, "base_videos": 0}` |
| indonesia_misc:llm:2026-11-23T08:32:16Z:5 | insufficient_data | Indonesian content's 0.89 replicable rate belongs to established channels. Baseline uploads hit 50k at a rate of 0.08 or less. | `{"base_hit_rate": null, "base_videos": 0}` |
| indonesia_misc:llm:2026-11-24T19:33:10Z:1 | insufficient_data | Indonesian content's 0.89 replicable rate reflects established channels only. In a random baseline of 60 or more recent uploads, 10% or fewer reach 50k views in 90 days. | `{"base_hit_rate": null, "base_videos": 0}` |
| indonesia_misc:llm:2026-11-25T21:45:41Z:2 | insufficient_data | Indonesian content's huge hit-channel medians (about 333k long-form) hide weak typical economics. With 80 or more baseline videos, the baseline median is 2,000 views or below. | `{"base_median": null, "base_videos": 0}` |
| indonesia_misc:llm:2026-11-27T18:23:43Z:5 | insufficient_data | Indonesian content's huge hit-channel medians (about 200k long-form) hide weak typical economics. With 80 or more baseline videos, the baseline median is 2,000 views or below. | `{"base_median": null, "base_videos": 0}` |
| kids_edu:base | insufficient_data | 新着投稿の標本(生存者バイアス補正)でも、5万再生に届くチャンネルが10%以上ある | `{"base_channel_hit_rate": null, "base_channels": 0}` |
| kids_edu:llm:2026-11-25T21:45:41Z:4 | insufficient_data | Kids education's huge medians (about 480k long-form) belong to a few incumbents. In a random baseline of 60 or more recent uploads, the base hit rate is 0.10 or below. | `{"base_hit_rate": null, "base_videos": 0}` |
| korea_misc:base | insufficient_data | 新着投稿の標本(生存者バイアス補正)でも、5万再生に届くチャンネルが10%以上ある | `{"base_channel_hit_rate": null, "base_channels": 0}` |
| maps_geo:llm:2026-11-23T23:57:43Z:5 | insufficient_data | Maps/geo's 19 replicable small channels hide poor odds for typical uploaders. With 120 or more baseline channels, the channel-level hit rate is 0.08 or lower. | `{"base_channel_hit_rate": 0.11764705882352941, "base_channels": 68}` |
| maps_geo:llm:2026-11-26T18:36:22Z:5 | insufficient_data | Maps/geo's 55 replicable small channels hide poor odds for typical uploaders. With 120 or more baseline channels, the channel-level hit rate is 0.08 or below. | `{"base_channel_hit_rate": 0.11764705882352941, "base_channels": 68}` |
| maps_geo:llm:2026-11-26T21:38:51Z:4 | insufficient_data | Maps/geo's 55 replicable small channels hide poor odds for typical uploaders. With 180 or more baseline videos, including Hindi and other non-English queries, the base hit rate is 0.08 or below. | `{"base_hit_rate": 0.12121212121212122, "base_videos": 99}` |
| math_logic:llm:2026-11-25T18:50:32Z:1 | insufficient_data | Math/logic's 0.20 base hit rate rests on only 50 videos, and its hits are concentrated (top-3 share 0.69). With 120 or more baseline videos, the base hit rate falls to 0.10 or below. | `{"base_hit_rate": 0.2, "base_videos": 50}` |
| philosophy:base | insufficient_data | 新着投稿の標本(生存者バイアス補正)でも、5万再生に届くチャンネルが10%以上ある | `{"base_channel_hit_rate": null, "base_channels": 0}` |
| relaxing_visual:base | insufficient_data | 新着投稿の標本(生存者バイアス補正)でも、5万再生に届くチャンネルが10%以上ある | `{"base_channel_hit_rate": null, "base_channels": 0}` |
| religion_myth:base | insufficient_data | 新着投稿の標本(生存者バイアス補正)でも、5万再生に届くチャンネルが10%以上ある | `{"base_channel_hit_rate": null, "base_channels": 0}` |
| religion_myth:llm:2026-11-23T20:18:13Z:4 | insufficient_data | Religion/myth's 18 replicable small channels are survivors: with 60 or more baseline videos, the base hit rate is 0.07 or lower. | `{"base_hit_rate": null, "base_videos": 0}` |
| religion_myth:llm:2026-11-23T23:57:43Z:1 | insufficient_data | Religion/myth's 18 replicable small channels are survivors. With 50 or more baseline channels, 8% or fewer channels reach 50k views in 90 days. | `{"base_channel_hit_rate": null, "base_channels": 0}` |
| scifi_story:llm:2026-11-24T22:30:39Z:2 | insufficient_data | AI-assisted sci-fi stories (17 AI-signal channels, 13 replicable new) look open, but typical uploads fail. With 200 or more baseline videos, the base hit rate stays at or below 0.08. | `{"base_hit_rate": 0.08270676691729323, "base_videos": 133}` |
| side_income:base | insufficient_data | 新着投稿の標本(生存者バイアス補正)でも、5万再生に届くチャンネルが10%以上ある | `{"base_channel_hit_rate": 0.0, "base_channels": 25}` |
| side_income:entry | insufficient_data | 新規チャンネル(開設365日以内)でも再現性ある成功が複数存在する | `{"replicable_new_channels": 0, "audited_channels": 3}` |
| side_income:open | insufficient_data | 上位3チャンネルがヒット再生の60%未満(寡占ではない) | `{"top3_share": 1.0, "channels_with_hits": 3}` |
| side_income:repl | insufficient_data | 監査済みヒットチャンネルの25%以上が単発でなく再現性を持つ | `{"replicable_rate": 0.3333333333333333, "audited_channels": 3}` |
| sports_story:base | insufficient_data | 新着投稿の標本(生存者バイアス補正)でも、5万再生に届くチャンネルが10%以上ある | `{"base_channel_hit_rate": null, "base_channels": 0}` |
| travel_culture:base | insufficient_data | 新着投稿の標本(生存者バイアス補正)でも、5万再生に届くチャンネルが10%以上ある | `{"base_channel_hit_rate": null, "base_channels": 0}` |
| travel_culture:llm:2026-11-23T08:32:16Z:3 | insufficient_data | Travel/culture's 14 replicable new channels do not generalize. In an unbiased baseline, the channel-level hit rate is 0.10 or less. | `{"base_channel_hit_rate": null, "base_channels": 0}` |
| travel_culture:llm:2026-11-23T08:34:44Z:4 | insufficient_data | Travel/culture's 14 replicable new channels do not generalise. With 50 or more baseline channels, the channel-level hit rate is 0.10 or below. | `{"base_channel_hit_rate": null, "base_channels": 0}` |
| travel_culture:llm:2026-11-23T20:18:13Z:2 | insufficient_data | Travel/culture's 14 replicable new channels do not generalise: with 50 or more baseline channels, the channel-level hit rate is 0.10 or lower. | `{"base_channel_hit_rate": null, "base_channels": 0}` |
| travel_culture:llm:2026-11-24T08:17:19Z:3 | insufficient_data | Travel/culture's 14 replicable new channels do not generalise. With 50 or more baseline channels, the channel-level hit rate is 0.10 or below. | `{"base_channel_hit_rate": null, "base_channels": 0}` |
| trivia:llm:2026-11-26T21:38:51Z:2 | insufficient_data | Japanese trivia's 0.25 channel-level baseline hit rate (142 channels) is inflated by popular 雑学 queries. With 220 or more baseline channels, it falls to 0.15 or below. | `{"base_channel_hit_rate": 0.2956989247311828, "base_channels": 186}` |
| trivia:llm:2026-11-27T18:23:43Z:4 | insufficient_data | Trivia's 0.30 channel-level baseline hit rate is inflated by popular Japanese 雑学 queries. With 260 or more baseline channels, including English and Hindi fact channels, it falls to 0.15 or below. | `{"base_channel_hit_rate": 0.2956989247311828, "base_channels": 186}` |
| trivia:llm:2026-11-27T21:22:32Z:1 | insufficient_data | Trivia's 0.26 video-level base hit rate (248 videos) is inflated by popular Japanese 雑学 queries. With 350 or more baseline videos, including Hindi and English fact content, the base hit rate falls to 0.15 or below. | `{"base_hit_rate": 0.25806451612903225, "base_videos": 248}` |
| true_crime:base | insufficient_data | 新着投稿の標本(生存者バイアス補正)でも、5万再生に届くチャンネルが10%以上ある | `{"base_channel_hit_rate": null, "base_channels": 0}` |
| true_crime:llm:2026-11-24T19:33:10Z:2 | insufficient_data | True crime is closed to newcomers despite its 0.90 replicable rate. In a baseline of 60 or more recent uploads, 8% or fewer reach 50k views. | `{"base_hit_rate": null, "base_videos": 0}` |
| true_crime:llm:2026-11-27T18:23:43Z:3 | insufficient_data | True crime's high hit-channel medians (about 317k long-form) hide poor odds for typical uploaders. In a baseline of 60 or more recent uploads, 8% or fewer reach 50k views in 90 days. | `{"base_hit_rate": null, "base_videos": 0}` |
| aga_hair:base | refuted | 新着投稿の標本(生存者バイアス補正)でも、5万再生に届くチャンネルが10%以上ある | `{"base_channel_hit_rate": 0.06451612903225806, "base_channels": 31}` |
| ai_film:llm:2026-11-24T22:30:39Z:4 | refuted | AI film's low concentration (top-3 share 0.29) will not hold. With 130 or more hit channels sampled, the top-3 share rises to 0.40 or more as a few AI studios capture the views. | `{"top3_share": 0.19058412458658164, "channels_with_hits": 205}` |
| ai_news_tools:entry | refuted | 新規チャンネル(開設365日以内)でも再現性ある成功が複数存在する | `{"replicable_new_channels": 1, "audited_channels": 70}` |
| ai_news_tools:open | refuted | 上位3チャンネルがヒット再生の60%未満(寡占ではない) | `{"top3_share": 0.6059552804405044, "channels_with_hits": 74}` |
| asmr_process:entry | refuted | 新規チャンネル(開設365日以内)でも再現性ある成功が複数存在する | `{"replicable_new_channels": 1, "audited_channels": 16}` |
| asmr_process:open | refuted | 上位3チャンネルがヒット再生の60%未満(寡占ではない) | `{"top3_share": 0.8198213920041216, "channels_with_hits": 19}` |
| asset_building:llm:2026-11-24T22:30:39Z:0 | refuted | Japanese asset-building's 0.79 replicable rate belongs to incumbents. With 80 or more audited channels, replicable new channels stay at 8 or fewer, so the market is effectively closed to a new channel. | `{"replicable_new_channels": 22, "audited_channels": 148}` |
| asset_building:llm:2026-11-25T18:50:32Z:0 | refuted | Japanese asset-building's 0.21 channel-level baseline hit rate (140 channels) is driven by NISA-boom queries. With 250 or more baseline channels, it falls to 0.12 or below, so typical new uploaders rarely hit. | `{"base_channel_hit_rate": 0.22709163346613545, "base_channels": 251}` |
| biology_nature:llm:2026-11-24T22:30:39Z:5 | refuted | Biology/nature's 24 replicable new channels sit on low typical demand. With 300 or more baseline videos, the baseline median stays at or below 1,000 views. | `{"base_median": 1062.5, "base_videos": 300}` |
| comparison_data:open | refuted | 上位3チャンネルがヒット再生の60%未満(寡占ではない) | `{"top3_share": 0.7622549241006398, "channels_with_hits": 66}` |
| cooking:llm:2026-11-23T08:32:16Z:1 | refuted | Cooking's high baseline (hit rate 0.39, median about 29k) reflects incumbents. With more audits, replicable new channels stay at 6 or fewer, meaning new entrants rarely break in. | `{"replicable_new_channels": 15, "audited_channels": 240}` |
| cooking:llm:2026-11-23T08:34:44Z:5 | refuted | Cooking's strong baseline belongs to incumbents. Even with 120 or more channels audited, replicable new channels stay at 8 or fewer, meaning newcomers rarely break in. | `{"replicable_new_channels": 15, "audited_channels": 240}` |
| cozy_life:llm:2026-11-22T09:49:53Z:2 | refuted | Cozy life's channel-level baseline hit rate stays at or above 0.18 when the baseline is expanded beyond about 100 channels. A drop would mean the 24 replicable new channels are outliers. | `{"base_channel_hit_rate": 0.17857142857142858, "base_channels": 280}` |
| de_misc:entry | refuted | 新規チャンネル(開設365日以内)でも再現性ある成功が複数存在する | `{"replicable_new_channels": 1, "audited_channels": 16}` |
| drama_story:llm:2026-11-23T23:57:43Z:4 | refuted | Drama story's high hit rate is already attracting AI-assisted competitors. With 60 or more audited channels, at least 5 show AI signals, eroding the edge for a new AI channel. | `{"ai_signal_channels": 1, "audited_channels": 123}` |
| drama_story:llm:2026-11-25T18:50:32Z:3 | refuted | Drama story's hits are winner-take-most. With 100 or more hit channels sampled, the top-3 share rises to 0.55 or above, eroding the room for a new channel. | `{"top3_share": 0.3821534517069535, "channels_with_hits": 136}` |
| drama_story:llm:2026-11-25T21:45:41Z:3 | refuted | Drama story's 0.80 replicable rate is inflated by a small audit (61 channels). With 100 or more audited channels, the replicable rate falls to 0.65 or below, meaning many hit channels are one-off viral successes. | `{"replicable_rate": 0.8455284552845529, "audited_channels": 123}` |
| economics:base | refuted | 新着投稿の標本(生存者バイアス補正)でも、5万再生に届くチャンネルが10%以上ある | `{"base_channel_hit_rate": 0.05660377358490566, "base_channels": 53}` |
| economics:entry | refuted | 新規チャンネル(開設365日以内)でも再現性ある成功が複数存在する | `{"replicable_new_channels": 0, "audited_channels": 25}` |
| gaming_lore:llm:2026-11-24T19:33:10Z:4 | refuted | Gaming lore's replicable success belongs to incumbents. Even with 100 or more audited channels, replicable new channels stay at 10 or fewer. | `{"replicable_new_channels": 17, "audited_channels": 187}` |
| grooming_men:base | refuted | 新着投稿の標本(生存者バイアス補正)でも、5万再生に届くチャンネルが10%以上ある | `{"base_channel_hit_rate": 0.06493506493506493, "base_channels": 77}` |
| grooming_men:entry | refuted | 新規チャンネル(開設365日以内)でも再現性ある成功が複数存在する | `{"replicable_new_channels": 0, "audited_channels": 9}` |
| grooming_men:open | refuted | 上位3チャンネルがヒット再生の60%未満(寡占ではない) | `{"top3_share": 0.6419695792616421, "channels_with_hits": 9}` |
| history:llm:2026-11-24T22:30:39Z:1 | refuted | History's 56 replicable new channels hide weak typical economics. With 400 or more baseline videos, the baseline median stays at or below 600 views, so a typical new history upload does not monetise. | `{"base_median": 1154.0, "base_videos": 482}` |
| horror_mystery:base | refuted | 新着投稿の標本(生存者バイアス補正)でも、5万再生に届くチャンネルが10%以上ある | `{"base_channel_hit_rate": 0.0962962962962963, "base_channels": 135}` |
| horror_mystery:llm:2026-11-22T09:49:53Z:4 | refuted | Horror/mystery is a refuted niche for newcomers: even with a larger baseline, the hit rate stays at or below 6%, despite a 0.72 replicable rate among hit channels. | `{"base_hit_rate": 0.08666666666666667, "base_videos": 150}` |
| kids_edu:llm:2026-11-24T19:33:10Z:5 | refuted | Kids education's huge medians belong to incumbents. With 50 or more audited channels, replicable small channels stay at 2 or fewer, making it a closed market. | `{"replicable_small_channels": 8, "audited_channels": 59}` |
| korea_misc:open | refuted | 上位3チャンネルがヒット再生の60%未満(寡占ではない) | `{"top3_share": 0.6321043876147944, "channels_with_hits": 33}` |
| language_learning:base | refuted | 新着投稿の標本(生存者バイアス補正)でも、5万再生に届くチャンネルが10%以上ある | `{"base_channel_hit_rate": 0.06666666666666667, "base_channels": 45}` |
| language_learning:open | refuted | 上位3チャンネルがヒット再生の60%未満(寡占ではない) | `{"top3_share": 0.6080272501404139, "channels_with_hits": 108}` |
| maps_geo:llm:2026-11-22T16:20:55Z:5 | refuted | Maps/geo hits are concentrated among a few incumbents. With a broader hit-channel sample, the top-3 share rises to 0.55 or more. | `{"top3_share": 0.31949690775626977, "channels_with_hits": 173}` |
| math_logic:entry | refuted | 新規チャンネル(開設365日以内)でも再現性ある成功が複数存在する | `{"replicable_new_channels": 1, "audited_channels": 33}` |
| mens_sexual_health:base | refuted | 新着投稿の標本(生存者バイアス補正)でも、5万再生に届くチャンネルが10%以上ある | `{"base_channel_hit_rate": 0.039473684210526314, "base_channels": 228}` |
| midlife_men:base | refuted | 新着投稿の標本(生存者バイアス補正)でも、5万再生に届くチャンネルが10%以上ある | `{"base_channel_hit_rate": 0.08333333333333333, "base_channels": 60}` |
| midlife_men:entry | refuted | 新規チャンネル(開設365日以内)でも再現性ある成功が複数存在する | `{"replicable_new_channels": 0, "audited_channels": 10}` |
| midlife_men:open | refuted | 上位3チャンネルがヒット再生の60%未満(寡占ではない) | `{"top3_share": 0.8149067156802811, "channels_with_hits": 10}` |
| personal_finance:base | refuted | 新着投稿の標本(生存者バイアス補正)でも、5万再生に届くチャンネルが10%以上ある | `{"base_channel_hit_rate": 0.021739130434782608, "base_channels": 46}` |
| personal_finance:entry | refuted | 新規チャンネル(開設365日以内)でも再現性ある成功が複数存在する | `{"replicable_new_channels": 0, "audited_channels": 32}` |
| philosophy:entry | refuted | 新規チャンネル(開設365日以内)でも再現性ある成功が複数存在する | `{"replicable_new_channels": 0, "audited_channels": 10}` |
| philosophy:open | refuted | 上位3チャンネルがヒット再生の60%未満(寡占ではない) | `{"top3_share": 0.6993842603746625, "channels_with_hits": 12}` |
| philosophy:repl | refuted | 監査済みヒットチャンネルの25%以上が単発でなく再現性を持つ | `{"replicable_rate": 0.1, "audited_channels": 10}` |
| psychology:base | refuted | 新着投稿の標本(生存者バイアス補正)でも、5万再生に届くチャンネルが10%以上ある | `{"base_channel_hit_rate": 0.07096774193548387, "base_channels": 155}` |
| relaxing_visual:entry | refuted | 新規チャンネル(開設365日以内)でも再現性ある成功が複数存在する | `{"replicable_new_channels": 0, "audited_channels": 12}` |
| relaxing_visual:open | refuted | 上位3チャンネルがヒット再生の60%未満(寡占ではない) | `{"top3_share": 0.7875165391736448, "channels_with_hits": 12}` |
| scifi_story:base | refuted | 新着投稿の標本(生存者バイアス補正)でも、5万再生に届くチャンネルが10%以上ある | `{"base_channel_hit_rate": 0.09433962264150944, "base_channels": 106}` |
| sex_trivia_edu:base | refuted | 新着投稿の標本(生存者バイアス補正)でも、5万再生に届くチャンネルが10%以上ある | `{"base_channel_hit_rate": 0.03816793893129771, "base_channels": 131}` |
| sleep_health:base | refuted | 新着投稿の標本(生存者バイアス補正)でも、5万再生に届くチャンネルが10%以上ある | `{"base_channel_hit_rate": 0.015625, "base_channels": 64}` |
| sleep_health:open | refuted | 上位3チャンネルがヒット再生の60%未満(寡占ではない) | `{"top3_share": 0.6646682187426575, "channels_with_hits": 34}` |
| space:base | refuted | 新着投稿の標本(生存者バイアス補正)でも、5万再生に届くチャンネルが10%以上ある | `{"base_channel_hit_rate": 0.0670391061452514, "base_channels": 179}` |
| tech_explain:base | refuted | 新着投稿の標本(生存者バイアス補正)でも、5万再生に届くチャンネルが10%以上ある | `{"base_channel_hit_rate": 0.07317073170731707, "base_channels": 41}` |
| travel_culture:llm:2026-11-23T23:57:43Z:2 | refuted | Travel/culture looks open (23 replicable small channels), but demand is actually concentrated. With 70 or more hit channels sampled, the top-3 share stays at 0.50 or above. | `{"top3_share": 0.45051230114206897, "channels_with_hits": 96}` |
| trivia:llm:2026-11-22T16:20:55Z:2 | refuted | Japanese trivia's 17 replicable small channels do not generalize. The channel-level baseline hit rate is 10% or less when sampled broadly. | `{"base_channel_hit_rate": 0.2956989247311828, "base_channels": 186}` |
| true_crime:llm:2026-11-22T19:44:52Z:1 | refuted | True crime's 0.94 replicable rate belongs to incumbents. Even with a larger audit, 3 or fewer replicable channels are new, so a new AI-assisted channel faces a closed market. | `{"replicable_new_channels": 8, "audited_channels": 97}` |
| ai_film:base | supported | 新着投稿の標本(生存者バイアス補正)でも、5万再生に届くチャンネルが10%以上ある | `{"base_channel_hit_rate": 0.2073170731707317, "base_channels": 82}` |
| ai_film:entry | supported | 新規チャンネル(開設365日以内)でも再現性ある成功が複数存在する | `{"replicable_new_channels": 43, "audited_channels": 199}` |
| ai_film:open | supported | 上位3チャンネルがヒット再生の60%未満(寡占ではない) | `{"top3_share": 0.19058412458658164, "channels_with_hits": 205}` |
| ai_film:repl | supported | 監査済みヒットチャンネルの25%以上が単発でなく再現性を持つ | `{"replicable_rate": 0.5175879396984925, "audited_channels": 199}` |
| ai_news_tools:base | supported | 新着投稿の標本(生存者バイアス補正)でも、5万再生に届くチャンネルが10%以上ある | `{"base_channel_hit_rate": 0.19148936170212766, "base_channels": 47}` |
| ai_news_tools:repl | supported | 監査済みヒットチャンネルの25%以上が単発でなく再現性を持つ | `{"replicable_rate": 0.5714285714285714, "audited_channels": 70}` |
| asmr_process:repl | supported | 監査済みヒットチャンネルの25%以上が単発でなく再現性を持つ | `{"replicable_rate": 0.3125, "audited_channels": 16}` |
| asset_building:base | supported | 新着投稿の標本(生存者バイアス補正)でも、5万再生に届くチャンネルが10%以上ある | `{"base_channel_hit_rate": 0.22709163346613545, "base_channels": 251}` |
| asset_building:entry | supported | 新規チャンネル(開設365日以内)でも再現性ある成功が複数存在する | `{"replicable_new_channels": 22, "audited_channels": 148}` |
| asset_building:open | supported | 上位3チャンネルがヒット再生の60%未満(寡占ではない) | `{"top3_share": 0.26843369854721194, "channels_with_hits": 163}` |
| asset_building:repl | supported | 監査済みヒットチャンネルの25%以上が単発でなく再現性を持つ | `{"replicable_rate": 0.6891891891891891, "audited_channels": 148}` |
| aviation_military:entry | supported | 新規チャンネル(開設365日以内)でも再現性ある成功が複数存在する | `{"replicable_new_channels": 17, "audited_channels": 173}` |
| aviation_military:open | supported | 上位3チャンネルがヒット再生の60%未満(寡占ではない) | `{"top3_share": 0.1577385847678977, "channels_with_hits": 204}` |
| aviation_military:repl | supported | 監査済みヒットチャンネルの25%以上が単発でなく再現性を持つ | `{"replicable_rate": 0.5086705202312138, "audited_channels": 173}` |
| biology_nature:base | supported | 新着投稿の標本(生存者バイアス補正)でも、5万再生に届くチャンネルが10%以上ある | `{"base_channel_hit_rate": 0.15178571428571427, "base_channels": 224}` |
| biology_nature:entry | supported | 新規チャンネル(開設365日以内)でも再現性ある成功が複数存在する | `{"replicable_new_channels": 21, "audited_channels": 96}` |
| biology_nature:open | supported | 上位3チャンネルがヒット再生の60%未満(寡占ではない) | `{"top3_share": 0.2712480273762885, "channels_with_hits": 105}` |
| biology_nature:repl | supported | 監査済みヒットチャンネルの25%以上が単発でなく再現性を持つ | `{"replicable_rate": 0.46875, "audited_channels": 96}` |
| cars_machines:entry | supported | 新規チャンネル(開設365日以内)でも再現性ある成功が複数存在する | `{"replicable_new_channels": 6, "audited_channels": 22}` |
| cars_machines:open | supported | 上位3チャンネルがヒット再生の60%未満(寡占ではない) | `{"top3_share": 0.5822465148239135, "channels_with_hits": 24}` |
| cars_machines:repl | supported | 監査済みヒットチャンネルの25%以上が単発でなく再現性を持つ | `{"replicable_rate": 0.5454545454545454, "audited_channels": 22}` |
| comparison_data:entry | supported | 新規チャンネル(開設365日以内)でも再現性ある成功が複数存在する | `{"replicable_new_channels": 10, "audited_channels": 62}` |
| comparison_data:llm:2026-11-22T19:44:52Z:3 | supported | Comparison/data videos are winner-take-most. With 60 or more hit channels sampled, the top-3 share stays at 0.70 or above, despite 16 replicable small channels. | `{"top3_share": 0.7622549241006398, "channels_with_hits": 66}` |
| comparison_data:repl | supported | 監査済みヒットチャンネルの25%以上が単発でなく再現性を持つ | `{"replicable_rate": 0.5483870967741935, "audited_channels": 62}` |
| cooking:base | supported | 新着投稿の標本(生存者バイアス補正)でも、5万再生に届くチャンネルが10%以上ある | `{"base_channel_hit_rate": 0.3958333333333333, "base_channels": 48}` |
| cooking:entry | supported | 新規チャンネル(開設365日以内)でも再現性ある成功が複数存在する | `{"replicable_new_channels": 15, "audited_channels": 240}` |
| cooking:open | supported | 上位3チャンネルがヒット再生の60%未満(寡占ではない) | `{"top3_share": 0.19036861762014398, "channels_with_hits": 249}` |
| cooking:repl | supported | 監査済みヒットチャンネルの25%以上が単発でなく再現性を持つ | `{"replicable_rate": 0.7583333333333333, "audited_channels": 240}` |
| cozy_life:base | supported | 新着投稿の標本(生存者バイアス補正)でも、5万再生に届くチャンネルが10%以上ある | `{"base_channel_hit_rate": 0.17857142857142858, "base_channels": 280}` |
| cozy_life:entry | supported | 新規チャンネル(開設365日以内)でも再現性ある成功が複数存在する | `{"replicable_new_channels": 42, "audited_channels": 172}` |
| cozy_life:llm:2026-11-22T16:20:55Z:4 | supported | Cozy life's typical views are too low to monetize. The baseline median stays at or below 5,000 views once the sample is expanded. | `{"base_median": 1467.0, "base_videos": 332}` |
| cozy_life:llm:2026-11-23T08:34:44Z:2 | supported | Cozy life hits are frequent but small. With 250 or more baseline videos, the median view count stays at or below 2,000, too low to monetise an AI-assisted channel. | `{"base_median": 1467.0, "base_videos": 332}` |
| cozy_life:open | supported | 上位3チャンネルがヒット再生の60%未満(寡占ではない) | `{"top3_share": 0.18464118095381307, "channels_with_hits": 192}` |
| cozy_life:repl | supported | 監査済みヒットチャンネルの25%以上が単発でなく再現性を持つ | `{"replicable_rate": 0.6627906976744186, "audited_channels": 172}` |
| de_misc:open | supported | 上位3チャンネルがヒット再生の60%未満(寡占ではない) | `{"top3_share": 0.521275339455707, "channels_with_hits": 19}` |
| de_misc:repl | supported | 監査済みヒットチャンネルの25%以上が単発でなく再現性を持つ | `{"replicable_rate": 0.5625, "audited_channels": 16}` |
| diy_craft:base | supported | 新着投稿の標本(生存者バイアス補正)でも、5万再生に届くチャンネルが10%以上ある | `{"base_channel_hit_rate": 0.20481927710843373, "base_channels": 83}` |
| diy_craft:entry | supported | 新規チャンネル(開設365日以内)でも再現性ある成功が複数存在する | `{"replicable_new_channels": 17, "audited_channels": 113}` |
| diy_craft:open | supported | 上位3チャンネルがヒット再生の60%未満(寡占ではない) | `{"top3_share": 0.23516322678737053, "channels_with_hits": 116}` |
| diy_craft:repl | supported | 監査済みヒットチャンネルの25%以上が単発でなく再現性を持つ | `{"replicable_rate": 0.5663716814159292, "audited_channels": 113}` |
| drama_story:base | supported | 新着投稿の標本(生存者バイアス補正)でも、5万再生に届くチャンネルが10%以上ある | `{"base_channel_hit_rate": 0.3942307692307692, "base_channels": 104}` |
| drama_story:entry | supported | 新規チャンネル(開設365日以内)でも再現性ある成功が複数存在する | `{"replicable_new_channels": 35, "audited_channels": 123}` |
| drama_story:llm:2026-11-22T09:49:53Z:1 | supported | Drama story's high baseline hit rate (0.46) is not driven by a few incumbents: with a larger audit, at least 10 replicable channels are new channels. | `{"replicable_new_channels": 35, "audited_channels": 123}` |
| drama_story:open | supported | 上位3チャンネルがヒット再生の60%未満(寡占ではない) | `{"top3_share": 0.3821534517069535, "channels_with_hits": 136}` |
| drama_story:repl | supported | 監査済みヒットチャンネルの25%以上が単発でなく再現性を持つ | `{"replicable_rate": 0.8455284552845529, "audited_channels": 123}` |
| economics:open | supported | 上位3チャンネルがヒット再生の60%未満(寡占ではない) | `{"top3_share": 0.3839756962858737, "channels_with_hits": 31}` |
| economics:repl | supported | 監査済みヒットチャンネルの25%以上が単発でなく再現性を持つ | `{"replicable_rate": 0.52, "audited_channels": 25}` |
| fr_misc:entry | supported | 新規チャンネル(開設365日以内)でも再現性ある成功が複数存在する | `{"replicable_new_channels": 6, "audited_channels": 45}` |
| fr_misc:open | supported | 上位3チャンネルがヒット再生の60%未満(寡占ではない) | `{"top3_share": 0.3335639768162933, "channels_with_hits": 50}` |
| fr_misc:repl | supported | 監査済みヒットチャンネルの25%以上が単発でなく再現性を持つ | `{"replicable_rate": 0.7333333333333333, "audited_channels": 45}` |
| gaming_lore:entry | supported | 新規チャンネル(開設365日以内)でも再現性ある成功が複数存在する | `{"replicable_new_channels": 17, "audited_channels": 187}` |
| gaming_lore:open | supported | 上位3チャンネルがヒット再生の60%未満(寡占ではない) | `{"top3_share": 0.22347793044315217, "channels_with_hits": 202}` |
| gaming_lore:repl | supported | 監査済みヒットチャンネルの25%以上が単発でなく再現性を持つ | `{"replicable_rate": 0.7272727272727273, "audited_channels": 187}` |
| grooming_men:repl | supported | 監査済みヒットチャンネルの25%以上が単発でなく再現性を持つ | `{"replicable_rate": 0.4444444444444444, "audited_channels": 9}` |
| health_body:entry | supported | 新規チャンネル(開設365日以内)でも再現性ある成功が複数存在する | `{"replicable_new_channels": 6, "audited_channels": 38}` |
| health_body:open | supported | 上位3チャンネルがヒット再生の60%未満(寡占ではない) | `{"top3_share": 0.43214556566242285, "channels_with_hits": 42}` |
| health_body:repl | supported | 監査済みヒットチャンネルの25%以上が単発でなく再現性を持つ | `{"replicable_rate": 0.42105263157894735, "audited_channels": 38}` |
| history:base | supported | 新着投稿の標本(生存者バイアス補正)でも、5万再生に届くチャンネルが10%以上ある | `{"base_channel_hit_rate": 0.2219730941704036, "base_channels": 446}` |
| history:entry | supported | 新規チャンネル(開設365日以内)でも再現性ある成功が複数存在する | `{"replicable_new_channels": 63, "audited_channels": 446}` |
| history:open | supported | 上位3チャンネルがヒット再生の60%未満(寡占ではない) | `{"top3_share": 0.28598598932896335, "channels_with_hits": 483}` |
| history:repl | supported | 監査済みヒットチャンネルの25%以上が単発でなく再現性を持つ | `{"replicable_rate": 0.5807174887892377, "audited_channels": 446}` |
| horror_mystery:entry | supported | 新規チャンネル(開設365日以内)でも再現性ある成功が複数存在する | `{"replicable_new_channels": 23, "audited_channels": 145}` |
| horror_mystery:open | supported | 上位3チャンネルがヒット再生の60%未満(寡占ではない) | `{"top3_share": 0.510869493824106, "channels_with_hits": 157}` |
| horror_mystery:repl | supported | 監査済みヒットチャンネルの25%以上が単発でなく再現性を持つ | `{"replicable_rate": 0.6137931034482759, "audited_channels": 145}` |
| indonesia_misc:entry | supported | 新規チャンネル(開設365日以内)でも再現性ある成功が複数存在する | `{"replicable_new_channels": 34, "audited_channels": 191}` |
| indonesia_misc:open | supported | 上位3チャンネルがヒット再生の60%未満(寡占ではない) | `{"top3_share": 0.14669204603090713, "channels_with_hits": 206}` |
| indonesia_misc:repl | supported | 監査済みヒットチャンネルの25%以上が単発でなく再現性を持つ | `{"replicable_rate": 0.7696335078534031, "audited_channels": 191}` |
| infrastructure:base | supported | 新着投稿の標本(生存者バイアス補正)でも、5万再生に届くチャンネルが10%以上ある | `{"base_channel_hit_rate": 0.12307692307692308, "base_channels": 65}` |
| infrastructure:entry | supported | 新規チャンネル(開設365日以内)でも再現性ある成功が複数存在する | `{"replicable_new_channels": 8, "audited_channels": 47}` |
| infrastructure:open | supported | 上位3チャンネルがヒット再生の60%未満(寡占ではない) | `{"top3_share": 0.35073865983793195, "channels_with_hits": 52}` |
| infrastructure:repl | supported | 監査済みヒットチャンネルの25%以上が単発でなく再現性を持つ | `{"replicable_rate": 0.48936170212765956, "audited_channels": 47}` |
| kids_edu:entry | supported | 新規チャンネル(開設365日以内)でも再現性ある成功が複数存在する | `{"replicable_new_channels": 8, "audited_channels": 59}` |
| kids_edu:open | supported | 上位3チャンネルがヒット再生の60%未満(寡占ではない) | `{"top3_share": 0.45275070300091497, "channels_with_hits": 63}` |
| kids_edu:repl | supported | 監査済みヒットチャンネルの25%以上が単発でなく再現性を持つ | `{"replicable_rate": 0.7457627118644068, "audited_channels": 59}` |
| korea_misc:entry | supported | 新規チャンネル(開設365日以内)でも再現性ある成功が複数存在する | `{"replicable_new_channels": 7, "audited_channels": 31}` |
| korea_misc:repl | supported | 監査済みヒットチャンネルの25%以上が単発でなく再現性を持つ | `{"replicable_rate": 0.41935483870967744, "audited_channels": 31}` |
| language_learning:entry | supported | 新規チャンネル(開設365日以内)でも再現性ある成功が複数存在する | `{"replicable_new_channels": 18, "audited_channels": 101}` |
| language_learning:repl | supported | 監査済みヒットチャンネルの25%以上が単発でなく再現性を持つ | `{"replicable_rate": 0.45544554455445546, "audited_channels": 101}` |
| maps_geo:base | supported | 新着投稿の標本(生存者バイアス補正)でも、5万再生に届くチャンネルが10%以上ある | `{"base_channel_hit_rate": 0.11764705882352941, "base_channels": 68}` |
| maps_geo:entry | supported | 新規チャンネル(開設365日以内)でも再現性ある成功が複数存在する | `{"replicable_new_channels": 28, "audited_channels": 144}` |
| maps_geo:llm:2026-11-22T09:49:53Z:5 | supported | Maps/geo demand is not concentrated: with more hit channels sampled, the top-3 share stays at or below 0.45. | `{"top3_share": 0.31949690775626977, "channels_with_hits": 173}` |
| maps_geo:open | supported | 上位3チャンネルがヒット再生の60%未満(寡占ではない) | `{"top3_share": 0.31949690775626977, "channels_with_hits": 173}` |
| maps_geo:repl | supported | 監査済みヒットチャンネルの25%以上が単発でなく再現性を持つ | `{"replicable_rate": 0.7222222222222222, "audited_channels": 144}` |
| math_logic:base | supported | 新着投稿の標本(生存者バイアス補正)でも、5万再生に届くチャンネルが10%以上ある | `{"base_channel_hit_rate": 0.225, "base_channels": 40}` |
| math_logic:open | supported | 上位3チャンネルがヒット再生の60%未満(寡占ではない) | `{"top3_share": 0.49948458325916234, "channels_with_hits": 49}` |
| math_logic:repl | supported | 監査済みヒットチャンネルの25%以上が単発でなく再現性を持つ | `{"replicable_rate": 0.48484848484848486, "audited_channels": 33}` |
| mens_sexual_health:entry | supported | 新規チャンネル(開設365日以内)でも再現性ある成功が複数存在する | `{"replicable_new_channels": 3, "audited_channels": 81}` |
| mens_sexual_health:open | supported | 上位3チャンネルがヒット再生の60%未満(寡占ではない) | `{"top3_share": 0.31405981716091885, "channels_with_hits": 96}` |
| mens_sexual_health:repl | supported | 監査済みヒットチャンネルの25%以上が単発でなく再現性を持つ | `{"replicable_rate": 0.4444444444444444, "audited_channels": 81}` |
| midlife_men:repl | supported | 監査済みヒットチャンネルの25%以上が単発でなく再現性を持つ | `{"replicable_rate": 0.6, "audited_channels": 10}` |
| personal_finance:open | supported | 上位3チャンネルがヒット再生の60%未満(寡占ではない) | `{"top3_share": 0.3999880988518758, "channels_with_hits": 36}` |
| personal_finance:repl | supported | 監査済みヒットチャンネルの25%以上が単発でなく再現性を持つ | `{"replicable_rate": 0.46875, "audited_channels": 32}` |
| psychology:entry | supported | 新規チャンネル(開設365日以内)でも再現性ある成功が複数存在する | `{"replicable_new_channels": 6, "audited_channels": 44}` |
| psychology:open | supported | 上位3チャンネルがヒット再生の60%未満(寡占ではない) | `{"top3_share": 0.5880282595588178, "channels_with_hits": 47}` |
| psychology:repl | supported | 監査済みヒットチャンネルの25%以上が単発でなく再現性を持つ | `{"replicable_rate": 0.4318181818181818, "audited_channels": 44}` |
| relationships_dating:base | supported | 新着投稿の標本(生存者バイアス補正)でも、5万再生に届くチャンネルが10%以上ある | `{"base_channel_hit_rate": 0.12087912087912088, "base_channels": 182}` |
| relationships_dating:entry | supported | 新規チャンネル(開設365日以内)でも再現性ある成功が複数存在する | `{"replicable_new_channels": 9, "audited_channels": 45}` |
| relationships_dating:llm:2026-11-24T08:17:19Z:4 | supported | Relationships/dating's 0.30 channel-level hit rate, measured on 60 channels, is inflated. With 100 or more baseline channels, it falls to 0.15 or below. | `{"base_channel_hit_rate": 0.12087912087912088, "base_channels": 182}` |
| relationships_dating:open | supported | 上位3チャンネルがヒット再生の60%未満(寡占ではない) | `{"top3_share": 0.34568000537618543, "channels_with_hits": 52}` |
| relationships_dating:repl | supported | 監査済みヒットチャンネルの25%以上が単発でなく再現性を持つ | `{"replicable_rate": 0.3333333333333333, "audited_channels": 45}` |
| relaxing_visual:repl | supported | 監査済みヒットチャンネルの25%以上が単発でなく再現性を持つ | `{"replicable_rate": 0.3333333333333333, "audited_channels": 12}` |
| religion_myth:entry | supported | 新規チャンネル(開設365日以内)でも再現性ある成功が複数存在する | `{"replicable_new_channels": 14, "audited_channels": 106}` |
| religion_myth:open | supported | 上位3チャンネルがヒット再生の60%未満(寡占ではない) | `{"top3_share": 0.5200822294320167, "channels_with_hits": 109}` |
| religion_myth:repl | supported | 監査済みヒットチャンネルの25%以上が単発でなく再現性を持つ | `{"replicable_rate": 0.5377358490566038, "audited_channels": 106}` |
| science:base | supported | 新着投稿の標本(生存者バイアス補正)でも、5万再生に届くチャンネルが10%以上ある | `{"base_channel_hit_rate": 0.13240418118466898, "base_channels": 287}` |
| science:entry | supported | 新規チャンネル(開設365日以内)でも再現性ある成功が複数存在する | `{"replicable_new_channels": 15, "audited_channels": 103}` |
| science:open | supported | 上位3チャンネルがヒット再生の60%未満(寡占ではない) | `{"top3_share": 0.40262998166183206, "channels_with_hits": 107}` |
| science:repl | supported | 監査済みヒットチャンネルの25%以上が単発でなく再現性を持つ | `{"replicable_rate": 0.5339805825242718, "audited_channels": 103}` |
| scifi_story:entry | supported | 新規チャンネル(開設365日以内)でも再現性ある成功が複数存在する | `{"replicable_new_channels": 22, "audited_channels": 120}` |
| scifi_story:open | supported | 上位3チャンネルがヒット再生の60%未満(寡占ではない) | `{"top3_share": 0.43208294384338386, "channels_with_hits": 122}` |
| scifi_story:repl | supported | 監査済みヒットチャンネルの25%以上が単発でなく再現性を持つ | `{"replicable_rate": 0.39166666666666666, "audited_channels": 120}` |
| sex_trivia_edu:entry | supported | 新規チャンネル(開設365日以内)でも再現性ある成功が複数存在する | `{"replicable_new_channels": 4, "audited_channels": 55}` |
| sex_trivia_edu:open | supported | 上位3チャンネルがヒット再生の60%未満(寡占ではない) | `{"top3_share": 0.3734401169038536, "channels_with_hits": 67}` |
| sex_trivia_edu:repl | supported | 監査済みヒットチャンネルの25%以上が単発でなく再現性を持つ | `{"replicable_rate": 0.41818181818181815, "audited_channels": 55}` |
| sleep_health:entry | supported | 新規チャンネル(開設365日以内)でも再現性ある成功が複数存在する | `{"replicable_new_channels": 2, "audited_channels": 26}` |
| sleep_health:repl | supported | 監査済みヒットチャンネルの25%以上が単発でなく再現性を持つ | `{"replicable_rate": 0.6153846153846154, "audited_channels": 26}` |
| space:entry | supported | 新規チャンネル(開設365日以内)でも再現性ある成功が複数存在する | `{"replicable_new_channels": 5, "audited_channels": 59}` |
| space:open | supported | 上位3チャンネルがヒット再生の60%未満(寡占ではない) | `{"top3_share": 0.3904014840849712, "channels_with_hits": 60}` |
| space:repl | supported | 監査済みヒットチャンネルの25%以上が単発でなく再現性を持つ | `{"replicable_rate": 0.5932203389830508, "audited_channels": 59}` |
| sports_story:entry | supported | 新規チャンネル(開設365日以内)でも再現性ある成功が複数存在する | `{"replicable_new_channels": 2, "audited_channels": 15}` |
| sports_story:open | supported | 上位3チャンネルがヒット再生の60%未満(寡占ではない) | `{"top3_share": 0.5403784201117594, "channels_with_hits": 17}` |
| sports_story:repl | supported | 監査済みヒットチャンネルの25%以上が単発でなく再現性を持つ | `{"replicable_rate": 0.7333333333333333, "audited_channels": 15}` |
| tech_explain:entry | supported | 新規チャンネル(開設365日以内)でも再現性ある成功が複数存在する | `{"replicable_new_channels": 7, "audited_channels": 51}` |
| tech_explain:open | supported | 上位3チャンネルがヒット再生の60%未満(寡占ではない) | `{"top3_share": 0.45232440590912065, "channels_with_hits": 56}` |
| tech_explain:repl | supported | 監査済みヒットチャンネルの25%以上が単発でなく再現性を持つ | `{"replicable_rate": 0.47058823529411764, "audited_channels": 51}` |
| travel_culture:entry | supported | 新規チャンネル(開設365日以内)でも再現性ある成功が複数存在する | `{"replicable_new_channels": 20, "audited_channels": 86}` |
| travel_culture:open | supported | 上位3チャンネルがヒット再生の60%未満(寡占ではない) | `{"top3_share": 0.45051230114206897, "channels_with_hits": 96}` |
| travel_culture:repl | supported | 監査済みヒットチャンネルの25%以上が単発でなく再現性を持つ | `{"replicable_rate": 0.6046511627906976, "audited_channels": 86}` |
| trivia:base | supported | 新着投稿の標本(生存者バイアス補正)でも、5万再生に届くチャンネルが10%以上ある | `{"base_channel_hit_rate": 0.2956989247311828, "base_channels": 186}` |
| trivia:entry | supported | 新規チャンネル(開設365日以内)でも再現性ある成功が複数存在する | `{"replicable_new_channels": 16, "audited_channels": 171}` |
| trivia:llm:2026-11-22T09:49:53Z:3 | supported | Japanese trivia's low concentration and 17 replicable small channels translate into a baseline hit rate of at least 10%. Otherwise, hits are rare among typical uploaders. | `{"base_hit_rate": 0.25806451612903225, "base_videos": 248}` |
| trivia:open | supported | 上位3チャンネルがヒット再生の60%未満(寡占ではない) | `{"top3_share": 0.17198150414195043, "channels_with_hits": 188}` |
| trivia:repl | supported | 監査済みヒットチャンネルの25%以上が単発でなく再現性を持つ | `{"replicable_rate": 0.7543859649122807, "audited_channels": 171}` |
| true_crime:entry | supported | 新規チャンネル(開設365日以内)でも再現性ある成功が複数存在する | `{"replicable_new_channels": 8, "audited_channels": 97}` |
| true_crime:open | supported | 上位3チャンネルがヒット再生の60%未満(寡占ではない) | `{"top3_share": 0.21905159492591708, "channels_with_hits": 135}` |
| true_crime:repl | supported | 監査済みヒットチャンネルの25%以上が単発でなく再現性を持つ | `{"replicable_rate": 0.7319587628865979, "audited_channels": 97}` |

## 過去事例の公式API再検証

| 動画ID | 事例 | 過去報告値 | API確認結果 |
|---|---|---|---|
| [kiqiQzn12rc](https://www.youtube.com/watch?v=kiqiQzn12rc) | The Curious Stick: Roman army camp | 4.16M-4.30M | views=4,396,188 published=2026-10-10 age_days=41 channel='The Curious Stick' subs_now=12300 |
| [fRQL6LEjwFg](https://www.youtube.com/watch?v=fRQL6LEjwFg) | GoDocs: Saudi Arabia water | 6.77M | views=7,724,212 published=2026-10-11 age_days=41 channel='GoDocs' subs_now=76200 |
| [q2E23sEfMIo](https://www.youtube.com/watch?v=q2E23sEfMIo) | Paper Borders: Roman Empire | 318K | views=348,815 published=2026-10-04 age_days=48 channel='Paper Borders' subs_now=447 |
| [8l-dxq3zwhs](https://www.youtube.com/watch?v=8l-dxq3zwhs) | SimplyTold: why humans wear clothes | 324K | views=325,052 published=2026-10-14 age_days=38 channel='SimplyTold' subs_now=945 |
| [BZkPquCm6v8](https://www.youtube.com/watch?v=BZkPquCm6v8) | Causality: world after WW3 | 4.586M | views=8,897,218 published=2026-11-11 age_days=10 channel='Causality' subs_now=84700 |
| [c2n4WUniQfE](https://www.youtube.com/watch?v=c2n4WUniQfE) | Phantom Expedition: crow language | 739K | views=849,765 published=2026-11-09 age_days=11 channel='Phantom Expedition' subs_now=44300 |
| [BQ6SjJ_VzoQ](https://www.youtube.com/watch?v=BQ6SjJ_VzoQ) | Vicky Qubes: bride cooking | 1.006M | views=2,088,955 published=2026-11-14 age_days=7 channel='Vicky Qubes' subs_now=93500 |
| [95EGhuiNAIk](https://www.youtube.com/watch?v=95EGhuiNAIk) | Cozy Village Tales: small rural house | 170.47M | views=174,794,260 published=2026-09-09 age_days=73 channel='Cozy Village Tales' subs_now=369000 |
| [qT4MQLhUt2k](https://www.youtube.com/watch?v=qT4MQLhUt2k) | Colin@NYC: helping AI short | 2.68M | views=3,048,425 published=2026-11-06 age_days=15 channel='Colin@NYC' subs_now=16800 |
| [TlrjGqHhplc](https://www.youtube.com/watch?v=TlrjGqHhplc) | Lumz Cinema: protecting alien child | 14.1M | views=14,977,144 published=2026-10-02 age_days=49 channel='Lumz Cinema' subs_now=102000 |

## Claude API 仮説生成

`{"hypotheses": 6, "topics": 4, "usage": {"in": 22609, "out": 2884}}`

## 直近エラー

- 2026-11-22T09:34:58Z `llm` AuthenticationError("Error code: 401 - {'type': 'error', 'error': {'type': 'authentication_error', 'message': 'invalid x-api-key'}, 'request_id': 'req_011ChHjnkKk4yMdn2cVTnYUE'}")
