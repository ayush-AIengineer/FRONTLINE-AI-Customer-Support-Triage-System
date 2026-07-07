"""
FRONTLINE — Main Entry Point with Feedback and Ticketing Support
Run from project root.

Usage:
  python main.py                          # Run all messages + show CLI table
  python main.py --message "some text"   # Triage a single message
  python main.py --evaluate              # Also run evaluation against ground truth
  python main.py --web                   # Launch web dashboard
  python main.py --provider gemini       # Use Gemini instead of OpenAI
  python main.py --feedback-collect      # Collect feedback-eligible results
  python main.py --feedback-submit       # Submit feedback via CLI prompts
  python main.py --no-tickets            # Disable automatic ticket creation
  python main.py --ticket-config         # Configure ticketing system
"""

import sys
import argparse
import logging
import json
import os
import asyncio
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(message)s",
)

def main():
    parser = argparse.ArgumentParser(
        description="FRONTLINE — AI Customer Support Triage System with Feedback and Ticketing Support",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py
  python main.py --evaluate
  python main.py --message "My order hasn't arrived"
  python main.py --web
  python main.py --provider gemini --model gemini-1.5-flash
  python main.py --feedback-collect   # Collect feedback-eligible results
  python main.py --feedback-submit    # Submit feedback interactively
  python main.py --no-tickets         # Disable automatic ticket creation
  python main.py --ticket-config      # Configure ticketing system
  python main.py --stream             # Enable streaming response for real-time feedback
  python main.py --async-mode         # Enable asynchronous batch processing for improved throughput
        """,
    )
    parser.add_argument("--message", "-m", type=str, help="Triage a single message")
    parser.add_argument("--evaluate", "-e", action="store_true", help="Run evaluation after processing")
    parser.add_argument("--web", "-w", action="store_true", help="Launch the web dashboard")
    parser.add_argument("--results", "-r", type=str, help="Path to saved results JSON to display")
    parser.add_argument("--provider", type=str, default=None, help="LLM provider: openai or gemini")
    parser.add_argument("--feedback-collect", action="store_true", help="Collect feedback-eligible results instead of processing")
    parser.add_argument("--feedback-submit", action="store_true", help="Submit feedback interactively via CLI")
    parser.add_argument("--feedback-file", type=str, help="Path to feedback submission JSON file")
    parser.add_argument("--no-tickets", action="store_true", help="Disable automatic ticket creation")
    parser.add_argument("--ticket-config", action="store_true", help="Configure ticketing system")
    parser.add_argument("--model", type=str, default=None, help="Model name")
    parser.add_argument("--no-cli", action="store_true", help="Skip CLI table display")
    parser.add_argument("--stream", action="store_true", help="Enable streaming response for real-time feedback")
    parser.add_argument("--async-mode", action="store_true", help="Enable asynchronous batch processing for improved throughput")
    args = parser.parse_args()

    if args.ticket_config:
        print("Configuring ticketing system...")
        from src.triage.ticketing import load_ticketing_config, save_ticketing_config

        config = load_ticketing_config()
        print("Current ticketing configuration:")
        print(json.dumps(config, indent=2))

        print("\nEnter new configuration (press Enter to keep current value):")

        # Enable/disable
        current_enabled = config.get("enabled", False)
        new_enabled = input(f"Enable ticketing? [{'y' if current_enabled else 'n'}]: ").strip().lower()
        if new_enabled:
            config["enabled"] = new_enabled in ['y', 'yes', 'true', '1']

        # Provider
        current_provider = config.get("provider", "none")
        new_provider = input(f"Ticketing provider (none/zendesk/jira/webhook) [{current_provider}]: ").strip()
        if new_provider:
            config["provider"] = new_provider

        # If not none, ask for additional config
        if config["provider"] != "none":
            if config["provider"] == "zendesk":
                subdomain = input(f"Zendesk subdomain [{config.get('subdomain', '')}]: ").strip()
                if subdomain:
                    config["subdomain"] = subdomain
                email = input(f"Email address [{config.get('email', '')}]: ").strip()
                if email:
                    config["email"] = email
                # Note: In a real app, you'd handle API token more securely
                api_token = input(f"API token [{'set' if config.get('api_token') else 'not set'}]: ").strip()
                if api_token:
                    config["api_token"] = api_token

            elif config["provider"] == "jira":
                subdomain = input(f"Jira subdomain [{config.get('subdomain', '')}]: ").strip()
                if subdomain:
                    config["subdomain"] = subdomain
                email = input(f"Email address [{config.get('email', '')}]: ").strip()
                if email:
                    config["email"] = email
                api_token = input(f"API token [{'set' if config.get('api_token') else 'not set'}]: ").strip()
                if api_token:
                    config["api_token"] = api_token
                project_key = input(f"Project key [{config.get('project_key', '')}]: ").strip()
                if project_key:
                    config["project_key"] = project_key

            elif config["provider"] == "webhook":
                webhook_url = input(f"Webhook URL [{config.get('webhook_url', '')}]: ").strip()
                if webhook_url:
                    config["webhook_url"] = webhook_url

        # Advanced options
        create_for_needs_human = input(f"Create tickets for needs_human=True? [{'y' if config.get('create_ticket_for_needs_human', True) else 'n'}]: ").strip()
        if create_for_needs_human:
            config["create_ticket_for_needs_human"] = create_for_needs_human.lower() in ['y', 'yes', 'true', '1']

        save_ticketing_config(config)
        print("Configuration saved!")
        return

    if args.web:
        print("Starting FRONTLINE Web Dashboard at http://localhost:5000")
        from src.ui.app import app
        app.run(debug=False, port=5000)
        return

    if args.feedback_collect:
        print("Collecting feedback-eligible results...")
        from src.triage.processor import process_batch_with_feedback_collection
        results, feedback_items = process_batch_with_feedback_collection(
            provider=args.provider,
            model=args.model,
            collect_feedback=True,
            create_tickets=not args.no_tickets
        )

        # Save feedback items to file for later submission
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        feedback_path = Path("outputs") / f"feedback_eligible_{timestamp}.json"
        feedback_path.parent.mkdir(exist_ok=True)

        with open(feedback_path, "w") as f:
            json.dump(feedback_items, f, indent=2)

        print(f"Collected {len(feedback_items)} feedback-eligible items")
        print(f"Saved to: {feedback_path}")
        print("To submit feedback, run: python main.py --feedback-submit --feedback-file", feedback_path)
        return

    if args.feedback_submit:
        print("Submitting feedback...")
        feedback_file = args.feedback_file

        if not feedback_file:
            # Find latest feedback file
            outputs_dir = Path("outputs")
            feedback_files = list(outputs_dir.glob("feedback_eligible_*.json"))
            if not feedback_files:
                print("No feedback files found. Run with --feedback-collect first.")
                return
            feedback_file = max(feedback_files, key=lambda f: f.stat().st_mtime)

        print(f"Loading feedback items from: {feedback_file}")

        with open(feedback_file, "r") as f:
            feedback_items = json.load(f)

        submitted_count = 0
        for item in feedback_items:
            print(f"\nMessage ID: {item['message_id']}")
            print(f"Message: {item['original_text'][:100]}{'...' if len(item['original_text']) > 100 else ''}")
            print("\nAI Prediction:")
            print(json.dumps(item['ai_prediction'], indent=2))

            print("\nPlease provide the corrected decision. Enter JSON values (press Enter to keep AI's value):")

            corrected = {}
            fields = ["category", "priority", "summary", "suggested_action", "needs_human", "confidence"]

            for field in fields:
                ai_value = item['ai_prediction'].get(field, "")
                if field == "needs_human":
                    current = "true" if ai_value else "false"
                    new_val = input(f"  {field} [{current}]: ").strip()
                    if new_val:
                        corrected[field] = new_val.lower() == "true"
                    else:
                        corrected[field] = ai_value
                elif field == "confidence":
                    current = str(ai_value)
                    new_val = input(f"  {field} [{current}]: ").strip()
                    if new_val:
                        try:
                            corrected[field] = float(new_val)
                        except ValueError:
                            print(f"   Invalid number, keeping AI's value: {ai_value}")
                            corrected[field] = ai_value
                    else:
                        corrected[field] = ai_value
                else:
                    current = str(ai_value)
                    new_val = input(f"  {field} [{current}]: ").strip()
                    if new_val:
                        corrected[field] = new_val
                    else:
                        corrected[field] = ai_value

            # Submit the feedback
            from src.triage.processor import submit_feedback
            success = submit_feedback(
                message_id=item['message_id'],
                original_text=item['original_text'],
                original_prediction=item['ai_prediction'],
                corrected_decision=corrected,
                feedback_source="cli_interactive"
            )

            if success:
                print("✓ Feedback submitted successfully!")
                submitted_count += 1
            else:
                print("✗ Failed to submit feedback")

        print(f"\nSubmitted {submitted_count}/{len(feedback_items)} feedback items.")
        return

    if args.results:
        with open(args.results, "r", encoding="utf-8") as f:
            results = json.load(f)
    elif args.message:
        from src.triage.processor import process_single, process_single_stream
        if args.stream:
            # Handle streaming for single message
            print("Streaming response for single message:")
            print("-" * 50)
            stream_gen = process_single_stream(
                args.message,
                provider=args.provider,
                model=args.model,
                create_ticket=not args.no_tickets
            )

            final_result = None
            for chunk in stream_gen:
                if chunk["type"] == "chunk":
                    print(chunk["content"], end="", flush=True)
                elif chunk["type"] == "result":
                    # Intermediate result, we'll show the final one
                    pass
                elif chunk["type"] == "complete":
                    final_result = {k: v for k, v in chunk.items()
                                  if k not in ["type", "original_text"]}
                    print()  # New line after streaming
                    print("-" * 50)
                    print("Completed!")
                elif chunk["type"] == "error":
                    print(f"\nError: {chunk['error']}")
                    final_result = {"error": chunk["error"]}

            if final_result:
                results = [{"id": "SINGLE_STREAM", "original_text": args.message, **final_result}]
            else:
                results = [{"id": "SINGLE_STREAM", "original_text": args.message, "error": "No result"}]
        else:
            # Standard processing
            result = process_single(
                args.message,
                provider=args.provider,
                model=args.model,
                create_ticket=not args.no_tickets
            )
            results = [{"id": "SINGLE", "original_text": args.message, **result}]
    else:
        print("Running FRONTLINE triage on all messages...\n")
        from src.triage.processor import process_all, process_all_async
        if args.stream:
            # Handle streaming mode
            print("Streaming responses for all messages:")
            print("=" * 50)
            stream_gen = process_all(
                provider=args.provider,
                model=args.model,
                create_tickets=not args.no_tickets,
                stream=True
            )

            # Process the stream and collect results for display/evaluation
            stream_results = []
            for chunk in stream_gen:
                if chunk["type"] in ["result", "complete"]:
                    # This is a final result
                    if chunk["type"] == "complete":
                        result_data = {k: v for k, v in chunk.items()
                                     if k not in ["type", "original_text"]}
                    else:
                        result_data = chunk.get("result", {})

                    # Add message ID if not present
                    if "id" not in result_data:
                        result_data["id"] = f"stream_{len(stream_results)}"

                    stream_results.append(result_data)
                    print(f"[{len(stream_results)}] Completed: {result_data.get('category', 'unknown')} - {result_data.get('priority', 'unknown')}")
                elif chunk["type"] == "chunk":
                    # Show streaming progress
                    print(f"[{chunk.get('message_id', '?')}] {chunk['content']}", end="", flush=True)
                elif chunk["type"] == "error":
                    print(f"\nError processing {chunk.get('message_id', 'unknown')}: {chunk['error']}")

            results = stream_results
            print("=" * 50)
            print(f"Streaming complete. Processed {len(results)} messages.")
        elif args.async_mode:
            # Handle asynchronous batch processing
            print("Processing messages asynchronously with concurrent LLM calls...")
            results = asyncio.run(process_all_async(
                provider=args.provider,
                model=args.model,
                create_tickets=not args.no_tickets,
                max_concurrency=10
            ))
            print(f"Asynchronous processing complete. Processed {len(results)} messages.")
        else:
            # Standard processing
            results = process_all(
                provider=args.provider,
                model=args.model,
                create_tickets=not args.no_tickets
            )

    if not args.no_cli:
        from src.ui.cli import display_results
        display_results(results)

    if args.evaluate and not args.message:
        from evaluation.evaluate import evaluate, print_evaluation_report
        metrics = evaluate(results)
        print_evaluation_report(metrics)

        # Save eval report
        out_path = Path("outputs") / "evaluation_report.json"
        out_path.parent.mkdir(exist_ok=True)
        with open(out_path, "w") as f:
            json.dump(metrics, f, indent=2)
        print(f"Evaluation report saved to: {out_path}")


if __name__ == "__main__":
    main()