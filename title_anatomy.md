# タイトル解剖(何の話題が、どんなタイトルで伸びたか)

生成: 2026-11-22T14:57:44Z / モデル: `claude-haiku-5-5`

- 分類 360 本 / APIコール 15 / 分類失敗 0 / 拒否 0 / 上限超過で未処理 0
- トークン 入力 29,729 / 出力 64,827 / 実測コスト $0.0354

## 注意事項(必ずお読みください)

- 相関であって因果ではありません。タイトルの型や話題が再生数を生んだとは言えません。
- 生存者バイアス: ヒット群は再生数で選んでおり、同じ型で伸びなかった動画は見えていません。
- 視聴維持率などの視聴者行動データはありません。クリックされても最後まで見られたかは不明です。
- サンプルが小さい(各群数十本)ため、差は偶然の可能性があります。
- 見ているのはタイトル・長さ・チャンネル指標のみで、動画の中身やサムネイルは見ていません。
- 分類は小型モデルによる自動判定で、人手での検証はしていません。誤分類を含みます。
- 模倣はしない: 他者のタイトルをコピーせず、あくまで参考傾向として使ってください。

## ジャンル: history

ヒット群 n=60(選定 60) / ベースライン群 n=60(選定 60)
比較の対象(ベースライン): 新着順の標本(date_samples)

#### フック型 (`hook_type`)

| 値 | ヒット n | ヒット割合 | ベース n | ベース割合 | リフト |
|---|---|---|---|---|---|
| mystery_reveal | 22 | 37% | 9 | 15% | 2.44 |
| question | 17 | 28% | 19 | 32% | 0.89 |
| other | 12 | 20% | 24 | 40% | 0.50 |
| definition_explainer | 2 | 3% | 5 | 8% | 0.40 |
| comparison | 2 | 3% | 0 | 0% | - |
| how_to | 0 | 0% | 1 | 2% | - |
| news_timely | 1 | 2% | 0 | 0% | - |
| numbered_list | 2 | 3% | 1 | 2% | - |
| personal_story | 2 | 3% | 1 | 2% | - |

#### 感情 (`emotion`)

| 値 | ヒット n | ヒット割合 | ベース n | ベース割合 | リフト |
|---|---|---|---|---|---|
| awe | 9 | 15% | 5 | 8% | 1.80 |
| curiosity | 49 | 82% | 46 | 77% | 1.07 |
| none | 0 | 0% | 4 | 7% | 0.00 |
| anger | 0 | 0% | 1 | 2% | - |
| comfort | 1 | 2% | 2 | 3% | - |
| fear | 1 | 2% | 2 | 3% | - |

#### 具体性 (`specificity`)

| 値 | ヒット n | ヒット割合 | ベース n | ベース割合 | リフト |
|---|---|---|---|---|---|
| low | 14 | 23% | 5 | 8% | 2.80 |
| high | 19 | 32% | 22 | 37% | 0.86 |
| medium | 27 | 45% | 33 | 55% | 0.82 |

#### 時事性 (`time_sensitivity`)

| 値 | ヒット n | ヒット割合 | ベース n | ベース割合 | リフト |
|---|---|---|---|---|---|
| evergreen | 58 | 97% | 59 | 98% | 0.98 |
| timely | 2 | 3% | 1 | 2% | - |

#### 釣り度 (`clickbait_level`)

| 値 | ヒット n | ヒット割合 | ベース n | ベース割合 | リフト |
|---|---|---|---|---|---|
| medium | 29 | 48% | 30 | 50% | 0.97 |
| low | 23 | 38% | 28 | 47% | 0.82 |
| high | 8 | 13% | 2 | 3% | - |

#### 実在の人物の物語 (`real_person_story`)

| 値 | ヒット n | ヒット割合 | ベース n | ベース割合 | リフト |
|---|---|---|---|---|---|
| false | 57 | 95% | 54 | 90% | 1.06 |
| true | 3 | 5% | 6 | 10% | 0.50 |

#### 数字を含む (`has_digit`)

| 値 | ヒット n | ヒット割合 | ベース n | ベース割合 | リフト |
|---|---|---|---|---|---|
| false | 46 | 77% | 44 | 73% | 1.05 |
| true | 14 | 23% | 16 | 27% | 0.88 |

