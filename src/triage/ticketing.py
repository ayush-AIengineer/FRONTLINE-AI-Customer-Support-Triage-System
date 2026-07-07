"""
FRONTLINE — Ticketing Service
Handles automatic ticket creation for critical issues.
"""

import json
import logging
import os
from typing import Dict, Optional
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

# Ticketing configuration
TICKETING_CONFIG_FILE = Path(__file__).parent.parent.parent / "config" / "ticketing.json"


def load_ticketing_config() -> Dict:
    """Load ticketing configuration from file."""
    try:
        if TICKETING_CONFIG_FILE.exists():
            with open(TICKETING_CONFIG_FILE, "r") as f:
                return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(f"Could not load ticketing config: {e}")
    return {
        "enabled": False,
        "provider": "none",  # options: none, zendesk, jira, webhook
        "webhook_url": "",
        "api_token": "",
        "email": "",
        "subdomain": "",
        "project_key": "",
        "default_priority": "high",
        "default_assignee": "",
        "create_ticket_for_needs_human": True,
        "custom_fields": {}
    }


def save_ticketing_config(config: Dict):
    """Save ticketing configuration to file."""
    try:
        TICKETING_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(TICKETING_CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)
    except OSError as e:
        logger.warning(f"Could not save ticketing config: {e}")


def create_ticket_for_triage_result(triage_result: Dict, message_text: str) -> Optional[Dict]:
    """
    Create a ticket in the configured ticketing system for a triage result.

    Args:
        triage_result: The triage decision result
        message_text: The original message text

    Returns:
        Dictionary with ticket information if created, None if not created or failed
    """
    config = load_ticketing_config()

    # Check if ticketing is enabled and if this case warrants a ticket
    if not config.get("enabled", False):
        return None

    # Only create tickets for P0/P1 issues or when specifically configured
    priority = triage_result.get("priority", "P3")
    needs_human = triage_result.get("needs_human", False)

    # Create ticket for P0, P1, or when needs_human is True (depending on config)
    should_create_ticket = False
    if priority in ["P0", "P1"]:
        should_create_ticket = True
    elif needs_human and config.get("create_ticket_for_needs_human", True):
        should_create_ticket = True

    if not should_create_ticket:
        return None

    # Create ticket based on provider
    provider = config.get("provider", "none")

    if provider == "zendesk":
        return _create_zendesk_ticket(triage_result, message_text, config)
    elif provider == "jira":
        return _create_jira_ticket(triage_result, message_text, config)
    elif provider == "webhook":
        return _create_webhook_ticket(triage_result, message_text, config)
    else:
        logger.warning(f"Unknown or unsupported ticketing provider: {provider}")
        return None


def _create_zendesk_ticket(triage_result: Dict, message_text: str, config: Dict) -> Dict:
    """Create a ticket in Zendesk (simulated)."""
    try:
        # In a real implementation, you would make an API call to Zendesk here
        # For this implementation, we'll simulate the ticket creation

        ticket_id = f"zendesk_{int(datetime.now().timestamp())}"
        logger.info(f"Created Zendesk ticket {ticket_id} (simulated)")

        return {
            "ticket_id": ticket_id,
            "provider": "zendesk",
            "url": f"https://{config.get('subdomain', 'example')}.zendesk.com/agent/tickets/{ticket_id}",
            "status": "created",
            "created_at": datetime.now().isoformat(),
            "details": {
                "title": f"[{triage_result.get('priority', 'P3')}] {triage_result.get('category', 'unknown')}: {triage_result.get('summary', 'No summary')[:100]}",
                "priority": _map_priority_to_zendesk(triage_result.get("priority", "P3")),
                "tags": ["automated", "frontline", f"category_{triage_result.get('category', 'unknown')}"]
            }
        }

    except Exception as e:
        logger.error(f"Failed to create Zendesk ticket: {e}")
        return None


