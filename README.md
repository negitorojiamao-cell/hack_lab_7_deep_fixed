# hack_lab_7_deep_fixed

## セットアップ

このプロジェクトを動かすには、Google Gemini APIキーを自分で取得し、ローカル環境に設定する必要があります。

### 1. Gemini APIキーを取得する

1. [Google AI Studio の APIキー発行ページ](https://aistudio.google.com/apikey) を開きます。
2. Googleアカウントでログインします。
3. APIキーを作成し、表示されたキーをコピーします。

### 2. `.env.example` を `.env` にコピーする

プロジェクトのルートフォルダー（`README.md` があるフォルダー）で、`.env.example` をコピーして、ファイル名を **`.env`** に変更してください。

Windows の PowerShell を使う場合は、プロジェクトのルートフォルダーで次を実行します。

```powershell
Copy-Item .env.example .env
```

### 3. `.env` に自分のAPIキーを設定する

作成した `.env` をメモ帳などのテキストエディターで開き、`GEMINI_API_KEY` の右側に、手順1で取得した自分のAPIキーを貼り付けて保存します。

```dotenv
GEMINI_API_KEY=ここに自分のGemini APIキーを貼り付ける
GEMINI_MODEL=gemini-3.5-flash-lite
HACKLAB_PORT=8765
HACKLAB_DAILY_AI_LIMIT=20
```

**重要：** `ここに自分のGemini APIキーを貼り付ける` の部分は説明用の文字列です。必ず実際に取得したAPIキーに置き換えてください。引用符で囲む必要はありません。

### 4. 起動する

上記の設定を保存したあと、プロジェクトの通常の起動手順に従ってアプリを起動してください。

## 設定項目

| 項目 | 説明 |
| --- | --- |
| `GEMINI_API_KEY` | Google AI Studioで取得したGemini APIキー |
| `GEMINI_MODEL` | 使用するGeminiモデル |
| `HACKLAB_PORT` | アプリが使用するポート番号 |
| `HACKLAB_DAILY_AI_LIMIT` | 1日あたりのAI利用上限 |

## APIキーの取り扱いについて

- **実際のAPIキーをGitHubにアップロードしないでください。**
- `.env` は自分のPC内だけに保存してください。
- このリポジトリでは `.gitignore` に `.env` を登録しているため、通常はGitの追跡対象になりません。
- `.env.example` は設定項目を共有するための見本ファイルです。実際のAPIキーを書き込まず、そのまま残してください。
- APIキーを誤って公開した場合は、Google AI Studioでそのキーを無効化し、新しいキーを発行してください。