#### 括弧【】「」を含む (`has_bracket`)

| 値 | ヒット n | ヒット割合 | ベース n | ベース割合 | リフト |
|---|---|---|---|---|---|
| false | 60 | 100% | 45 | 75% | 1.33 |
| true | 0 | 0% | 15 | 25% | 0.00 |

### 数値の事実(ヒット vs ベースライン)

| 指標 | ヒット | ベース |
|---|---|---|
| 長尺の長さ中央値(分) | 42.7 | 39.7 |
| タイトル文字数の中央値 | 60 | 56 |
| 数字を含むタイトルの割合 | 23% | 27% |
| 括弧【】「」を含む割合 | 0% | 25% |
| 再生数/日の中央値 | 22,999 | 70 |
| チャンネル登録者数の中央値 | 116,500 | 106,000 |
| 1年未満のチャンネルの割合 | 30% | 20% |
| 90日あたり投稿数の中央値 | 50.0 | 9.0 |

### 話題クラスタ(ヒット 3 本以上)

**ヒット本数の多い順**

| クラスタ | ヒット本数 | 再生数中央値 | 例1 | 例2 |
|---|---|---|---|---|
| medieval life | 4 | 726,084 | The medieval period did not look like this! It was full of colour! | How Did Humans Survive −40° Nights Inside a Massive Medieval Castle? |
| ancient human technology | 3 | 9,328,082 | How Did Ancient Humans Make the First Sharp Stone Tools? 😱 / #shorts | How Did Ancient Humans Make the First Clay Pots? 😱 /#shorts |
| egyptian archaeology documentaries | 3 | 3,250,133 | Investigating the Hidden Chamber (Full Episode) / Kingdom of the Mummies / National Geographic | Cleopatra's Final Secret (Full Episode) / Documentary Special / National Geographic |
| human evolution | 3 | 1,388,575 | This Fossil Is Forcing A Rewrite Of Human History | How Did Early Humans Make Their FIRST Pots? 🏺 / Human Evolution #shorts |
| ancient aliens | 3 | 933,620 | The Next Stage of Human Evolution / Ancient Aliens / Marathon | Ancient Tech That's OUT OF THIS WORLD / Ancient Aliens |
| medieval daily life | 3 | 601,247 | What Was Life Like In Medieval London? | Inside 3 Medieval Houses: How Different Was Daily Life? |

**ヒット群の再生数中央値の高い順**

| クラスタ | ヒット本数 | 再生数中央値 | 例1 | 例2 |
|---|---|---|---|---|
| ancient human technology | 3 | 9,328,082 | How Did Ancient Humans Make the First Sharp Stone Tools? 😱 / #shorts | How Did Ancient Humans Make the First Clay Pots? 😱 /#shorts |
| egyptian archaeology documentaries | 3 | 3,250,133 | Investigating the Hidden Chamber (Full Episode) / Kingdom of the Mummies / National Geographic | Cleopatra's Final Secret (Full Episode) / Documentary Special / National Geographic |
| human evolution | 3 | 1,388,575 | This Fossil Is Forcing A Rewrite Of Human History | How Did Early Humans Make Their FIRST Pots? 🏺 / Human Evolution #shorts |
| ancient aliens | 3 | 933,620 | The Next Stage of Human Evolution / Ancient Aliens / Marathon | Ancient Tech That's OUT OF THIS WORLD / Ancient Aliens |
| medieval life | 4 | 726,084 | The medieval period did not look like this! It was full of colour! | How Did Humans Survive −40° Nights Inside a Massive Medieval Castle? |
| medieval daily life | 3 | 601,247 | What Was Life Like In Medieval London? | Inside 3 Medieval Houses: How Different Was Daily Life? |

### プレイブック案(仮説)

以下は相関から機械的に作った**仮説**です。因果は確認していません。

- 目標の長さ(長尺): ヒット群の中央値 42.7 分の±25% = 32.0〜53.4 分
- リフトの高いタイトルの型 上位3点:
  - 具体性=「low」: ヒット 23% / ベース 8%(リフト 2.80)
  - フック型=「mystery_reveal」: ヒット 37% / ベース 15%(リフト 2.44)
  - 感情=「awe」: ヒット 15% / ベース 8%(リフト 1.80)
