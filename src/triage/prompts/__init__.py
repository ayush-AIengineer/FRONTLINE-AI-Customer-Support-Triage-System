import logging
from .en import SYSTEM_PROMPT as EN_PROMPT
from .es import SYSTEM_PROMPT as ES_PROMPT
from .fr import SYSTEM_PROMPT as FR_PROMPT
from .zh import SYSTEM_PROMPT as ZH_PROMPT

logger = logging.getLogger(__name__)

PROMPTS = {
    "en": EN_PROMPT,
    "es": ES_PROMPT,
    "fr": FR_PROMPT,
    "zh": ZH_PROMPT,
}

def get_system_prompt(lang_code: str = "en") -> str:
    """
    Returns the language-specific system prompt.
    Falls back to English if the language is not explicitly supported.
    """
    base_lang = lang_code.split('-')[0].lower() if lang_code else "en"
    if base_lang in PROMPTS:
        return PROMPTS[base_lang]
    
    logger.debug(f"No specific prompt for language '{lang_code}', falling back to English.")
    return PROMPTS["en"]
