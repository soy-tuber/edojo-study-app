# 江戸川女子中 入試問題 勉強アプリ

令和7年度（2025年度）江戸川女子中学校の入試問題を、左に問題ページ・右に関連YouTube動画を並べて学習できる Streamlit アプリです。家庭での私的学習用に作成しています。

## 使い方（ローカル）

`run.bat` をダブルクリックするとブラウザでアプリが開きます。

または、コマンドで起動する場合:

```
"%LOCALAPPDATA%\Programs\Python\Python312\python.exe" -m streamlit run app.py
```

開いたら `http://localhost:8501` にアクセスし、**PINコード**を入力します。

## PINコード

アプリの入口にPINロックがあります。PINは Streamlit のシークレット（`APP_PIN`）で管理します。

- **ローカル**: `.streamlit/secrets.toml` に `APP_PIN = "..."` を記載（このファイルは `.gitignore` 済み）。
- **Streamlit Community Cloud**: アプリの `Settings > Secrets` に同じ内容を貼り付け。
- シークレット未設定時の既定PINは `app.py` 内の `APP_PIN` 既定値が使われます。

## Streamlit Community Cloud へのデプロイ

1. このリポジトリを GitHub に push 済みにする。
2. https://share.streamlit.io にログイン。
3. 「New app」→ このリポジトリ／ブランチ `main`／メインファイル `app.py` を指定。
4. 「Advanced settings > Secrets」に以下を貼り付け:
   ```
   APP_PIN = "1203"
   ```
5. Deploy。発行されたURLにPINを入れて利用します。

## 画面

- **サイドバー** … 科目（算数・理科・社会）と回（第1〜3回）をえらぶ。「問題ページだけ表示」で計算用紙・表紙を隠せます。
- **左** … 問題ページの画像。「まえ／つぎ」ボタンやジャンプで移動。
- **右** … キーワードに関連したYouTube動画。キーワード欄を書きかえると `index.json` に自動保存されます。

## ファイル構成

| ファイル | 説明 |
|---|---|
| `app.py` | アプリ本体（PINロック付き） |
| `build_pages.py` | PDF をページ画像に変換し `index.json` を生成 |
| `index.json` | 問題ページ一覧と検索キーワード |
| `pages/` | ページ画像 |
| `requirements.txt` | 依存パッケージ |
| `run.bat` | ローカル起動用 |

## 問題PDFを入れ替え・追加するとき

`build_pages.py` はローカルの `C:\Users\q0702\edojo_2025` にある問題PDFを参照します。差し替えたら次を実行:

```
"%LOCALAPPDATA%\Programs\Python\Python312\python.exe" build_pages.py
```

※ 国語は問題文が非公開のため対象外です。

## 注意

- 掲載している入試問題は江戸川女子中学校の著作物です。本リポジトリ・アプリは家庭内の私的学習を目的としています。
- YouTube の検索結果を APIキーなしで取得しています。仕様変更で取得できない場合は「YouTubeで開く」ボタンから直接検索できます。
