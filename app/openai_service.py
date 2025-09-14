import os
import logging
import json
import re
import asyncio
from concurrent.futures import ThreadPoolExecutor
from openai import OpenAI
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

class KatakanaConverter:
    def __init__(self):
        self.client = None
        api_key = os.getenv("OPENAI_API_KEY")
        organization = os.getenv("ORGANIZATION")
        
        if api_key and api_key != "your_openai_api_key_here":
            try:
                self.client = OpenAI(
                    api_key=api_key,
                    organization=organization
                )
                logger.debug(f"OpenAI client initialized")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {str(e)}")
                self.client = None
        else:
            logger.warning("OpenAI API key not found")
    
    def convert_text_complete(self, text: str, language: str = "en") -> Optional[Dict]:
        """
        テキストをカタカナに変換（GPT-5 Responses API使用）

        Args:
            text: 変換するテキスト
            language: 言語コード (en, ko, fr, es, etc.)

        Returns:
            変換結果の辞書（phrase_mappings, casual_katakana, formal_katakana）
        """
        if not self.client:
            logger.warning("OpenAI client is not initialized - returning None immediately")
            return None
        
        # 長いテキストの場合は分割処理
        if len(text) > 1000:  # 1000文字を超える場合は分割
            return self._convert_long_text(text, language)
        
        # 短いテキストの場合は直接処理
        return self._convert_short_text(text, language)
    
    def _convert_long_text(self, text: str, language: str = "en") -> Optional[Dict]:
        """
        長いテキストを分割して並列処理で変換
        """
        # 改行を保持しながら文単位で分割
        sentences = []
        for line in text.split('\n'):
            line = line.strip()
            if line:
                # 文単位で分割（ピリオド、感嘆符、疑問符で分割）
                line_sentences = re.split(r'([.!?]+\s*)', line)
                current_sentence = ""
                
                for i in range(0, len(line_sentences), 2):
                    sentence_part = line_sentences[i].strip()
                    if sentence_part:
                        current_sentence = sentence_part
                        if i + 1 < len(line_sentences):
                            current_sentence += line_sentences[i + 1]
                        sentences.append(current_sentence.strip())
        
        if not sentences:
            sentences = [text[:1000]]
        
        # 1000文字以内のチャンクを作成
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            test_chunk = current_chunk + (" " if current_chunk else "") + sentence
            
            if len(test_chunk) <= 1000:
                current_chunk = test_chunk
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                # 文が長すぎる場合はそのまま追加（_convert_short_textで処理）
                current_chunk = sentence
        
        if current_chunk:
            chunks.append(current_chunk)
        
        if not chunks:
            chunks = [text[:1000]]
        
        # 並列処理でチャンクを変換
        all_phrase_mappings = []
        
        with ThreadPoolExecutor(max_workers=3) as executor:
            future_to_chunk = {
                executor.submit(self._convert_short_text, chunk, language): chunk 
                for chunk in chunks
            }
            
            for future in future_to_chunk:
                chunk = future_to_chunk[future]
                try:
                    result = future.result()
                    if result and result.get("phrase_mappings"):
                        all_phrase_mappings.extend(result["phrase_mappings"])
                    else:
                        logger.warning(f"Failed to convert chunk: {chunk[:50]}...")
                except Exception as exc:
                    logger.error(f"Chunk conversion generated exception: {exc}")
        
        if all_phrase_mappings:
            return {
                "phrase_mappings": all_phrase_mappings,
                "casual_katakana": "".join([item["casual"] for item in all_phrase_mappings]),
                "formal_katakana": "".join([item["formal"] for item in all_phrase_mappings])
            }
        
        return None
    
    def _convert_short_text(self, text: str, language: str = "en") -> Optional[Dict]:
        """
        短いテキストの変換処理
        """
        logger.debug(f"Processing text with length: {len(text)}, language: {language}")
        try:
            # Language-specific instructions
            language_instructions = {
                "en": "English",
                "ko": "Korean", 
                "fr": "French",
                "es": "Spanish",
                "de": "German",
                "it": "Italian",
                "pt": "Portuguese",
                "zh": "Chinese (Mandarin)",
                "ja": "Japanese"
            }
            
            lang_name = language_instructions.get(language, "the given language")
            
            prompt = f"""Convert {lang_name} SOUNDS to katakana (NOT translation):
"{text}"

IMPORTANT: Convert ALL parts of the text, including repeated phrases. Do NOT skip duplicates.
Break into natural speech phrases and return JSON format:

Example:
{{
  "phrases": [
    {{"phrase": "I'm going to", "casual": "アムゴナ", "formal": "アイム ゴーイング トゥ"}},
    {{"phrase": "get out of", "casual": "ゲラウラブ", "formal": "ゲット アウト オブ"}},
    {{"phrase": "here", "casual": "ヒア", "formal": "ヒア"}},
    {{"phrase": "I'm going to", "casual": "アムゴナ", "formal": "アイム ゴーイング トゥ"}}
  ]
}}

Cover the ENTIRE text from beginning to end. Include repeated phrases each time they appear.

Return ONLY valid JSON, no explanations."""

            response = self._make_openai_request(prompt)
            
            if response:
                # Parse JSON response
                try:
                    # GPTが余計なマークダウン記号を付ける場合があるので正規表現で除去
                    clean_response = response.strip()
                    
                    # ```json または ```JSON または ``` で始まり ``` で終わるパターンを抽出
                    json_pattern = r'```(?:json|JSON)?\s*(.*?)\s*```'
                    match = re.search(json_pattern, clean_response, re.DOTALL | re.IGNORECASE)
                    
                    if match:
                        clean_response = match.group(1).strip()
                    else:
                        # マークダウンブロックが見つからない場合はそのまま使用
                        clean_response = clean_response.strip()
                    
                    data = json.loads(clean_response)
                    phrases = data.get("phrases", [])
                    
                    result = []
                    for phrase_data in phrases:
                        phrase = phrase_data.get("phrase", "").strip()
                        casual = phrase_data.get("casual", "").strip()
                        formal = phrase_data.get("formal", "").strip()
                        
                        if phrase and casual and formal:
                            result.append({
                                "line": phrase,
                                "casual": casual,
                                "formal": formal
                            })
                    
                    if result:
                        return {
                            "phrase_mappings": result,
                            "casual_katakana": "".join([item["casual"] for item in result]),
                            "formal_katakana": "".join([item["formal"] for item in result])
                        }
                        
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse JSON response: {e}")
                    logger.error(f"Raw response was: '{response}'")
                except Exception as e:
                    logger.error(f"Failed to process response: {e}")
                    logger.error(f"Raw response was: '{response}'")
            
            return None
            
        except Exception as e:
            logger.error(f"OpenAI conversion failed for '{text}': {str(e)}")
            return None
    
    def _make_openai_request(self, prompt: str) -> Optional[str]:
        """GPT-5 Responses APIへのリクエスト"""
        if not self.client:
            logger.error("OpenAI client is not initialized")
            return None

        # Use GPT-5 with Responses API for best performance
        model_name = "gpt-5"

        try:
            logger.debug(f"Calling {model_name} API with prompt length: {len(prompt)} characters")

            # Use Responses API for GPT-5
            response = self.client.responses.create(
                model=model_name,
                input=prompt,
                reasoning={"effort": "low"},  # Fast response for katakana conversion
                text={"verbosity": "low"}     # Concise output
            )

            content = response.output_text
            logger.debug(f"{model_name} API response received: {len(content or '')} characters")
            return content

        except Exception as e:
            error_type = type(e).__name__
            error_msg = str(e)
            logger.error(f"gpt-5 request failed - Error type: {error_type}")
            logger.error(f"gpt-5 request failed - Error message: {error_msg}")
            logger.error(f"Full error details: {repr(e)}")
            
            # エラーメッセージを確認してAPIの問題を特定
            if "api" in error_msg.lower() or "auth" in error_msg.lower():
                logger.error("Authentication/API key issue detected")
            elif "organization" in error_msg.lower():
                logger.error("Organization configuration issue detected")
            
            return None

# Global converter instance
converter = KatakanaConverter()