import json
import time
import logging
import os
from typing import Optional, List, Dict, Any
from pathlib import Path
from dotenv import load_dotenv

from triage.lang_detect import detect_language
from triage.prompts import get_system_prompt

load_dotenv()
logger = logging.getLogger(__name__)

# ─── Configuration ────────────────────────────────────────────────────────────

CONFIG_DIR = Path(__file__).parent.parent.parent / "config"
FEEDBACK_DIR = Path(__file__).parent.parent.parent / "data"
FEEDBACK_FILE = FEEDBACK_DIR / "feedback.json"

def load_confidence_threshold() -> float:
    try:
        conf_file = CONFIG_DIR / "confidence.json"
        if conf_file.exists():
            with open(conf_file, "r") as f:
                return float(json.load(f).get("threshold", 0.6))
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(f"Could not load confidence threshold, using default: {e}")
    return 0.6

def save_confidence_threshold(threshold: float):
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        conf_file = CONFIG_DIR / "confidence.json"
        with open(conf_file, "w") as f:
            json.dump({"threshold": threshold}, f)
    except OSError as e:
        logger.warning(f"Could not save confidence threshold: {e}")


def get_language_confidence_threshold(lang_code: str) -> float:
    """
    Get confidence threshold for a specific language.
    Falls back to the default threshold if language-specific not configured.
    """
    try:
        # Try to load language-specific config
        lang_conf_file = CONFIG_DIR / f"confidence_{lang_code}.json"
        if lang_conf_file.exists():
            with open(lang_conf_file, "r") as f:
                config = json.load(f)
                return float(config.get("threshold", 0.6))
    except (json.JSONDecodeError, OSError):
        pass

    # Fall back to default threshold
    return load_confidence_threshold()

