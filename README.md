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

## 1ページに複数の単元

入試問題は1ページに別々の単元の問題が並んでいることが多いため、右パネルでは
**ページ内の単元ごとに見出し（📘 単元名）を立て、その単元の動画を縦に並べて**表示します。
各単元の検索キーワードは `index.json` の `topics`（`{label, query}` のリスト）で管理します。

## AI先生に質問する（Gemini チャット）

画面の **右下に浮かぶ「🤖 AI先生に きく」ボタン** から、AI先生（Gemini）に質問できます。

- ボタンを押すとチャット枠が右下にひらきます（問題は隠れません）。「✕」でとじられます。
- **「📖 この問題を解説して」** ワンタップで、いま見ている問題の解説が始まります。自由に質問も入力できます。
- AI先生は問題ページの画像を見て答えます。いきなり答えを言わず、ヒントから順に教える小学生向けの口調です。
- 会話は **問題ページごと** に分かれます（ページを移動しても各ページの会話は残ります）。「会話をけす」でリセット。
- 使うには Gemini API キーが必要です（https://aistudio.google.com/apikey で無料取得、無料枠で十分）。
  - **ローカル**: `.streamlit/secrets.toml` の `GEMINI_API_KEY` に貼り付け。
  - **Streamlit Community Cloud**: `Settings > Secrets` に `GEMINI_API_KEY` を追加。
- キー未設定の場合、チャット枠は「準備中」と表示されます。

## Streamlit Community Cloud へのデプロイ

1. このリポジトリを GitHub に push 済みにする。
2. https://share.streamlit.io にログイン。
3. 「New app」→ このリポジトリ／ブランチ `main`／メインファイル `app.py` を指定。
4. 「Advanced settings > Secrets」に以下を貼り付け:
   ```
   APP_PIN = "1203"
   GEMINI_API_KEY = "（Gemini APIキー）"
   ```
5. Deploy。発行されたURLにPINを入れて利用します。

## 画面

- **サイドバー** … 科目（算数・理科・社会）と回（第1〜3回）をえらぶ。「問題ページだけ表示」で計算用紙・表紙を隠せます。
- **左** … 問題ページの画像。「まえ／つぎ」ボタンやジャンプで移動。
- **右** … そのページの単元ごとに、見出し（📘 単元名）＋関連YouTube動画を縦に並べて表示。各単元のキーワード欄を書きかえると `index.json` に自動保存されます。
- **右下** … AI先生チャット（「🤖 AI先生に きく」ボタンでひらく浮動ウィンドウ）。

## ファイル構成

| ファイル | 説明 |
|---|---|
| `app.py` | アプリ本体（PINロック付き） |
| `build_pages.py` | PDF をページ画像に変換し `index.json` を生成 |
| `build_db.py` | `index.json` と問題PDFから SQLite DB（`edojo.db`）を生成 |
| `index.json` | 問題ページ一覧と単元別の検索キーワード（`topics`） |
| `pages/` | ページ画像 |
| `requirements.txt` | 依存パッケージ |
| `run.bat` | ローカル起動用 |

## ローカルで SQLite データベースを作る

`index.json` のメタデータと、問題PDFから抽出した問題文を 1 つの SQLite DB に
まとめたいときは次を実行します（`edojo.db` がカレントに生成されます）:

```
"%LOCALAPPDATA%\Programs\Python\Python312\python.exe" build_db.py
```

- 入試PDFはテキスト埋め込み済みのため、AI/OCR を使わず PyMuPDF で問題文を抽出します（図・数式画像は対象外）。
- テーブル: `exams`（試験）/ `pages`（ページ・問題文）/ `topics`（単元・検索キーワード）。
- `edojo.db` はローカル生成物のため `.gitignore` 済み（配布しません）。

## 問題PDFを入れ替え・追加するとき

`build_pages.py` はローカルの `C:\Users\q0702\edojo_2025` にある問題PDFを参照します。差し替えたら次を実行:

```
"%LOCALAPPDATA%\Programs\Python\Python312\python.exe" build_pages.py
```

※ 国語は問題文が非公開のため対象外です。

## 注意

- 掲載している入試問題は江戸川女子中学校の著作物です。本リポジトリ・アプリは家庭内の私的学習を目的としています。
- YouTube の検索結果を APIキーなしで取得しています。仕様変更で取得できない場合は「YouTubeで開く」ボタンから直接検索できます。