- 有望な話題クラスタ 上位5件(ヒット群の再生数中央値順):
  - ancient human technology(ヒット 3 本 / 再生数中央値 9,328,082)
  - egyptian archaeology documentaries(ヒット 3 本 / 再生数中央値 3,250,133)
  - human evolution(ヒット 3 本 / 再生数中央値 1,388,575)
  - ancient aliens(ヒット 3 本 / 再生数中央値 933,620)
  - medieval life(ヒット 4 本 / 再生数中央値 726,084)

注意: 生存者バイアス・視聴維持率データなし・小サンプル・タイトルのみ・小型モデルの未検証分類、という限界があります。

## ジャンル: asset_building

ヒット群 n=60(選定 60) / ベースライン群 n=60(選定 60)
比較の対象(ベースライン): 同じチャンネルの、ヒットに届かなかった投稿(ランダム標本ではありません)

#### フック型 (`hook_type`)

| 値 | ヒット n | ヒット割合 | ベース n | ベース割合 | リフト |
|---|---|---|---|---|---|
| warning_urgent | 12 | 20% | 7 | 12% | 1.71 |
| how_to | 9 | 15% | 7 | 12% | 1.29 |
| comparison | 5 | 8% | 4 | 7% | 1.25 |
| news_timely | 6 | 10% | 5 | 8% | 1.20 |
| other | 7 | 12% | 8 | 13% | 0.88 |
| numbered_list | 6 | 10% | 7 | 12% | 0.86 |
| question | 7 | 12% | 15 | 25% | 0.47 |
| mystery_reveal | 1 | 2% | 5 | 8% | 0.20 |
| definition_explainer | 1 | 2% | 1 | 2% | - |
| personal_story | 6 | 10% | 1 | 2% | - |

#### 感情 (`emotion`)

| 値 | ヒット n | ヒット割合 | ベース n | ベース割合 | リフト |
|---|---|---|---|---|---|
| hope | 18 | 30% | 10 | 17% | 1.80 |
| fear | 24 | 40% | 16 | 27% | 1.50 |
| curiosity | 16 | 27% | 23 | 38% | 0.70 |
| none | 1 | 2% | 6 | 10% | 0.17 |
| comfort | 0 | 0% | 3 | 5% | 0.00 |
| anger | 0 | 0% | 2 | 3% | - |
| awe | 1 | 2% | 0 | 0% | - |

#### 具体性 (`specificity`)

| 値 | ヒット n | ヒット割合 | ベース n | ベース割合 | リフト |
|---|---|---|---|---|---|
| high | 33 | 55% | 31 | 52% | 1.06 |
| medium | 22 | 37% | 21 | 35% | 1.05 |
| low | 5 | 8% | 8 | 13% | 0.62 |

#### 時事性 (`time_sensitivity`)

| 値 | ヒット n | ヒット割合 | ベース n | ベース割合 | リフト |
|---|---|---|---|---|---|
| timely | 31 | 52% | 16 | 27% | 1.94 |
| evergreen | 29 | 48% | 44 | 73% | 0.66 |

#### 釣り度 (`clickbait_level`)

| 値 | ヒット n | ヒット割合 | ベース n | ベース割合 | リフト |
|---|---|---|---|---|---|
| high | 27 | 45% | 9 | 15% | 3.00 |
| medium | 26 | 43% | 30 | 50% | 0.87 |
| low | 7 | 12% | 21 | 35% | 0.33 |

#### 実在の人物の物語 (`real_person_story`)

| 値 | ヒット n | ヒット割合 | ベース n | ベース割合 | リフト |
|---|---|---|---|---|---|
| false | 53 | 88% | 59 | 98% | 0.90 |
| true | 7 | 12% | 1 | 2% | - |

#### 数字を含む (`has_digit`)

| 値 | ヒット n | ヒット割合 | ベース n | ベース割合 | リフト |
|---|---|---|---|---|---|
| true | 42 | 70% | 38 | 63% | 1.11 |
| false | 18 | 30% | 22 | 37% | 0.82 |

#### 括弧【】「」を含む (`has_bracket`)

| 値 | ヒット n | ヒット割合 | ベース n | ベース割合 | リフト |
|---|---|---|---|---|---|
| true | 45 | 75% | 38 | 63% | 1.18 |
| false | 15 | 25% | 22 | 37% | 0.68 |

### 数値の事実(ヒット vs ベースライン)

