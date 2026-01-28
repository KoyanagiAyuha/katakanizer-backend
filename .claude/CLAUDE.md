# Katakanizer Backend

日記をお笑い芸人風に変換する API サーバー

## Tech Stack

- **Framework**: FastAPI
- **ORM**: SQLAlchemy 2.x (async)
- **Database**: PostgreSQL
- **Auth**: Firebase Authentication
- **AI**: OpenAI GPT-5
- **Deploy**: Vercel (Serverless)

## OpenAI モデルについて（重要）

**GPT-5 系のみを使用すること。GPT-4 系（GPT-4, GPT-4o, GPT-4.1 など）は絶対に使用禁止。**

- 使用モデル: `gpt-5-nano`（軽量タスク向け）
- API: Responses API（推奨方式）

## Local Development

```bash
# DB起動
docker compose up -d

# サーバー起動
uv run uvicorn src.main:app --reload
```

## Deploy

```bash
vercel deploy
```
