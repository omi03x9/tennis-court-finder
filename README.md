# テニスコート空き検索

柏市・流山市・我孫子市の公開予約情報から、指定した1日の時間帯にソフトテニスで使える1面を探すWebアプリです。予約操作やログインは行いません。スマートフォンとPCに対応しています。

**[検索サイトを開く](https://tennis-court-finder.onrender.com/)**

[GitHubリポジトリ](https://github.com/omi03x9/tennis-court-finder)。Renderの無料プランで公開しています。しばらく利用がない場合、初回の表示に起動待ちが発生します。

## 検索の動作

- 検索のたびに各市の公開情報を取得します。
- 同じコートを連続して使える候補を優先します。他の連続利用可能なコートも表示できます。
- 連続利用できるコートがなければ、同じ施設内でコートを移動する組み合わせを探します。施設をまたぐ組み合わせは出しません。
- 希望時間を含む予約枠全体を「必要な予約時間」として表示します。時間の隙間がある組み合わせは候補にしません。
- 我孫子市は1予約3時間以内になるよう、必要な予約を分けて表示します。
- 取得に失敗した市はエラーとして表示します。取得失敗を「空きなし」として扱いません。

取得結果は空き状況の照会です。実際の予約可否には各市の利用資格、申込期間、予約上限などが適用されます。公式サイトで最終確認してください。

## 起動

Python 3.12と`lxml`を使用します。プロジェクトのフォルダ内で実行してください。

```powershell
python -m pip install -r requirements.txt
python server.py
```

ブラウザーで <http://127.0.0.1:8765/> を開きます。公開環境では`HOST=0.0.0.0`と公開基盤が指定する`PORT`を使用します。

## GitHubへの保存と公開

ソースコードをGitHubに置き、PythonサーバーはRenderなどのWebサービスで動かす構成です。各市の予約サイトとの通信はサーバー側で行うため、静的ファイルを配信するGitHub Pagesだけでは動作しません。

公開の具体的な手順は[DEPLOY.md](DEPLOY.md)、検証内容は[VALIDATION.md](VALIDATION.md)を参照してください。Render用の無料プラン設定を`render.yaml`に含めています。

## 構成

| ファイル | 役割 |
| --- | --- |
| `sources.py` | 市ごとの公開情報の取得・解析 |
| `planner.py` | 連続利用とコート移動の判定 |
| `server.py` | 検索APIと画面の配信 |
| `public/` | 画面、スタイル、ブラウザー側処理 |
| `tests/test_planner.py` | 時間帯とコートの組み合わせの検証 |

検索は3市を並行して照会し、完了した市から順に結果を表示します。同じ市への同時照会を制限し、外部への通信先は固定しています。予約サイトの画面・パラメーターが変更された場合はアダプターの更新が必要です。

## テスト

```powershell
python -m unittest discover -s tests -v
node --check public/app.js
```

## 情報源

- [柏市公共施設予約システム](https://shisetsu-reservation.city.kashiwa.lg.jp/)
- [流山市の公共施設予約システム案内](https://www.city.nagareyama.chiba.jp/eservice/1010248/index.html) / [予約システム](https://web136.rsv.ws-scs.jp/nagare/web/)
- [ちば施設予約システム（我孫子市のみ）](https://www.cm1.eprs.jp/yoyaku-chiba/ew/)

各市の公式サービスではありません。
