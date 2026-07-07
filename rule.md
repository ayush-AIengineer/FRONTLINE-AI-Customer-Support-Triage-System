FRONTLINE — One-Day AI Build Challenge
 
Build AI software you'd actually trust to run on its own.
 
The situation
 
A fast-growing company is drowning in customer messages — support requests, complaints, random questions, all dumped into one messy pile. They want an AI system on the front line that reads each message and makes a fast, structured triage decision. Your job: build it, and make it reliable enough that a real team would trust it unsupervised.
This isn't "make a chatbot reply." It's "turn unstructured, messy, sometimes-adversarial input into structured decisions software can act on — and know when to call a human."
 
What you're building
 
A tool that reads a set of raw customer messages and, for each one, outputs a structured triage decision:
{ category, priority (P0–P3), summary, suggested_action, needs_human, confidence }
You'll get a dataset of ~40 real-style messages: some clear, some vague, some angry, multi-issue, sarcastic, out-of-scope, non-English — plus a few designed to trip up lazy solutions. Handle them all without falling over.
 
Levels — clear the first, then climb
 
Level 1 · It works (everyone hits this) Processes every message. Emits valid, consistent JSON — not prose. Runs end-to-end on the messy dataset without crashing.
Level 2 · It's reliable (this is where you separate yourself) Flags low-confidence / ambiguous cases for a human instead of guessing. Doesn't get hijacked by message content (yes, one message will try). Never invents details that aren't in the message. Survives garbage input.
Level 3 · You can prove it (winning teams) Hand-label ~10 messages as ground truth, then measure how often your system agrees — report the number and where it fails. Note rough tokens / cost / latency per message + one idea to cut it. Add a minimal UI (CLI table, web page, or dashboard). Optional: let it call a tool/function when it needs one.
 
What you submit 
 
1. Code that runs (repo link Public).
2. One-page "AI Decisions" note: model + tools used, prompt strategy, how you handle uncertainty and bad input, how you know it works, what you'd fix with more time. - README
 
Using Cursor, Copilot, Claude, v0, etc. to build is encouraged — that's a skill we're testing. But you must understand and defend every line. Expect 2 minutes of "why did you do it this way?"
 

