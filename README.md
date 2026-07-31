
# PawPal+ : An AI Agent for Pet Care Scheduling

## Base Project

This project extends **PawPal+**, originally built for AI110 Module 2
(`ai110-module2show-pawpal-starter`). The original scenario: a busy pet
owner needs help staying consistent with pet care, tracking tasks like
walks, feeding, meds, and grooming, with a system that considers time and
priority and produces a daily plan. The original app let the owner manually
enter pets and tasks through Streamlit forms, then displayed a schedule
sorted by time with conflict warnings — all rule-based, with no AI involved.

This final project keeps all of that original scheduling logic
(`Task`, `Pet`, `Owner`, `Scheduler` in `pawpal_system.py`) fully intact and
adds a new **Agentic Workflow** layer on top of it, powered by the Google
Gemini API.

---

## What This Project Does

PawPal+ now lets a pet owner manage their pet care schedule by simply
**talking to it in plain English**, instead of only filling out forms. For example:

> "Add a daily walk for Rex at 8am"
> "What's on today's schedule?"
> "Are there any scheduling conflicts?"

An AI agent (Gemini, via function calling) reads the request, decides which
underlying scheduling operation to perform, actually executes it against the
real `Scheduler`/`Pet`/`Task` objects, and then explains what it did in
natural language. The original manual forms are still available as a
fallback, and both paths operate on the exact same underlying data, so
anything the AI does is immediately reflected in the schedule and conflict
sections.

