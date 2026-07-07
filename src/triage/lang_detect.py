import logging
from langdetect import detect, detect_langs, LangDetectException

logger = logging.getLogger(__name__)

def detect_language(text: str) -> str:
    """
    Detects the language of the given text using langdetect.
    Returns the ISO 639-1 language code (e.g., 'en', 'es', 'fr', 'zh-cn').
    Falls back to 'en' on failure.
    
    This function maintains backward compatibility with existing code.
    """
    if not text or not text.strip():
        return "en"
        
    try:
        lang = detect(text)
        return lang
    except LangDetectException as e:
        logger.warning(f"Language detection failed, falling back to 'en': {e}")
        return "en"

def detect_language_with_confidence(text: str) -> tuple[str, float]:
    """
    Detects the language of the given text using langdetect with confidence score.
    Returns a tuple of (language_code, confidence) where confidence is 0.0-1.0.
    Falls back to ('en', 0.0) on failure or empty text.
    """
    if not text or not text.strip():
        return "en", 0.0
        
    try:
        # Get list of languages with probabilities
        langs = detect_langs(text)
        if langs:
            # Return the most likely language and its confidence
            top_lang = langs[0]
            return str(top_lang.lang), float(top_lang.prob)
        else:
            return "en", 0.0
    except LangDetectException as e:
        logger.warning(f"Language detection with confidence failed, falling back to ('en', 0.0): {e}")
        return "en", 0.0

def is_language_supported(lang_code: str) -> bool:
    """
    Checks if a language code is supported by our system.
    Currently supports: en, es, fr, zh (and zh-cn, zh-tw variants).
    """
    if not lang_code:
        return False
    
    # Normalize language code (take first 2 chars)
    base_lang = lang_code.lower()[:2]
    
    # Supported languages
    supported = {"en", "es", "fr", "zh"}
    
    return base_lang in supported
