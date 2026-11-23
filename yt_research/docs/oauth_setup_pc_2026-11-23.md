# YouTube 連携(OAuth)設定手順 — PC で行う作業

目的: 動画のアップロード(最初は非公開)と、再生数などの取得を、AI の仕組みから行えるようにする接続を作ります。
**API キー(YOUTUBE_API_KEY)とは別物**です。キーは公開情報の読み取り専用で、アップロードと自分の分析データには OAuth が必要です。

所要: 30〜45分。**事業専用の Google アカウントで**ログインして行います(建設事業のアカウントではありません)。
秘密にするもの: クライアントシークレット、リフレッシュトークン。**チャットには貼らないでください。**

表記: [未確認] は、公式の全文で確認できていない点です(画面の表示を優先してください)。

## 1. Google Cloud のプロジェクトを作る
1. https://console.cloud.google.com を開く(事業専用アカウントで)。
2. 画面上部のプロジェクト選択 →「新しいプロジェクト」→ 名前は「yt-publisher」など → 作成。
3. 作成したプロジェクトを選択した状態にする。

## 2. API を有効にする
1. 「API とサービス」→「ライブラリ」。
2. 「YouTube Data API v3」を検索 →「有効にする」。
3. 「YouTube Analytics API」を検索 →「有効にする」。

## 3. OAuth 同意画面
1. 「API とサービス」→「OAuth 同意画面」(新しい表示では「Google Auth Platform」)。
2. 「開始」→ アプリ名「yt-publisher」、サポートメールは自分のアドレス。
3. 対象: **外部**。
4. 連絡先メールを入力して作成。
5. 「対象」(Audience)で、**テストユーザーに自分のアドレスを追加**する。
6. **公開ステータスに注意**:
   - 「テスト」のままだと、リフレッシュトークンが**7日で失効する**との情報があります(フォーラムの情報で、公式の全文は未確認)。
   - 「本番環境に公開」にすると失効しない、との情報があります。ただし、機密性の高いスコープ(YouTube への投稿など)で本番にすると、Google の確認(審査)が必要になる場合があります。自分だけが使う場合は「未確認のアプリ」と表示されますが、確認画面で自分が承認すれば使えるはずです [未確認]。
   - 最初は「テスト」で進めて、7日ごとにトークンを取り直す運用でも構いません。

## 4. OAuth クライアント ID を作る
1. 「API とサービス」→「認証情報」→「認証情報を作成」→「OAuth クライアント ID」。
2. アプリケーションの種類: **ウェブ アプリケーション**。
3. 名前: 「yt-publisher-web」。
4. **承認済みのリダイレクト URI** に、次を追加:
   `https://developers.google.com/oauthplayground`
5. 作成 → 表示される**クライアント ID と クライアント シークレット**を、安全な場所(パスワード管理など)に保存。

## 5. リフレッシュトークンを取る(OAuth 2.0 Playground)
1. https://developers.google.com/oauthplayground を開く。
2. 右上の歯車 → 「**Use your own OAuth credentials**」にチェック → 手順4のクライアント ID / シークレットを入力。「OAuth flow」は **Server-side**、「Access type」は **Offline**。
3. 左の「Step 1」の下のほうにある入力欄に、次のスコープを**1つずつ**入れる(または一覧から選ぶ):
   - `https://www.googleapis.com/auth/youtube.upload`
   - `https://www.googleapis.com/auth/youtube`
   - `https://www.googleapis.com/auth/yt-analytics.readonly`
   (収益データは、後で `https://www.googleapis.com/auth/yt-analytics-monetary.readonly` を追加)
4. 「Authorize APIs」→ 事業専用アカウントで承認(「未確認のアプリ」と出たら「詳細」→「(アプリ名)に移動」)。
5. 「Exchange authorization code for tokens」→ **Refresh token** が表示される。
6. 注意: Playground 自体の共有の資格情報だと、リフレッシュトークンが24時間で失効するので、**必ず自分のクライアントを使う設定(手順2)で取る**こと。

## 6. GitHub のシークレットに登録する
リポジトリ `takahashi-shoten/takahashi-dashboard` → Settings → Secrets and variables → Actions → 「New repository secret」。次の3つを登録します。
- `YT_OAUTH_CLIENT_ID`
- `YT_OAUTH_CLIENT_SECRET`
- `YT_OAUTH_REFRESH_TOKEN`

値は**ここ(GitHub)にだけ**入力し、チャットには貼らないでください。

## 7. 完了後(私が行う)
- 接続確認(チャンネル情報の取得)。
- 最初の動画の、**非公開**でのアップロード確認。
- 動画の公開(Public)は、**あなたの承認が記録されるまで、システムが拒否**します。

## 確認できていない点(実機で確かめます)
1. リフレッシュトークンの有効期間(テスト/本番)。
2. 動画1本のアップロードに使うクォータ(1,600ユニットとされる)と、1日の上限(10,000)。
3. インプレッションとクリック率の取得に使う項目名(`videoThumbnailImpressions` と `videoThumbnailImpressionsClickRate` が候補)。
4. 収益データの取得条件。