def load_feedback() -> List[Dict]:
    try:
        if FEEDBACK_FILE.exists():
            with open(FEEDBACK_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("feedback_entries", [])
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(f"Could not load feedback: {e}")
    return []

def save_feedback(feedback_entries: List[Dict]):
    try:
        FEEDBACK_DIR.mkdir(parents=True, exist_ok=True)
        data = {
            "feedback_version": "1.0",
            "description": "Storage for human feedback on triage decisions to enable continuous learning",
            "feedback_entries": feedback_entries
        }
        with open(FEEDBACK_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except OSError as e:
        logger.warning(f"Could not save feedback: {e}")

def _fallback_response(error: str) -> Dict:
    """Generate a fallback response when LLM fails."""
    return {
        "category": "unclear",
        "priority": "P2",
        "summary": f"[SYSTEM FALLBACK] Failed to analyze message. Error: {error}",
        "suggested_action": "Manually review this message.",
        "needs_human": True,
        "confidence": 0.0,
        "detected_language": "en",
        "flags": ["system_error"]
    }

def add_feedback_entry(message: str, original_prediction: Dict, corrected_decision: Dict,
                      feedback_source: str = "human_operator") -> bool:
    try:
        feedback_entries = load_feedback()
        entry = {
            "id": f"fb_{len(feedback_entries) + 1}_{int(time.time())}",
            "timestamp": time.time(),
            "message": message,
            "original_prediction": original_prediction,
            "corrected_decision": corrected_decision,
            "feedback_source": feedback_source,
            "used_for_training": False
        }
        feedback_entries.append(entry)
        save_feedback(feedback_entries)
        return True
    except Exception as e:
        logger.error(f"Failed to add feedback entry: {e}")
        return False

def get_relevant_feedback(message: str, category: str = None, limit: int = 3) -> List[Dict]:
    try:
        feedback_entries = load_feedback()
        if category:
            filtered = [
                fb for fb in feedback_entries
                if fb.get("corrected_decision", {}).get("category") == category
            ]
        else:
            filtered = feedback_entries

        sorted_feedback = sorted(
            filtered,
            key=lambda x: x.get("timestamp", 0),
            reverse=True
        )
        return sorted_feedback[:limit]
    except Exception as e:
        logger.warning(f"Error retrieving feedback: {e}")
        return []

def create_few_shot_prompt(message: str, feedback_examples: List[Dict] = None, conversation_history: List[Dict] = None) -> str:
    """Creates the user prompt containing few-shot examples if available."""
    prompt = ""
    if conversation_history:
        prompt += "Conversation history:\n"
        for i, conv_msg in enumerate(conversation_history, 1):
            # We assume each conv_msg is a dict with at least 'text' and maybe 'id'
            # We'll format it as: [Previous message] ...
            prompt += f"{i}. {conv_msg.get('text', '')}\n"
        prompt += "\n"
    if feedback_examples:
        prompt += "Learn from these examples of correct triage decisions:\n\n"
        for i, example in enumerate(feedback_examples, 1):
            msg = example.get("message", "")
            corrected = example.get("corrected_decision", {})
            prompt += f"Example {i}:\nCustomer message:\n---\n{msg}\n---\n"
            prompt += f"Correct triage decision:\n{json.dumps(corrected, indent=2, ensure_ascii=False)}\n\n"

        prompt += "Now, for the following customer message, provide the correct triage decision:\n\n"

    prompt += f"Customer message to triage:\n\n---\n{message}\n---\n\nRespond with ONLY the JSON triage decision. No explanation."
    return prompt

# ─── LLM Caller ───────────────────────────────────────────────────────────────

def get_llm_response(message: str, provider: str = None, model: str = None, use_few_shot: bool = True, conversation_history: Optional[List[Dict]] = None) -> Dict:
    provider = provider or os.getenv("MODEL_PROVIDER", "openai")
    model = model or os.getenv("MODEL_NAME", "gpt-4o-mini")

    # Language routing
    lang_code = detect_language(message)
    sys_prompt = get_system_prompt(lang_code)

    if use_few_shot:
        feedback_examples = get_relevant_feedback(message, limit=3)
        user_prompt = create_few_shot_prompt(message, feedback_examples, conversation_history)
    else:
        user_prompt = create_few_shot_prompt(message, [], conversation_history)

    try:
        if provider == "openai":
            return _call_openai(sys_prompt, user_prompt, model)
        elif provider == "gemini":
            return _call_gemini(sys_prompt, user_prompt, model)
        else:
            raise ValueError(f"Unknown provider: {provider}")
    except Exception as e:
        logger.error(f"LLM call failed: {e}")
        return _fallback_response(str(e))


def get_llm_response_stream(message: str, provider: str = None, model: str = None, use_few_shot: bool = True, conversation_history: Optional[List[Dict]] = None):
    """
    Get a streaming response from the LLM for a triage request.
    Yields chunks of the response as they arrive.

    Args:
        message: The customer message to triage
        provider: LLM provider (openai or gemini)
        model: Specific model name
        use_few_shot: Whether to use few-shot learning from feedback
        conversation_history: Optional list of previous messages in the conversation

    Yields:
        Dict chunks of the streaming response
    """
    provider = provider or os.getenv("MODEL_PROVIDER", "openai")
    model = model or os.getenv("MODEL_NAME", "gpt-4o-mini")

    # Language routing
    lang_code = detect_language(message)
    sys_prompt = get_system_prompt(lang_code)

    # Decide whether to use few-shot learning
    if use_few_shot:
        feedback_examples = get_relevant_feedback(message, limit=3)
        prompt = create_few_shot_prompt(message, feedback_examples, conversation_history)
    else:
        prompt = create_few_shot_prompt(message, [], conversation_history)

    try:
        if provider == "openai":
            yield from _call_openai_stream(sys_prompt, prompt, model)
        elif provider == "gemini":
            yield from _call_gemini_stream(sys_prompt, prompt, model)
        else:
            raise ValueError(f"Unknown provider: {provider}")
    except Exception as e:
        logger.error(f"LLM streaming call failed: {e}")
        yield _fallback_response_stream(str(e))


def _call_openai(system_prompt: str, user_prompt: str, model: str) -> Dict:
    from openai import OpenAI
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.1,
    )
    return json.loads(response.choices[0].message.content)

def _call_gemini(system_prompt: str, user_prompt: str, model: str) -> Dict:
    import google.generativeai as genai
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    full_prompt = system_prompt + "\n\n" + user_prompt
    gemini_model = genai.GenerativeModel(model)
    response = gemini_model.generate_content(
        full_prompt,
        generation_config=genai.GenerationConfig(temperature=0.1)
    )
    raw = response.text.strip()
    if raw.startswith("```json"):
        raw = raw[7:-3]
    return json.loads(raw)


def _call_openai_stream(system_prompt: str, user_prompt: str, model: str):
    """Stream response from OpenAI API."""
    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        stream = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
            stream=True,
        )

        # Collect chunks to form a complete response for validation
        accumulated_content = ""
        for chunk in stream:
            if chunk.choices[0].delta.content is not None:
                content_chunk = chunk.choices[0].delta.content
                accumulated_content += content_chunk
                # Yield each chunk as it arrives
                yield {
                    "type": "chunk",
                    "content": content_chunk,
                    "accumulated": accumulated_content
                }

        # After stream completes, try to parse the accumulated content as JSON
        try:
            result = json.loads(accumulated_content)
            result["_meta"] = {
                "provider": "openai",
                "model": model,
                "streamed": True,
                "completed": True
            }
            yield {
                "type": "complete",
                "result": validate_triage(result)
            }
        except json.JSONDecodeError:
            # If JSON parsing fails, yield a fallback
            yield {
                "type": "error",
                "error": "Failed to parse JSON from streamed response",
                "accumulated": accumulated_content
            }
            yield {
                "type": "complete",
                "result": _fallback_response("JSON parsing failed")
            }

    except Exception as e:
        logger.error(f"OpenAI streaming call failed: {e}")
        yield {
            "type": "error",
            "error": str(e)
        }
        yield {
            "type": "complete",
            "result": _fallback_response(str(e))
        }


