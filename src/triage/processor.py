"""
FRONTLINE — Batch Processor with Feedback and Ticketing Support
Reads messages.json, triages each one, saves results to outputs/.
Supports collecting human feedback for continuous learning and automatic ticket creation.
"""

import json
import logging
import os
import time
import asyncio
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List, Generator, Union

from .engine import get_llm_response, validate_triage, add_feedback_entry, get_llm_response_stream
from .ticketing import create_ticket_for_triage_result, load_ticketing_config

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

DATA_PATH = Path(__file__).parent.parent.parent / "data" / "messages.json"
OUTPUT_DIR = Path(__file__).parent.parent.parent / "outputs"


def process_all(
    messages_path: Path = DATA_PATH,
    output_dir: Path = OUTPUT_DIR,
    provider: str = None,
    model: str = None,
    delay_s: float = 0.5,
    create_tickets: bool = True,
    stream: bool = False
) -> Union[list[dict], Generator[dict, None, None]]:
    """
    Processes all messages and returns list of triage results.
    Also saves results to a timestamped JSON file.
    Optionally creates tickets for critical issues.

    Args:
        messages_path: Path to messages JSON file
        output_dir: Directory to save results
        provider: LLM provider (openai or gemini)
        model: Specific model name
        delay_s: Delay between API calls
        create_tickets: Whether to create tickets for critical issues
        stream: Whether to yield results as they're processed (streaming mode)

    Returns:
        If stream=False: List of all results
        If stream=True: Generator yielding results as they're processed
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(messages_path, "r", encoding="utf-8") as f:
        messages = json.load(f)

    results = []
    total = len(messages)
    tickets_created = 0

    logger.info(f"Processing {total} messages...")

    for i, msg in enumerate(messages, 1):
        msg_id = msg["id"]
        text = msg["text"]
        logger.info(f"[{i}/{total}] Triaging {msg_id}...")

        if stream:
            # Streaming mode - yield results as they come
            result_gen = process_single_stream(
                text,
                provider=provider,
                model=model,
                create_ticket=create_tickets
            )

            # Process the stream and yield meaningful results
            for chunk in result_gen:
                if chunk["type"] in ["result", "complete"]:
                    # This is a final result
                    result_data = chunk.get("result", {})
                    if not result_data and chunk["type"] == "complete":
                        # Extract result from complete chunk
                        result_data = {k: v for k, v in chunk.items()
                                     if k not in ["type", "original_text"]}

                    # Add message ID and original text
                    result_data["id"] = msg_id
                    result_data["original_text"] = text

                    results.append(result_data)  # Collect for final return if needed

                    # Create ticket if warranted and not already done
                    if create_tickets and "ticket_created" not in result_data:
                        validated_result = {k: v for k, v in result_data.items()
                                          if k not in ["id", "original_text"]}
                        ticket_result = create_ticket_for_triage_result(validated_result, text)
                        if ticket_result:
                            tickets_created += 1
                            result_data["ticket_created"] = ticket_result
                            logger.info(f"Created ticket for message {msg_id}: {ticket_result.get('ticket_id')}")

                    yield result_data
                    break  # Only yield the final result for each message
                elif chunk["type"] == "chunk":
                    # Yield chunk for real-time updates
                    yield {
                        "type": "chunk",
                        "message_id": msg_id,
                        "content": chunk["content"],
                        "accumulated": chunk["accumulated"]
                    }
                elif chunk["type"] == "error":
                    # Yield error
                    yield {
                        "type": "error",
                        "message_id": msg_id,
                        "error": chunk["error"]
                    }
        else:
            # Standard processing
            raw = get_llm_response(text, provider=provider, model=model)
            validated = validate_triage(raw)

            result = {
                "id": msg_id,
                "original_text": text,
                **validated,
            }
            results.append(result)

            # Create ticket if enabled and warranted
            if create_tickets:
                ticket_result = create_ticket_for_triage_result(validated, text)
                if ticket_result:
                    tickets_created += 1
                    # Add ticket info to result for tracking
                    result["ticket_created"] = ticket_result
                    logger.info(f"Created ticket for message {msg_id}: {ticket_result.get('ticket_id')}")

        # Polite delay to avoid rate limits (skip for streaming as it's handled differently)
        if not stream and i < total:
            time.sleep(delay_s)

    if not stream:
        # Save results only in non-streaming mode
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = output_dir / f"triage_results_{timestamp}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        logger.info(f"Results saved to: {out_path}")
        logger.info(f"Created {tickets_created} tickets during processing")
        return results
    # In streaming mode, we don't return anything here as results are yielded


def process_single(text: str, provider: str = None, model: str = None, create_ticket: bool = True, conversation_history: Optional[List[Dict]] = None) -> dict:
    """Triage a single message string.

    Args:
        text: The message text to triage
        provider: LLM provider (openai or gemini)
        model: Specific model name
        create_ticket: Whether to create a ticket for this message if warranted
        conversation_history: Optional list of previous messages in the conversation (each a dict with at least 'text' key)

    Returns:
        Dict containing the triage result
    """
    # Pass conversation history to the LLM call
    raw = get_llm_response(text, provider=provider, model=model, conversation_history=conversation_history)
    validated = validate_triage(raw)

    result = {
        "original_text": text,
        **validated,
    }

    # Create ticket if enabled and warranted
    if create_ticket:
        ticket_result = create_ticket_for_triage_result(validated, text)
        if ticket_result:
            result["ticket_created"] = ticket_result
            logger.info(f"Created ticket for single message: {ticket_result.get('ticket_id')}")

    return result


def process_single_stream(text: str, provider: str = None, model: str = None, create_ticket: bool = True, conversation_history: Optional[List[Dict]] = None) -> Generator[dict, None, None]:
    """
    Triage a single message string with streaming response.

    Args:
        text: The message text to triage
        provider: LLM provider (openai or gemini)
        model: Specific model name
        create_ticket: Whether to create a ticket for this message if warranted
        conversation_history: Optional list of previous messages in the conversation (each a dict with at least 'text' key)

    Yields:
        Dict chunks during processing, then final result
    """
    # Get streaming response
    stream_gen = get_llm_response_stream(text, provider=provider, model=model, conversation_history=conversation_history)

    # Process the stream to accumulate the final result
    accumulated_content = ""
    final_result = None

    for chunk in stream_gen:
        if chunk["type"] == "chunk":
            # Yield the chunk for real-time updates
            yield {
                "type": "chunk",
                "content": chunk["content"],
                "accumulated": chunk["accumulated"],
                "original_text": text
            }
        elif chunk["type"] == "complete":
            # We have the final result
            final_result = chunk["result"]
            yield {
                "type": "result",
                "result": final_result,
                "original_text": text
            }
        elif chunk["type"] == "error":
            # Error occurred
            yield {
                "type": "error",
                "error": chunk["error"],
                "original_text": text
            }
            return

    # If we got a final result, create ticket if needed and yield final result
    if final_result:
        validated_result = final_result

        # Create ticket if enabled and warranted
        if create_ticket:
            ticket_result = create_ticket_for_triage_result(validated_result, text)
            if ticket_result:
                validated_result["ticket_created"] = ticket_result
                logger.info(f"Created ticket for single message (stream): {ticket_result.get('ticket_id')}")

        yield {
            "type": "complete",
            "original_text": text,
            **validated_result
        }


def submit_feedback(
    message_id: str,
    original_text: str,
    original_prediction: dict,
    corrected_decision: dict,
    feedback_source: str = "human_operator"
) -> bool:
    """
    Submit human feedback on a triage decision for continuous learning.

    Args:
        message_id: ID of the message being corrected
        original_text: The original message text
        original_prediction: The AI's original triage decision
        corrected_decision: The human-corrected triage decision
        feedback_source: Who provided the feedback

    Returns:
        True if feedback was successfully recorded, False otherwise
    """
    try:
        success = add_feedback_entry(
            message=original_text,
            original_prediction=original_prediction,
            corrected_decision=corrected_decision,
            feedback_source=feedback_source
        )

        if success:
            logger.info(f"Feedback submitted for message {message_id}")
        else:
            logger.error(f"Failed to submit feedback for message {message_id}")

        return success
    except Exception as e:
        logger.error(f"Error submitting feedback for message {message_id}: {e}")
        return False


def get_triage_with_feedback_option(
    text: str,
    message_id: str = None,
    provider: str = None,
    model: str = None
) -> dict:
    """
    Get triage result for a single message, designed to be used in feedback loops.
    Returns the triage result along with metadata needed for feedback submission.

    Args:
        text: The message text to triage
        message_id: Optional ID for the message
        provider: LLM provider to use
        model: Specific model to use

    Returns:
        Dictionary containing triage result and feedback metadata
    """
    # Get the triage result
    raw_result = get_llm_response(text, provider=provider, model=model)
    validated_result = validate_triage(raw_result)

    # Prepare feedback metadata
    feedback_metadata = {
        "message_id": message_id or f"temp_{int(time.time())}",
        "original_text": text,
        "timestamp": time.time(),
        "ai_prediction": validated_result,
        "provider": provider or os.getenv("MODEL_PROVIDER", "openai"),
        "model": model or os.getenv("MODEL_NAME", "gpt-4o-mini")
    }

    # Combine result with feedback metadata
    result = {
        **validated_result,
        "_feedback_metadata": feedback_metadata
    }

    return result


def process_batch_with_feedback_collection(
    messages_path: Path = DATA_PATH,
    output_dir: Path = OUTPUT_DIR,
    provider: str = None,
    model: str = None,
    delay_s: float = 0.5,
    collect_feedback: bool = False,
    create_tickets: bool = True
) -> tuple[list[dict], list[dict]]:
    """
    Process all messages and optionally prepare for feedback collection.

    Args:
        messages_path: Path to messages JSON file
        output_dir: Directory to save results
        provider: LLM provider
        model: Specific model
        delay_s: Delay between API calls
        collect_feedback: If True, returns feedback-eligible results instead of saving
        create_tickets: Whether to create tickets during processing

    Returns:
        Tuple of (results, feedback_eligible_items)
        If collect_feedback is False, feedback_eligible_items will be empty
        If collect_feedback is True, results will be empty and feedback_eligible_items
        will contain items ready for feedback submission
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(messages_path, "r", encoding="utf-8") as f:
        messages = json.load(f)

    results = []
    feedback_eligible = []
    total = len(messages)
    tickets_created = 0

    logger.info(f"Processing {total} messages{'with feedback preparation' if collect_feedback else ''}...")

    for i, msg in enumerate(messages, 1):
        msg_id = msg["id"]
        text = msg["text"]
        logger.info(f"[{i}/{total}] Triaging {msg_id}...")

        raw = get_llm_response(text, provider=provider, model=model)
        validated = validate_triage(raw)

        result = {
            "id": msg_id,
            "original_text": text,
            **validated,
        }

        # Create ticket if enabled and warranted
        if create_tickets and not collect_feedback:
            ticket_result = create_ticket_for_triage_result(validated, text)
            if ticket_result:
                tickets_created += 1
                # Add ticket info to result for tracking
                result["ticket_created"] = ticket_result

        if collect_feedback:
            # Prepare item for feedback collection
            feedback_item = {
                "message_id": msg_id,
                "original_text": text,
                "ai_prediction": validated,
                "timestamp": time.time()
            }
            feedback_eligible.append(feedback_item)
        else:
            # Normal processing - save result
            results.append(result)

        # Polite delay to avoid rate limits
        if i < total:
            time.sleep(delay_s)

    if collect_feedback:
        logger.info(f"Prepared {len(feedback_eligible)} items for feedback collection")
        return [], feedback_eligible
    else:
        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = output_dir / f"triage_results_{timestamp}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        logger.info(f"Results saved to: {out_path}")
        logger.info(f"Created {tickets_created} tickets during processing")
        return results, []


