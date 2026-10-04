# 公開手順

想定する保存先はGitHubアカウント`omi03x9`の新規リポジトリ`tennis-court-finder`です。公開用のコードを準備した段階では、リポジトリや公開URLが作成済みとは限りません。

## 1. GitHub

1. GitHubに`omi03x9`としてサインインします。
2. `tennis-court-finder`という新規リポジトリを作ります。
3. このフォルダのファイルを保存します。`research/`、`.env`、`__pycache__/`、`.venv/`は除外します。
4. mainブランチに`server.py`と`render.yaml`があることを確認します。

## 2. Render

1. [Render](https://dashboard.render.com/)にサインインします。アカウントを作る場合、利用規約への同意は本人が行ってください。
2. New → Web ServiceでGitHubの`omi03x9/tennis-court-finder`を選びます。GitHub連携は対象リポジトリだけに絞れます。連携権限を本人が確認してください。
3. 以下の設定を確認します。Blueprintから`render.yaml`を使う方法もあります。

| 項目 | 値 |
| --- | --- |
| Runtime | Python |
| Branch | main |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `python server.py` |
| Instance Type | Free |
| Health Check Path | `/health` |
| Environment | `HOST=0.0.0.0`, `PYTHONIOENCODING=utf-8`, `PYTHON_VERSION=3.12.8` |

4. デプロイし、成功後に表示された`https://…onrender.com`のURLを開きます。
5. スマホとPCで実際に検索し、3市の照会が成功することを確認します。ローカルで成功しても、公開環境からの接続可否は別途検証が必要です。

無料サービスは一定時間アクセスがないと停止し、次のアクセス時に起動を待つ場合があります。最新の条件は[Renderの無料プラン説明](https://render.com/docs/free)で確認してください。有料プランや支払い情報の登録はこの手順の前提にしていません。

[GitHub Pagesは静的サイトのホスティング](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages)です。このアプリではPythonの実行基盤が必要です。

## 更新

GitHubのコードを更新し、Renderで再デプロイします。各市の画面が変わって取得エラーが出る場合は、`sources.py`を修正して実データで検証してから公開してください。