| 指標 | ヒット | ベース |
|---|---|---|
| 長尺の長さ中央値(分) | 27.2 | 12.4 |
| タイトル文字数の中央値 | 46 | 42 |
| 数字を含むタイトルの割合 | 70% | 63% |
| 括弧【】「」を含む割合 | 75% | 63% |
| 再生数/日の中央値 | 9,166 | 183 |
| チャンネル登録者数の中央値 | 205,000 | 37,550 |
| 1年未満のチャンネルの割合 | 13% | 28% |
| 90日あたり投稿数の中央値 | 31.0 | 81.0 |

### 話題クラスタ(ヒット 3 本以上)

**ヒット本数の多い順**

| クラスタ | ヒット本数 | 再生数中央値 | 例1 | 例2 |
|---|---|---|---|---|
| stock market crash | 4 | 400,262 | 思い様々　生活切り詰めて投資する「NISA貧乏」は株価急落をどう見たか【もっと知りたい！】【グッド！モーニング】(2026年11月10日) | 新NISA民へ。週明け急落？退場しないで。 |
| nisa goals | 3 | 424,698 | 【nisa シミュレーション】この金額まで貯めたら放置でOK！資産が増え続けるNISAのゴール | 【nisa シミュレーション】NISAこの金額達成すると資産が1億円を超えるので人生上がれます |

**ヒット群の再生数中央値の高い順**

| クラスタ | ヒット本数 | 再生数中央値 | 例1 | 例2 |
|---|---|---|---|---|
| nisa goals | 3 | 424,698 | 【nisa シミュレーション】この金額まで貯めたら放置でOK！資産が増え続けるNISAのゴール | 【nisa シミュレーション】NISAこの金額達成すると資産が1億円を超えるので人生上がれます |
| stock market crash | 4 | 400,262 | 思い様々　生活切り詰めて投資する「NISA貧乏」は株価急落をどう見たか【もっと知りたい！】【グッド！モーニング】(2026年11月10日) | 新NISA民へ。週明け急落？退場しないで。 |

### プレイブック案(仮説)

以下は相関から機械的に作った**仮説**です。因果は確認していません。

- 目標の長さ(長尺): ヒット群の中央値 27.2 分の±25% = 20.4〜34.1 分
- リフトの高いタイトルの型 上位3点:
  - 釣り度=「high」: ヒット 45% / ベース 15%(リフト 3.00)
  - 時事性=「timely」: ヒット 52% / ベース 27%(リフト 1.94)
  - 感情=「hope」: ヒット 30% / ベース 17%(リフト 1.80)
- 有望な話題クラスタ 上位5件(ヒット群の再生数中央値順):
  - nisa goals(ヒット 3 本 / 再生数中央値 424,698)
  - stock market crash(ヒット 4 本 / 再生数中央値 400,262)

注意: 生存者バイアス・視聴維持率データなし・小サンプル・タイトルのみ・小型モデルの未検証分類、という限界があります。

## ジャンル: cozy_life

ヒット群 n=60(選定 60) / ベースライン群 n=60(選定 60)
比較の対象(ベースライン): 新着順の標本(date_samples)

#### フック型 (`hook_type`)

| 値 | ヒット n | ヒット割合 | ベース n | ベース割合 | リフト |
|---|---|---|---|---|---|
| how_to | 21 | 35% | 4 | 7% | 5.25 |
| personal_story | 8 | 13% | 5 | 8% | 1.60 |
| other | 27 | 45% | 47 | 78% | 0.57 |
| definition_explainer | 0 | 0% | 1 | 2% | - |
| mystery_reveal | 2 | 3% | 1 | 2% | - |
| question | 1 | 2% | 1 | 2% | - |
| warning_urgent | 1 | 2% | 1 | 2% | - |

#### 感情 (`emotion`)

| 値 | ヒット n | ヒット割合 | ベース n | ベース割合 | リフト |
|---|---|---|---|---|---|
| curiosity | 8 | 13% | 5 | 8% | 1.60 |
| nostalgia | 10 | 17% | 7 | 12% | 1.43 |
| comfort | 29 | 48% | 38 | 63% | 0.76 |
| awe | 2 | 3% | 7 | 12% | 0.29 |
| anger | 0 | 0% | 1 | 2% | - |
| fear | 3 | 5% | 1 | 2% | - |
| hope | 5 | 8% | 1 | 2% | - |
| none | 3 | 5% | 0 | 0% | - |

