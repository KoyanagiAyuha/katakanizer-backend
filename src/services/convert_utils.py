import logging

logger = logging.getLogger(__name__)


def fill_missing_conversions(original_text: str, word_mappings: list[dict]) -> list[dict]:
    """GPT変換結果をそのまま返す"""
    if not word_mappings:
        logger.warning("No GPT mappings provided")
        return []
    return word_mappings
