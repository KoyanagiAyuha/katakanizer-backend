#!/usr/bin/env python3
"""
GPT-5-nano プロンプト実験スクリプト
フレーズベースのカタカナ変換プロンプトを最適化する
"""

import os
from dotenv import load_dotenv
from openai import OpenAI

# .envファイルから環境変数を読み込み
load_dotenv()

# OpenAI API設定
api_key = os.getenv("OPENAI_API_KEY")
if not api_key or api_key == "your_openai_api_key_here":
    print("OPENAI_API_KEY環境変数を設定してください")
    exit(1)

client = OpenAI(api_key=api_key)

def test_prompt(prompt, test_text):
    """プロンプトをテストして結果を表示"""
    print(f"\n{'='*60}")
    print(f"テストテキスト: {test_text}")
    print(f"{'='*60}")
    print(f"プロンプト:\n{prompt}")
    print(f"{'-'*60}")
    
    try:
        response = client.chat.completions.create(
            model="gpt-5-nano",
            messages=[
                {
                    "role": "system",
                    "content": "You are a Japanese pronunciation expert. Return ONLY what is requested, no explanations."
                },
                {
                    "role": "user", 
                    "content": prompt
                }
            ]
        )
        
        result = response.choices[0].message.content
        print(f"結果:\n{result}")
        print(f"文字数: {len(result) if result else 0}")
        
        return result
        
    except Exception as e:
        print(f"エラー: {str(e)}")
        return None

# テスト用の文章
test_sentences = [
    "I'm going to get out of here",
    "I am hungry now", 
    "hello world",
    "an apple"
]

# プロンプトパターンを試す
prompts = [
    # パターン1: 最もシンプル
    """Convert to Japanese katakana with phrase groupings:
"{text}"

Return format:
phrase1|casual1|formal1
phrase2|casual2|formal2""",
    
    # パターン2: 例付きシンプル
    """Convert English to katakana phrases:
"{text}"

Example: "I'm going to" → I'm going to|アムガナ|アイム ゴーイング トゥ

Format: phrase|casual|formal""",
    
    # パターン3: JSONなし
    """Break into natural speech phrases with katakana:
"{text}"

Return each line as: original→casual→formal""",
    
    # パターン4: 最小限
    """Katakana phrases for: "{text}"
Format: text→casual→formal"""
]

if __name__ == "__main__":
    print("GPT-5-nano プロンプト実験開始")
    
    for i, prompt_template in enumerate(prompts, 1):
        print(f"\n{'#'*80}")
        print(f"プロンプトパターン {i}")
        print(f"{'#'*80}")
        
        for test_text in test_sentences:
            prompt = prompt_template.replace("{text}", test_text)
            result = test_prompt(prompt, test_text)
            
            # 結果の解析を試す
            if result:
                print("解析結果:")
                lines = result.strip().split('\n')
                for line in lines:
                    if '|' in line:
                        parts = line.split('|')
                        print(f"  フレーズ: {parts[0] if len(parts) > 0 else 'N/A'}")
                        print(f"  カジュアル: {parts[1] if len(parts) > 1 else 'N/A'}")
                        print(f"  フォーマル: {parts[2] if len(parts) > 2 else 'N/A'}")
                    elif '→' in line:
                        parts = line.split('→')
                        print(f"  フレーズ: {parts[0] if len(parts) > 0 else 'N/A'}")
                        print(f"  カジュアル: {parts[1] if len(parts) > 1 else 'N/A'}")
                        print(f"  フォーマル: {parts[2] if len(parts) > 2 else 'N/A'}")
                    else:
                        print(f"  生出力: {line}")
            
            input("次のテストに進むにはEnterを押してください...")