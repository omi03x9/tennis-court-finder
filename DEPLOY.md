# 公開手順

公開URLは[M2TIO COURT FINDER](https://m2tio-court-finder.vercel.app/)、保存先は[omi03x9/tennis-court-finder](https://github.com/omi03x9/tennis-court-finder)です。2026年10月4日にVercelの無料Hobbyプランへ移行しました。

## Vercel

1. 個人・非商用向けの無料Hobbyプランでログインします。Proや有料トライアルは不要です。
2. GitHubアプリのRepository accessをOnly select repositoriesにし、`tennis-court-finder`だけを指定します。初回の権限付与・利用規約への同意は本人が行ってください。
3. このリポジトリをImportし、Project Nameは`m2tio-court-finder`、Application PresetはOther、Root Directoryは`./`を選びます。
4. `vercel.json`の設定でデプロイします。画面は`public/`、検索APIは`api/search.py`です。東京リージョン、最大120秒、Python 3.12を使用します。
5. ログインしていないブラウザーから、当日の初期日付、19:00〜21:00、タイトル、3市の検索、スマホ幅の表示を確認します。

GitHubのmainを更新すると自動デプロイされます。各市の画面が変わった場合は`sources.py`を修正し、実データで検証してください。

画面表示にはRenderの15分休止後の起動待ちがありません。検索APIは初回の初期化や自治体サイトへの照会時間が必要で、検索が常に即時完了する保証はありません。無料枠は[Vercel Hobbyの公式説明](https://vercel.com/docs/plans/hobby)で確認してください。

同時検索のセマフォは各Python実行インスタンス内の制限です。複数インスタンスをまたぐ全体の制限ではありません。

## Render版

既存の[Render URL](https://tennis-court-finder.onrender.com/)も残しています。`render.yaml`は再作成用です。Public Git Repository方式なので、更新時はRenderサービス画面のManual Deploy → Deploy latest commitを使います。無料プランはアクセスが15分ないと休止し、再開に約1分かかります。

[GitHub Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages)は静的配信用なので、このPython検索APIを単独では実行できません。
