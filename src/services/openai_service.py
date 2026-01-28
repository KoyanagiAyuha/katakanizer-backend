import logging
import re
from concurrent.futures import ThreadPoolExecutor

from openai import OpenAI
from pydantic import BaseModel

from ..config import get_settings

logger = logging.getLogger(__name__)

MODEL_NAME = "gpt-5.1"

LANGUAGE_NAMES = {
    "en": "English",
    "ko": "Korean",
    "fr": "French",
    "es": "Spanish",
    "de": "German",
    "it": "Italian",
    "pt": "Portuguese",
    "zh": "Chinese (Mandarin)",
    "ja": "Japanese",
}


class PhraseMapping(BaseModel):
    """フレーズのカタカナ変換結果"""

    phrase: str
    casual: str
    formal: str


class ConversionResponse(BaseModel):
    """カタカナ変換のレスポンス"""

    phrases: list[PhraseMapping]


class KatakanaConverter:
    def __init__(self):
        self._client: OpenAI | None = None
        self._initialized = False

    @property
    def client(self) -> OpenAI | None:
        """遅延初期化でクライアントを取得"""
        if not self._initialized:
            self._initialized = True
            settings = get_settings()
            api_key = settings.openai_api_key

            if api_key and api_key != "your-openai-api-key":
                try:
                    self._client = OpenAI(api_key=api_key)
                    logger.debug("OpenAI client initialized")
                except Exception as e:
                    logger.error(f"Failed to initialize OpenAI client: {e}")
                    self._client = None
            else:
                logger.warning("OpenAI API key not found")
        return self._client

    def convert_text_complete(self, text: str, language: str = "en") -> dict | None:
        if not self.client:
            logger.warning("OpenAI client is not initialized")
            return None

        if len(text) > 1000:
            return self._convert_long_text(text, language)

        return self._convert_short_text(text, language)

    def _convert_long_text(self, text: str, language: str = "en") -> dict | None:
        sentences = []
        for line in text.split("\n"):
            line = line.strip()
            if line:
                line_sentences = re.split(r"([.!?]+\s*)", line)
                for i in range(0, len(line_sentences), 2):
                    sentence_part = line_sentences[i].strip()
                    if sentence_part:
                        current_sentence = sentence_part
                        if i + 1 < len(line_sentences):
                            current_sentence += line_sentences[i + 1]
                        sentences.append(current_sentence.strip())

        if not sentences:
            sentences = [text[:1000]]

        chunks = []
        current_chunk = ""

        for sentence in sentences:
            test_chunk = current_chunk + (" " if current_chunk else "") + sentence

            if len(test_chunk) <= 1000:
                current_chunk = test_chunk
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = sentence

        if current_chunk:
            chunks.append(current_chunk)

        if not chunks:
            chunks = [text[:1000]]

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
                "formal_katakana": "".join([item["formal"] for item in all_phrase_mappings]),
            }

        return None

    def _convert_short_text(self, text: str, language: str = "en") -> dict | None:
        logger.debug(f"Processing text with length: {len(text)}, language: {language}")
        try:
            lang_name = LANGUAGE_NAMES.get(language, "the given language")

            prompt = f"""Convert {lang_name} SOUNDS to katakana (NOT translation):
"{text}"

IMPORTANT: Convert ALL parts of the text, including repeated phrases. Do NOT skip duplicates.
Break into natural speech phrases.

Example output:
- phrase: "I'm going to", casual: "アムゴナ", formal: "アイム ゴーイング トゥ"
- phrase: "get out of", casual: "ゲラウラブ", formal: "ゲット アウト オブ"

Cover the ENTIRE text from beginning to end. Include repeated phrases each time they appear."""

            result = self._make_openai_request(prompt)

            if result and result.phrases:
                phrase_mappings = [
                    {
                        "line": p.phrase,
                        "casual": p.casual,
                        "formal": p.formal,
                    }
                    for p in result.phrases
                ]
                return {
                    "phrase_mappings": phrase_mappings,
                    "casual_katakana": "".join([p.casual for p in result.phrases]),
                    "formal_katakana": "".join([p.formal for p in result.phrases]),
                }

            return None

        except Exception as e:
            logger.error(f"OpenAI conversion failed for '{text}': {e}")
            return None

    def _make_openai_request(self, prompt: str) -> ConversionResponse | None:
        if not self.client:
            logger.error("OpenAI client is not initialized")
            return None

        try:
            logger.debug(f"Calling {MODEL_NAME} API with prompt length: {len(prompt)} characters")

            response = self.client.responses.parse(
                model=MODEL_NAME,
                input=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                text_format=ConversionResponse,
            )

            result = response.output_parsed
            logger.debug(f"{MODEL_NAME} API response received: {len(result.phrases) if result else 0} phrases")
            return result

        except Exception as e:
            error_type = type(e).__name__
            error_msg = str(e)
            logger.error(f"{MODEL_NAME} request failed - Error type: {error_type}")
            logger.error(f"{MODEL_NAME} request failed - Error message: {error_msg}")
            return None


converter = KatakanaConverter()
