# M2TIO COURT FINDER

柏市・流山市・我孫子市の公開予約情報から、指定した1日の時間帯にソフトテニスで使える1面を探すWebアプリです。予約操作やログインは行いません。スマートフォンとPCに対応しています。

**[検索サイトを開く](https://m2tio-court-finder.vercel.app/)**

[GitHubリポジトリ](https://github.com/omi03x9/tennis-court-finder)。Vercelの無料Hobbyプランで公開しています。画面は静的配信、検索APIはPython Functionsで実行します。検索時には自治体サイトへの照会時間がかかります。

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

ソースコードをGitHubに置き、Vercelで画面とPython検索APIを公開する構成です。各市の予約サイトとの通信はサーバー側で行うため、静的ファイルを配信するGitHub Pagesだけでは動作しません。

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

## Vercelでの公開

初期時刻は19:00〜21:00、日付は日本時間の当日です。Vercelでは`public/`を静的配信し、`api/search.py`が既存の検索処理を実行します。`vercel.json`は東京リージョン・最大120秒で設定しています。新しい依存ライブラリは不要です。2026年10月4日にVercelで公開し、匿名ブラウザーから3市・79面の検索成功を確認しました。

Vercelの無料HobbyプランでGitHubリポジトリをImportし、Framework PresetはOther、Root Directoryはリポジトリ直下とします。設定は`vercel.json`を使用します。公開後は匿名でのページ表示と3市の検索を確認してください。APIの同時検索制限は各実行インスタンス内に適用されます。