#### 具体性 (`specificity`)

| 値 | ヒット n | ヒット割合 | ベース n | ベース割合 | リフト |
|---|---|---|---|---|---|
| high | 30 | 50% | 25 | 42% | 1.20 |
| medium | 27 | 45% | 31 | 52% | 0.87 |
| low | 3 | 5% | 4 | 7% | 0.75 |

#### 時事性 (`time_sensitivity`)

| 値 | ヒット n | ヒット割合 | ベース n | ベース割合 | リフト |
|---|---|---|---|---|---|
| evergreen | 60 | 100% | 49 | 82% | 1.22 |
| timely | 0 | 0% | 11 | 18% | 0.00 |

#### 釣り度 (`clickbait_level`)

| 値 | ヒット n | ヒット割合 | ベース n | ベース割合 | リフト |
|---|---|---|---|---|---|
| medium | 13 | 22% | 8 | 13% | 1.62 |
| low | 42 | 70% | 52 | 87% | 0.81 |
| high | 5 | 8% | 0 | 0% | - |

#### 実在の人物の物語 (`real_person_story`)

| 値 | ヒット n | ヒット割合 | ベース n | ベース割合 | リフト |
|---|---|---|---|---|---|
| false | 60 | 100% | 60 | 100% | 1.00 |

#### 数字を含む (`has_digit`)

| 値 | ヒット n | ヒット割合 | ベース n | ベース割合 | リフト |
|---|---|---|---|---|---|
| true | 16 | 27% | 6 | 10% | 2.67 |
| false | 44 | 73% | 54 | 90% | 0.81 |

#### 括弧【】「」を含む (`has_bracket`)

| 値 | ヒット n | ヒット割合 | ベース n | ベース割合 | リフト |
|---|---|---|---|---|---|
| false | 59 | 98% | 60 | 100% | 0.98 |
| true | 1 | 2% | 0 | 0% | - |

### 数値の事実(ヒット vs ベースライン)

| 指標 | ヒット | ベース |
|---|---|---|
| 長尺の長さ中央値(分) | 17.6 | 16.0 |
| タイトル文字数の中央値 | 94 | 92 |
| 数字を含むタイトルの割合 | 27% | 10% |
| 括弧【】「」を含む割合 | 2% | 0% |
| 再生数/日の中央値 | 173,188 | 534 |
| チャンネル登録者数の中央値 | 117,500 | 111,000 |
| 1年未満のチャンネルの割合 | 75% | 67% |
| 90日あたり投稿数の中央値 | 44.0 | 75.5 |

### 話題クラスタ(ヒット 3 本以上)

**ヒット本数の多い順**

| クラスタ | ヒット本数 | 再生数中央値 | 例1 | 例2 |
|---|---|---|---|---|
| ghibli village asmr | 10 | 3,895,884 | 🌧️🐈🍲A Rainy Day, Tiny Kitten & a Special Family Lunch  / Ghibli Village Life | 🌙 1990s Indian Village Summer Night 🌧️ Power Cut, Rooftop Sleep & Magical Monsoon Rain / Ghibli ASMR |
| village cooking recipes | 9 | 5,392,569 | Chinese Rural Cuisine / Eating Grilled Fish & Roast Duck Today — Crispy & Smoky 🇨🇳 #rurallife | 🍗Bihari Champaran Chicken Recipe 🔥❤️/ #shorts #villagelife #ghibli #asmr #chicken #cooking #viral |
| village cooking & rural life | 8 | 3,340,824 | Rainy Village Lunch / Jackfruit Curry & Roti #ghiblistyle #asmr #shorts | Rainy Day in a 90s Indian Village / Traditional Chicken Curry & Village Life |
| rainy village cooking | 7 | 6,944,383 | Cozy Rainy Paniyaram making in a peaceful Village#hubby #couple#villagelife #ghibli #lifeisbutadream | 🌧️ Making Spicy Vegetable Noodles in Heavy Monsoon Rain 🍜 / Cozy Village Cooking ASMR 🐐#villagelife |
| ghibli village farm life | 5 | 14,590,499 | The Little Tree Hut That Saved Their Farm 🥜🌧️ / Ghibli Village #villagelife #rainsounds #farmlife | Building a Tree House to Protect Watermelons / Ghibli Village Life #asmr #ghibli #short #nostalgia  |
| traditional village cooking | 3 | 21,647,140 | Giant Crab Sticky Rice 🦀 / Cozy Village Cooking | 🌿 From Okra Harvest to a Sweet Surprise 💚🌧️ / Traditional Village Cooking / Cozy 90s Life #shorts |
| outdoor wild food cooking | 3 | 7,331,941 | Catching Crayfish, Fishing from a Bamboo Raft & Cooking Outdoors #cooking #food #asmr | Harvesting GIANT Freshwater Snails! 🐌 #rurallife #food #asmr#harvesting #countrysidelife #cooking |