**Why it matters:** pet care requests are often quick and informal ("just
add a vet visit tomorrow at 9") rather than careful form-filling. Letting an
AI agent translate that informal request into a structured, validated
scheduling action — and catch conflicts automatically — removes friction
from a genuinely tedious task.

---

## Architecture Overview

The full system diagram (Mermaid source) is at
[`diagrams/architecture.mmd`](diagrams/architecture.mmd). Paste it into
[mermaid.live](https://mermaid.live) to view it rendered, or view it directly
on GitHub.

**High-level flow:**

1. **Input** — the user types a natural-language request into the Streamlit
   chat box (`app.py`), or uses the manual "Add Pet" / "Add Task" forms.
2. **Agentic layer** (`pawpal_agent.py`) — the `chat()` function sends the
   message to Gemini along with 7 available tools (`add_pet_tool`,
   `add_task_tool`, `get_schedule_tool`, `detect_conflicts_tool`,
   `filter_incomplete_tasks_tool`, `filter_by_pet_tool`,
   `complete_task_tool`). Gemini decides whether to call a tool, and with
   what arguments.
3. **Tool execution** — the requested tool runs against the real
   `Owner`/`Pet`/`Task`/`Scheduler` objects. This is where the AI's decision
   actually changes application state — it is not a side, standalone script.
4. **Multi-step loop** — if Gemini needs to call more than one tool in a row
   (e.g. add a task, then check conflicts), the loop continues, capped at 5
   steps as a guardrail against runaway loops.
5. **Output** — Gemini's final natural-language summary is shown in the
   chat, and the page reruns so "Today's Schedule" and "Conflicts"
   immediately reflect whatever the agent changed.
6. **Reliability layer** — every request/tool-call/error is logged to
   `agent.log`; rate-limit errors are automatically retried with a
   server-suggested delay; all tool execution is wrapped in `try/except`
   so a bad model response can never crash the app.
7. **Human-in-the-loop** — a developer can review `agent.log` to confirm
   correct tool calls; manual-form results can be cross-checked against
   AI-driven results; and `test_agent.py` provides scripted test
   conversations reviewed by a human before submission.

---

## Getting Started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Configure your Gemini API key

1. Get a free key at [https://aistudio.google.com/apikey](https://aistudio.google.com/apikey)
   (free tier, no credit card required).
2. Create a file named `.env` in the project root:

GEMINI_API_KEY=your_key_here

3. `.env` is already excluded via `.gitignore` — never commit your real key.

### Run the app

```bash
streamlit run app.py
```

### Suggested workflow (if extending further)

1. Review the architecture diagram and existing tool list.
2. Identify any new scheduling capability you want the agent to support.
3. Add the corresponding method to `PawPalAgent` in `pawpal_agent.py`.
4. Add a matching `FunctionDeclaration` and register it in `pawpal_tool`.
5. Add a scripted test case to `test_agent.py`.
6. Update `diagrams/architecture.mmd` if the flow changed.

---

## 🤖 Sample Interactions (AI Agent)

The following are real, unedited outputs captured from `test_agent.py`
(logged via `agent.log`), showing the agent understanding a request,
choosing a tool, executing it against the real system, and explaining the
result.

**Example 1 — Adding a task via natural language**

User: Add a morning walk for Rex at 8am, it happens daily.

[LOG] Gemini requested tool: add_task_tool with args
{'pet_name': 'Rex', 'description': 'morning walk', 'time': '08:00', 'frequency': 'daily'}
[LOG] Added task: pet=Rex, description=morning walk, time=08:00, frequency=daily

Agent: I have successfully scheduled a daily morning walk for Rex at 08:00.


**Example 2 — Querying the schedule**

User: What's on today's schedule?

[LOG] Gemini requested tool: get_schedule_tool with args {}
[LOG] Retrieved schedule (1 tasks)

Agent: Today's schedule has one task:

08:00 – Morning walk for Rex (dog)

**Example 3 — Adding a conflicting task, then detecting the conflict**

User: Add a vet visit for Rex at 8am, just once.
Agent: I've successfully scheduled a vet visit for Rex at 08:00 (once).

User: Are there any scheduling conflicts?

[LOG] Gemini requested tool: detect_conflicts_tool with args {}
[LOG] Checked conflicts: found 1

Agent: Yes, there is a scheduling conflict:

08:00: "morning walk" for Rex conflicts with "Vet visit" for Rex.

---

## 🧪 Testing PawPal+

```bash
# Original scheduling logic (no AI involved):
pytest test_pawpal.py

# Scripted AI agent conversations:
python3 test_agent.py
```

Sample `pytest` output:

======== test session starts ========
collected 5 items
tests/test_pawpal.py::test_mark_complete PASSED
tests/test_pawpal.py::test_add_task PASSED
tests/test_pawpal.py::test_sort_by_time PASSED
tests/test_pawpal.py::test_recurring_daily PASSED
tests/test_pawpal.py::test_conflict PASSED
========= 5 passed in 0.07s ============


Sample `test_agent.py` outcome: all 3 scripted conversations completed
successfully — adding a recurring task, querying the schedule, and adding
a conflicting task followed by an accurate conflict detection (full logs
in the Sample Interactions section above).

**Confidence Level:** ⭐⭐⭐⭐ (4/5) — Core scheduling logic (5/5 pytest tests)
and all 3 scripted agent conversations pass reliably. One point held back
because the agent's behavior still depends on a third-party API (rate
limits, occasional 503s), and the tool set, while functional, is not yet
exhaustive (e.g. no "delete task" or "reschedule to a specific new time"
tool yet).

---
## Reliability & Evaluation

In addition to automated tests (`test_pawpal.py`, `test_agent.py`) and
logging/error-handling (`agent.log`, `try/except` guardrails, automatic
retry on rate limits — see Design Decisions above), the AI agent's behavior
was manually reviewed against a set of test conversations. Results below are
based on directly reading `agent.log` output (which tool was called, with
what arguments) and comparing it to the expected behavior, rather than a
demo video.

**Human Evaluation Results**

| Test Input | Evaluation Criteria | Result |
|---|---|---|
| "Add a morning walk for Rex at 8am, it happens daily." | Calls `add_task_tool` with correct pet, time, frequency; task actually appears in schedule afterward | ✅ Pass |
| "What's on today's schedule?" | Calls `get_schedule_tool`; summary text matches the actual task list | ✅ Pass |
| "Add a vet visit for Rex at 8am, just once." → "Are there any scheduling conflicts?" | Second message correctly identifies the 08:00 overlap created by the first | ✅ Pass |
| "Add a daily walk for Bella at 7am" (before Bella exists as a pet) | Should either add Bella first or clearly explain it can't find her | ✅ Pass (graceful) — agent explained it couldn't find Bella and asked whether to add tasks once she exists, rather than crashing or silently failing |
| "Add a new pet named Bella, she's a 2 year old cat." (before `add_pet_tool` existed) | Should register the pet | ❌ Fail (initial version) — agent had no tool for this, so it apologized and suggested the user add Bella manually instead of completing the action. **Fixed** by adding `add_pet_tool`; re-tested and passing. |
| Rapid back-to-back messages triggering a 429 rate-limit error | Should recover automatically without a user-visible crash | ✅ Pass — `agent.log` shows `Rate limited (attempt 1/3), waiting 9s...` followed by a successful retry and correct final answer |

**Summary:** 5 of 6 evaluated interactions passed on the first implementation;
the one failure (missing `add_pet_tool`) was a scoped gap rather than a bug,
and was fixed and re-verified. The agent handled a real, unplanned rate-limit
error during testing gracefully, which is direct evidence the reliability
guardrails work under real conditions rather than only in a "happy path" demo.

## 📐 Smarter Scheduling (Original Logic)

| Feature | Method(s) | Notes |
|---------|-----------|-------|
| Task sorting | `Scheduler.sort_by_time()` | Sorts all tasks chronologically by their "HH:MM" time string |
| Filtering | `Scheduler.filter_incomplete_tasks()`, `Scheduler.filter_by_pet()` | Filter tasks by completion status or by a specific pet |
| Conflict handling | `Scheduler.detect_conflicts()` | Flags tasks scheduled at the same time and returns warning messages |
| Recurring tasks | `Scheduler.complete_and_reschedule()` | When a daily/weekly task is completed, auto-generates the next occurrence using timedelta |

## 🤖 Agentic Tool Layer (New)

| Tool | Wraps | Notes |
|------|-------|-------|
| `add_pet_tool` | `Owner.add_pet()` | Lets the agent register a new pet from natural language |
| `add_task_tool` | `Pet.add_task()` | Lets the agent add a task without the user filling a form |
| `get_schedule_tool` | `Scheduler.sort_by_time()` | Agent can summarize the full schedule conversationally |
| `detect_conflicts_tool` | `Scheduler.detect_conflicts()` | Agent proactively checks for overlaps on request |
| `filter_incomplete_tasks_tool` | `Scheduler.filter_incomplete_tasks()` | Agent can answer "what's still left to do?" |
| `filter_by_pet_tool` | `Scheduler.filter_by_pet()` | Agent can answer "what does Rex have today?" |
| `complete_task_tool` | `Scheduler.complete_and_reschedule()` | Agent can mark tasks done and auto-reschedule recurring ones |

---

## 📸 Demo Walkthrough

1. Run the app with `streamlit run app.py`. The PawPal+ page opens in the browser.
2. Under **Owner**, enter the owner's name and click "Update Owner Name".
3. Under **🤖 AI Assistant**, type a request in plain English, e.g. *"Add a
   new pet named Bella, she's a 2 year old cat"* or *"Add a daily walk for
   Rex at 8am"*, and press Enter. The agent will decide which tool to call,
   execute it, and reply with a natural-language confirmation.
4. Alternatively (or in addition), use the manual **Add a Pet** / **Add a
   Task** forms below the chat — both paths update the exact same
   underlying schedule.
5. The **Today's Schedule** section automatically shows all tasks sorted by
   time, with each task's date, pet, species, age, owner, and completion
   status — whether it was added via chat or via the manual form.
6. If two tasks are scheduled at the same time, a **⚠️ Conflicts** section
   appears with a warning showing which tasks clash. Try asking the AI
   Assistant *"Are there any scheduling conflicts?"* to have it check and
   summarize this for you conversationally.
7. Every request the agent handles is recorded in `agent.log`, including
   which tool was called, with what arguments, and any errors encountered
   (useful for reviewing exactly what the AI did and why).

---

## Design Decisions

- **Function calling over free-form generation.** The agent is restricted
  to a fixed set of well-defined tools that wrap the original, already-tested
  `Scheduler` methods, rather than generating arbitrary code or text to
  "act." This keeps every AI-driven action auditable and prevents the model
  from doing anything outside the scheduling domain.
- **Shared state between AI and manual UI.** The agent operates on the same
  `Owner`/`Scheduler` objects as the manual Streamlit forms
  (`st.session_state.owner`), so the two interfaces can never drift out of
  sync, and a human can always fall back to manual forms if the AI is
  unavailable.
- **Multi-step tool loop with a hard cap.** Some requests need more than one
  tool call (e.g., "add this task and tell me if anything conflicts"). The
  loop allows up to 5 chained tool calls, capped to avoid runaway loops.
- **Retry-with-backoff for rate limits.** Google's free tier enforces
  per-minute request limits that a multi-tool-call conversation can
  sometimes exceed. `_send_with_retry()` parses the server's suggested wait
  time out of the error and retries automatically (up to 3 attempts), so
  transient rate limits are invisible to the end user in normal use.
- **Never trust `.text` alone.** An early version of the agent occasionally
  returned the literal string `"None"`, because Gemini's `response.text`
  convenience property returns `None` when a response contains only a
  function call and no accompanying text. The fix was to manually walk
  `response.candidates[0].content.parts` and extract text parts directly,
  with a safe fallback message if none is found.

---

## Reflection

See [`model_card.md`](model_card.md) for the full responsible-AI reflection,
including system limitations, potential misuse and mitigations, what
surprised us during reliability testing, and a specific example each of a
helpful and a flawed AI suggestion encountered while building this project.