def _create_jira_ticket(triage_result: Dict, message_text: str, config: Dict) -> Dict:
    """Create a ticket in Jira (simulated)."""
    try:
        # In a real implementation, you would make an API call to Jira here
        # For this implementation, we'll simulate the ticket creation

        ticket_id = f"jira-{int(datetime.now().timestamp())}"
        logger.info(f"Created Jira ticket {ticket_id} (simulated)")

        return {
            "ticket_id": ticket_id,
            "provider": "jira",
            "url": f"https://{config.get('subdomain', 'example')}.atlassian.net/browse/{ticket_id}",
            "status": "created",
            "created_at": datetime.now().isoformat(),
            "details": {
                "summary": f"[{triage_result.get('priority', 'P3')}] {triage_result.get('category', 'unknown')}: {triage_result.get('summary', 'No summary')[:100]}",
                "pai priority": _map_priority_to_jira(triage_result.get("priority", "P3")),
                "labels": ["automated", "frontline", f"category_{triage_result.get('category', 'unknown')}"]
            }
        }

    except Exception as e:
        logger.error(f"Failed to create Jira ticket: {e}")
        return None


def _create_webhook_ticket(triage_result: Dict, message_text: str, config: Dict) -> Dict:
    """Send data to a webhook (simulated)."""
    try:
        webhook_url = config.get("webhook_url", "")
        if not webhook_url:
            return None

        # In a real implementation, you would make an HTTP POST request to the webhook
        # For this implementation, we'll simulate the webhook call

        payload = {
            "timestamp": datetime.now().isoformat(),
            "source": "frontline_triage",
            "message": message_text,
            "analysis": triage_result
        }

        # Simulate sending to webhook
        logger.info(f"Sent data to webhook {webhook_url} (simulated)")

        return {
            "webhook_url": webhook_url,
            "provider": "webhook",
            "status": "sent",
            "sent_at": datetime.now().isoformat(),
            "payload": payload
        }

    except Exception as e:
        logger.error(f"Failed to send to webhook: {e}")
        return None


def _map_priority_to_zendesk(priority: str) -> str:
    """Map internal priority to Zendesk priority."""
    mapping = {
        "P0": "urgent",
        "P1": "high",
        "P2": "normal",
        "P3": "low"
    }
    return mapping.get(priority, "normal")


def _map_priority_to_jira(priority: str) -> str:
    """Map internal priority to Jira priority."""
    mapping = {
        "P0": "Highest",
        "P1": "High",
        "P2": "Medium",
        "P3": "Low"
    }
    return mapping.get(priority, "Medium")


# For testing purposes
if __name__ == "__main__":
    # Test the ticketing system
    print("Testing ticketing system...")

    # Test configuration
    test_config = {
        "enabled": True,
        "provider": "zendesk",
        "subdomain": "testcompany",
        "create_ticket_for_needs_human": True
    }
    save_ticketing_config(test_config)

    print("Testing ticket creation with sample data...")
    # Sample triage result
    sample_triage = {
        "category": "billing",
        "priority": "P0",
        "summary": "Customer reports duplicate charge",
        "suggested_action": "Refund duplicate charge",
        "needs_human": True,
        "confidence": 0.95,
        "detected_language": "en",
        "flags": []
    }

    sample_message = "I was charged twice for the same item. Please refund one of the charges."

    result = create_ticket_for_triage_result(sample_triage, sample_message)
    print(f"Ticket creation result: {result}")

    # Test with jira
    test_config["provider"] = "jira"
    save_ticketing_config(test_config)
    result = create_ticket_for_triage_result(sample_triage, sample_message)
    print(f"Jira ticket creation result: {result}")

    # Test with webhook
    test_config["provider"] = "webhook"
    test_config["webhook_url"] = "https://example.com/webhook"
    save_ticketing_config(test_config)
    result = create_ticket_for_triage_result(sample_triage, sample_message)
    print(f"Webhook notification result: {result}")

    print("Testing completed.")