**ヒット群の再生数中央値の高い順**

| クラスタ | ヒット本数 | 再生数中央値 | 例1 | 例2 |
|---|---|---|---|---|
| traditional village cooking | 3 | 21,647,140 | Giant Crab Sticky Rice 🦀 / Cozy Village Cooking | 🌿 From Okra Harvest to a Sweet Surprise 💚🌧️ / Traditional Village Cooking / Cozy 90s Life #shorts |
| ghibli village farm life | 5 | 14,590,499 | The Little Tree Hut That Saved Their Farm 🥜🌧️ / Ghibli Village #villagelife #rainsounds #farmlife | Building a Tree House to Protect Watermelons / Ghibli Village Life #asmr #ghibli #short #nostalgia  |
| outdoor wild food cooking | 3 | 7,331,941 | Catching Crayfish, Fishing from a Bamboo Raft & Cooking Outdoors #cooking #food #asmr | Harvesting GIANT Freshwater Snails! 🐌 #rurallife #food #asmr#harvesting #countrysidelife #cooking |
| rainy village cooking | 7 | 6,944,383 | Cozy Rainy Paniyaram making in a peaceful Village#hubby #couple#villagelife #ghibli #lifeisbutadream | 🌧️ Making Spicy Vegetable Noodles in Heavy Monsoon Rain 🍜 / Cozy Village Cooking ASMR 🐐#villagelife |
| village cooking recipes | 9 | 5,392,569 | Chinese Rural Cuisine / Eating Grilled Fish & Roast Duck Today — Crispy & Smoky 🇨🇳 #rurallife | 🍗Bihari Champaran Chicken Recipe 🔥❤️/ #shorts #villagelife #ghibli #asmr #chicken #cooking #viral |
| ghibli village asmr | 10 | 3,895,884 | 🌧️🐈🍲A Rainy Day, Tiny Kitten & a Special Family Lunch  / Ghibli Village Life | 🌙 1990s Indian Village Summer Night 🌧️ Power Cut, Rooftop Sleep & Magical Monsoon Rain / Ghibli ASMR |
| village cooking & rural life | 8 | 3,340,824 | Rainy Village Lunch / Jackfruit Curry & Roti #ghiblistyle #asmr #shorts | Rainy Day in a 90s Indian Village / Traditional Chicken Curry & Village Life |

### プレイブック案(仮説)

以下は相関から機械的に作った**仮説**です。因果は確認していません。

- 目標の長さ(長尺): ヒット群の中央値 17.6 分の±25% = 13.2〜21.9 分
- リフトの高いタイトルの型 上位3点:
  - フック型=「how_to」: ヒット 35% / ベース 7%(リフト 5.25)
  - 数字を含む=「true」: ヒット 27% / ベース 10%(リフト 2.67)
  - 釣り度=「medium」: ヒット 22% / ベース 13%(リフト 1.62)
- 有望な話題クラスタ 上位5件(ヒット群の再生数中央値順):
  - traditional village cooking(ヒット 3 本 / 再生数中央値 21,647,140)
  - ghibli village farm life(ヒット 5 本 / 再生数中央値 14,590,499)
  - outdoor wild food cooking(ヒット 3 本 / 再生数中央値 7,331,941)
  - rainy village cooking(ヒット 7 本 / 再生数中央値 6,944,383)
  - village cooking recipes(ヒット 9 本 / 再生数中央値 5,392,569)

注意: 生存者バイアス・視聴維持率データなし・小サンプル・タイトルのみ・小型モデルの未検証分類、という限界があります。
