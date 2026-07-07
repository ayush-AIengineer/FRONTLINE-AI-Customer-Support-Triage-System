import pytest
from unittest.mock import patch
from triage.lang_detect import detect_language
from triage.prompts import get_system_prompt

def test_detect_language_english():
    text = "Hello, my account is blocked. I need help."
    assert detect_language(text) == "en"

def test_detect_language_spanish():
    text = "Hola, mi cuenta está bloqueada y necesito ayuda."
    assert detect_language(text) == "es"

def test_detect_language_french():
    text = "Bonjour, mon compte est bloqué. J'ai besoin d'aide."
    assert detect_language(text) == "fr"

def test_detect_language_chinese():
    text = "你好，我的账户被封锁了。我需要帮助。"
    # langdetect might return 'zh-cn' or 'zh'
    assert detect_language(text).startswith("zh")

def test_detect_language_fallback():
    # empty or invalid text should fallback to english
    assert detect_language("") == "en"
    assert detect_language("   ") == "en"

def test_get_system_prompt_routing():
    # Should route to specific prompts
    es_prompt = get_system_prompt("es")
    assert "Eres una IA" in es_prompt

    fr_prompt = get_system_prompt("fr")
    assert "Vous êtes une IA" in fr_prompt

    zh_prompt = get_system_prompt("zh-cn")
    assert "你是一家软件公司的" in zh_prompt

    en_prompt = get_system_prompt("en")
    assert "You are a customer support triage AI" in en_prompt

    # Fallback routing
    unknown_prompt = get_system_prompt("it") # italian not supported
    assert "You are a customer support triage AI" in unknown_prompt
