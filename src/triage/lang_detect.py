import logging
from langdetect import detect, detect_langs, LangDetectException

logger = logging.getLogger(__name__)

def detect_language(text: str) -> str:
    """
    Detects the language of the given text using langdetect.
    Returns the ISO 639-1 language code (e.g., 'en', 'es', 'fr', 'zh-cn').
    Falls back to 'en' on failure.
    """
    if not text or not text.strip():
        return "en"
        
    try:
        lang = detect(text)
        return lang
    except LangDetectException as e:
        logger.warning(f"Language detection failed, falling back to 'en': {e}")
        return "en"
