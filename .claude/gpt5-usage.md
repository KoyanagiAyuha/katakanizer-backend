# GPT-5 使い方ガイド

## 重要: GPT-4系は使用禁止

このプロジェクトでは **GPT-5 系のみ** を使用する。GPT-4、GPT-4o、GPT-4.1 などの GPT-4 系モデルは絶対に使用しないこと。

## 利用可能なモデル

| モデル | 用途 | 価格（入力/出力） |
|-------|------|-----------------|
| `gpt-5-nano` | 軽量タスク（分類、要約） | $0.05 / $0.40 per 1M tokens |
| `gpt-5-mini` | 中規模タスク | - |
| `gpt-5` | 汎用 | - |
| `gpt-5.2` | 最新・高性能 | $1.75 / $14 per 1M tokens |

## Responses API（推奨）

GPT-5 では **Responses API** が推奨される。Chat Completions API も引き続きサポートされているが、新規開発では Responses API を使用すること。

### 基本的な使い方（同期）

```python
from openai import OpenAI

client = OpenAI(api_key="your-api-key")

response = client.responses.create(
    model="gpt-5-nano",
    instructions="あなたはお笑い芸人です。",  # システムプロンプト相当
    input=[
        {
            "role": "user",
            "content": [{"type": "input_text", "text": "こんにちは"}],
        }
    ],
    max_output_tokens=2000,
    temperature=0.8,
)

print(response.output_text)
```

### 非同期での使い方

```python
from openai import AsyncOpenAI

client = AsyncOpenAI(api_key="your-api-key")

response = await client.responses.create(
    model="gpt-5-nano",
    instructions="あなたはお笑い芸人です。",
    input=[
        {
            "role": "user",
            "content": [{"type": "input_text", "text": "こんにちは"}],
        }
    ],
    max_output_tokens=2000,
    temperature=0.8,
)

print(response.output_text)
```

## Chat Completions API との違い

| 項目 | Chat Completions API | Responses API |
|-----|---------------------|---------------|
| メソッド | `client.chat.completions.create()` | `client.responses.create()` |
| システムプロンプト | `{"role": "system", "content": "..."}` | `instructions="..."` |
| ユーザー入力 | `{"role": "user", "content": "..."}` | `{"role": "user", "content": [{"type": "input_text", "text": "..."}]}` |
| 出力トークン制限 | `max_tokens` | `max_output_tokens` |
| レスポンス取得 | `response.choices[0].message.content` | `response.output_text` |

## パラメータ

### 主要パラメータ

- `model`: 使用するモデル（`gpt-5-nano`, `gpt-5-mini`, `gpt-5`, `gpt-5.2`）
- `instructions`: システムプロンプト（モデルの振る舞いを指定）
- `input`: ユーザー入力のリスト
- `max_output_tokens`: 出力トークンの上限
- `temperature`: 出力のランダム性（0.0〜2.0、デフォルト1.0）

### GPT-5.1以降の追加パラメータ

- `reasoning`: 推論レベル（`none`, `low`, `medium`, `high`, `xhigh`）
  - `gpt-5-nano` ではデフォルト `none`

## このプロジェクトでの実装例

`src/services/openai.py` を参照：

```python
from openai import AsyncOpenAI

client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

response = await client.responses.create(
    model="gpt-5-nano",
    instructions=prompt_template,
    input=[
        {
            "role": "user",
            "content": [{"type": "input_text", "text": user_prompt}],
        }
    ],
    max_output_tokens=2000,
    temperature=0.8,
)

return response.output_text or ""
```
