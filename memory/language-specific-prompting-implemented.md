# Language-Specific Prompting Implementation

## Overview
Implemented language-specific prompting for improved multilingual support as specified in Task 7 of the WORKFLOW_PLAN.md.

## Changes Made

### 1. Enhanced Language Detection (`src/triage/lang_detect.py`)
- Added `detect_language_with_confidence()` function that returns language code and confidence score
- Added `get_language_confidence_scores()` function for getting all detected languages with probabilities
- Added `is_language_supported()` function to check if a language is supported by our system
- Maintained backward compatibility with existing `detect_language()` function

### 2. Language-Specific Prompt Templates (`src/triage/prompts/`)
- Created language-specific prompt files:
  - `en.py`: English system prompt
  - `es.py`: Spanish system prompt  
  - `fr.py`: French system prompt
  - `zh.py`: Chinese system prompt
- Updated `__init__.py` to map language codes to appropriate prompts with English fallback

### 3. Integration with LLM Pipeline (`src/triage/engine.py`)
- Modified `get_llm_response()` to detect language and route to appropriate system prompt
- Modified `get_llm_response_stream()` to support streaming with language detection
- Language detection happens before LLM call to ensure correct prompt selection

### 4. Language-Specific Confidence Thresholds (`src/triage/engine.py`)
- Added `get_language_confidence_threshold()` function for language-configurable confidence thresholds
- Created language-specific config files (e.g., `config/confidence_es.json` for Spanish)
- Modified `validate_triage()` to use language-specific thresholds instead of global threshold
- Default threshold: 0.6, Spanish threshold: 0.3 (as example)

### 5. Enhanced Output Schema
- Maintained `detected_language` field in triage output (ISO 639-1 code)
- Added `non_english` flag when appropriate (handled in prompt logic)
- Confidence scores now filtered through language-specific thresholds

## Testing
- Added comprehensive tests in `tests/test_multilingual.py`:
  - Language detection accuracy for EN, ES, FR, ZH
  - Fallback to English for unsupported/undetectable languages
  - Prompt routing based on detected language
  - Configuration of language-specific thresholds

## Usage
The system automatically:
1. Detects the language of incoming messages
2. Selects the appropriate language-specific system prompt
3. Processes the message with that prompt
4. Applies language-specific confidence thresholds for human escalation decisions
5. Returns the detected language in the response for agent reference

## Supported Languages
- English (en) - default
- Spanish (es) 
- French (fr)
- Chinese (zh, zh-cn, zh-tw)

## Configuration
Language-specific confidence thresholds can be configured by creating files in `config/`:
- `confidence_<language_code>.json` with format: `{"threshold": <value between 0.0 and 1.0>}`

Example: `config/confidence_es.json` contains `{"threshold": 0.3}` for Spanish.