def _call_gemini_stream(system_prompt: str, user_prompt: str, model: str):
    """Stream response from Gemini API."""
    try:
        import google.generativeai as genai
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

        full_prompt = system_prompt + "\n\n" + user_prompt

        # Note: Gemini's streaming support may vary; this is a placeholder implementation
        # In practice, you would use Gemini's streaming API if available
        model_instance = genai.GenerativeModel(model)
        response = model_instance.generate_content(
            full_prompt,
            generation_config=genai.GenerationConfig(temperature=0.1),
            stream=True  # This may not be supported by all Gemini versions
        )

        # Collect chunks to form a complete response for validation
        accumulated_content = ""
        for chunk in response:
            if hasattr(chunk, 'text') and chunk.text:
                content_chunk = chunk.text
                accumulated_content += content_chunk
                # Yield each chunk as it arrives
                yield {
                    "type": "chunk",
                    "content": content_chunk,
                    "accumulated": accumulated_content
                }

        # After stream completes, try to parse the accumulated content as JSON
        try:
            result = json.loads(accumulated_content)
            result["_meta"] = {
                "provider": "gemini",
                "model": model,
                "streamed": True,
                "completed": True
            }
            yield {
                "type": "complete",
                "result": validate_triage(result)
            }
        except json.JSONDecodeError:
            # If JSON parsing fails, yield a fallback
            yield {
                "type": "error",
                "error": "Failed to parse JSON from streamed response",
                "accumulated": accumulated_content
            }
            yield {
                "type": "complete",
                "result": _fallback_response("JSON parsing failed")
            }

    except Exception as e:
        logger.error(f"Gemini streaming call failed: {e}")
        # Fallback to non-streaming if streaming fails
        try:
            result = _call_gemini(system_prompt, user_prompt, model)
            yield {
                "type": "complete",
                "result": result
            }
        except Exception as fallback_error:
            logger.error(f"Gemini fallback also failed: {fallback_error}")
            yield {
                "type": "error",
                "error": str(fallback_error)
            }
            yield {
                "type": "complete",
                "result": _fallback_response(str(fallback_error))
            }


def _fallback_response_stream(error: str):
    """Generate a fallback response stream."""
    yield {
        "type": "chunk",
        "content": "",
        "accumulated": ""
    }
    yield {
        "type": "complete",
        "result": _fallback_response(error)
    }


# ─── Validation ───────────────────────────────────────────────────────────────
    return {
        "category": "unclear",
        "priority": "P2",
        "summary": f"[SYSTEM FALLBACK] Failed to analyze message. Error: {error}",
        "suggested_action": "Manually review this message.",
        "needs_human": True,
        "confidence": 0.0,
        "detected_language": "en",
        "flags": ["system_error"]
    }

# ─── Validation ───────────────────────────────────────────────────────────────

VALID_CATEGORIES = [
    "billing", "order_issue", "technical_bug", "technical_outage", 
    "account_support", "security", "feature_request", "general_inquiry", 
    "out_of_scope", "adversarial", "unclear", "positive_feedback", "complaint"
]
VALID_PRIORITIES = ["P0", "P1", "P2", "P3"]

def validate_triage(result: Dict) -> Dict:
    out = {
        "category": result.get("category", "unclear"),
        "priority": result.get("priority", "P3"),
        "summary": result.get("summary", "No summary provided."),
        "suggested_action": result.get("suggested_action", "Review manually."),
        "needs_human": bool(result.get("needs_human", True)),
        "confidence": float(result.get("confidence", 0.0)),
        "detected_language": result.get("detected_language", "en"),
        "flags": result.get("flags", [])
    }
    
    if out["category"] not in VALID_CATEGORIES:
        out["flags"].append("invalid_category_corrected")
        out["category"] = "unclear"

    if out["priority"] not in VALID_PRIORITIES:
        out["flags"].append("invalid_priority_corrected")
        out["priority"] = "P3"

    # Clamp confidence to [0.0, 1.0] range
    if out["confidence"] > 1.0:
        out["confidence"] = 1.0
    elif out["confidence"] < 0.0:
        out["confidence"] = 0.0

    # Language-specific confidence threshold
    lang_code = out["detected_language"]
    threshold = get_language_confidence_threshold(lang_code)
    if out["confidence"] < threshold:
        out["needs_human"] = True
        if "low_confidence" not in out["flags"]:
            out["flags"].append("low_confidence")

    if out["priority"] == "P0":
        out["needs_human"] = True

    if out["category"] == "adversarial":
        out["priority"] = "P0"
        out["needs_human"] = True
        
    # Ensure lists remain lists
    if not isinstance(out["flags"], list):
        out["flags"] = [str(out["flags"])]

    return out