async def _process_single_async(
    text: str,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    create_ticket: bool = True,
    use_few_shot: bool = True,
    conversation_history: Optional[List[Dict]] = None,
) -> Dict[str, Any]:
    """
    Process a single message asynchronously (offloads blocking LLM call to thread pool).

    Returns:
        Dict containing the triage result with added 'id' and 'original_text' fields
        (to be added by caller).
    """
    loop = asyncio.get_event_loop()
    # Run the blocking LLM call in a thread pool
    raw = await loop.run_in_executor(
        None, get_llm_response, text, provider, model, use_few_shot, conversation_history
    )
    validated = validate_triage(raw)

    result = {
        "original_text": text,
        **validated,
    }

    if create_ticket:
        ticket_result = create_ticket_for_triage_result(validated, text)
        if ticket_result:
            result["ticket_created"] = ticket_result
            logger.info(f"Created ticket for single message (async): {ticket_result.get('ticket_id')}")

    return result


async def process_all_async(
    messages_path: Path = DATA_PATH,
    output_dir: Path = OUTPUT_DIR,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    delay_s: float = 0.5,
    create_tickets: bool = True,
    max_concurrency: int = 10,
) -> List[Dict[str, Any]]:
    """
    Processes all messages asynchronously with controlled concurrency.
    Also saves results to a timestamped JSON file.
    Optionally creates tickets for critical issues.

    Args:
        messages_path: Path to messages JSON file
        output_dir: Directory to save results
        provider: LLM provider (openai or gemini)
        model: Specific model name
        delay_s: Delay between API calls (not used in async mode, kept for compatibility)
        create_tickets: Whether to create tickets for critical issues
        max_concurrency: Maximum number of concurrent LLM requests

    Returns:
        List of all results
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(messages_path, "r", encoding="utf-8") as f:
        messages = json.load(f)

    total = len(messages)
    logger.info(f"Processing {total} messages asynchronously with max concurrency {max_concurrency}...")

    semaphore = asyncio.Semaphore(max_concurrency)

    async def process_with_semaphore(msg: Dict) -> Dict[str, Any]:
        async with semaphore:
            msg_id = msg["id"]
            text = msg["text"]
            logger.debug(f"[{msg_id}] Starting async processing...")

            # Process the single message asynchronously
            result = await _process_single_async(
                text,
                provider=provider,
                model=model,
                create_ticket=create_tickets,
            )

            # Add message ID and original text
            result["id"] = msg_id
            result["original_text"] = text

            logger.debug(f"[{msg_id}] Completed async processing.")
            return result

    # Create tasks for all messages
    tasks = [process_with_semaphore(msg) for msg in messages]

    # Wait for all tasks to complete
    results = await asyncio.gather(*tasks, return_exceptions=False)

    # Count tickets created
    tickets_created = sum(1 for r in results if r.get("ticket_created") is not None)
    logger.info(f"Created {tickets_created} tickets during async processing")

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = output_dir / f"triage_results_{timestamp}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    logger.info(f"Results saved to: {out_path}")
    return results


if __name__ == "__main__":
    results = process_all()
    print(f"\nDone! Processed {len(results)} messages.")