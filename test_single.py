#!/usr/bin/env python3
"""
単一プロンプトテスト
"""

import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("OPENAI_API_KEY not found")
    exit(1)

client = OpenAI(api_key=api_key)

text = "I'm going to get out of here"

prompt = f"""Convert English SOUNDS to katakana (NOT translation):
"{text}"

Break into natural speech phrases:
I'm going to|アムガナ|アイム ゴーイング トゥ
get out of|ゲラウロ|ゲット アウト オブ
here|ヒア|ヒア

Format: phrase|casual|formal"""

print(f"テスト: {text}")
print(f"プロンプト:\n{prompt}")
print("-" * 50)

try:
    response = client.chat.completions.create(
        model="gpt-5-nano",
        messages=[
            {
                "role": "system",
                "content": "Convert English pronunciation to katakana sounds, not meaning."
            },
            {
                "role": "user", 
                "content": prompt
            }
        ]
    )
    
    result = response.choices[0].message.content
    print(f"結果:\n{result}")
    
except Exception as e:
    print(f"エラー: {str(e)}")