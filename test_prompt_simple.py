#!/usr/bin/env python3
"""
GPT-5-nano プロンプト実験スクリプト（非対話式）
英語音写カタカナ変換プロンプトを最適化する
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
    print(f"\n{'='*80}")
    print(f"テストテキスト: {test_text}")
    print(f"{'='*80}")
    print(f"プロンプト:\n{prompt}")
    print(f"{'-'*80}")
    
    try:
        response = client.chat.completions.create(
            model="gpt-5-nano",
            messages=[
                {
                    "role": "system",
                    "content": "You are a Japanese pronunciation expert who converts English sounds to katakana. Convert pronunciation, NOT meaning."
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
    "an apple", 
    "hello world"
]

# 改良されたプロンプトパターン
prompts = [
    # パターン1: 音写を明示
    """Convert English SOUNDS to katakana pronunciation (NOT translation):
"{text}"

Break into natural speech phrases, return format:
phrase|casual|formal""",
    
    # パターン2: 例付き音写
    """Convert English pronunciation to katakana sounds:
"{text}"

Example: "I'm going to" sounds like → I'm going to|アムガナ|アイム ゴーイング トゥ

Return: phrase|casual|formal""",
    
    # パターン3: 非常にシンプル
    """English sounds to katakana: "{text}"
Format: phrase→casual→formal""",
    
    # パターン4: 発音重視
    """How do English speakers pronounce: "{text}"
Write katakana for each phrase:
phrase|how it sounds casual|formal pronunciation"""
]

if __name__ == "__main__":
    print("GPT-5-nano 英語音写カタカナ変換プロンプト実験")
    
    for i, prompt_template in enumerate(prompts, 1):
        print(f"\n{'#'*100}")
        print(f"プロンプトパターン {i}")
        print(f"{'#'*100}")
        
        for test_text in test_sentences:
            prompt = prompt_template.replace("{text}", test_text)
            result = test_prompt(prompt, test_text)
            
            # 結果の解析
            if result:
                print("解析結果:")
                lines = result.strip().split('\n')
                for line in lines:
                    if '|' in line:
                        parts = line.split('|')
                        print(f"  フレーズ: {parts[0].strip() if len(parts) > 0 else 'N/A'}")
                        print(f"  カジュアル: {parts[1].strip() if len(parts) > 1 else 'N/A'}")
                        print(f"  フォーマル: {parts[2].strip() if len(parts) > 2 else 'N/A'}")
                    elif '→' in line:
                        parts = line.split('→')
                        print(f"  フレーズ: {parts[0].strip() if len(parts) > 0 else 'N/A'}")
                        print(f"  カジュアル: {parts[1].strip() if len(parts) > 1 else 'N/A'}")
                        print(f"  フォーマル: {parts[2].strip() if len(parts) > 2 else 'N/A'}")
                    else:
                        print(f"  生出力: {line}")
                        
    print(f"\n{'#'*100}")
    print("実験完了")
    print(f"{'#'*100}")