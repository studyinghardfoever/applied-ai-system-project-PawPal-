# Model Card: PawPal+ AI Agent

This document contains the responsible-AI reflection for the Agentic
Workflow layer added to PawPal+ (see `README.md` for the full project
description, architecture, setup instructions, and testing summary).

---

## What are the limitations or biases in your system?

**The core limitation is a technical choice: this system uses a
pre-trained, general-purpose large language model (Gemini) accessed via
function calling, rather than a model trained specifically for this task
using supervised learning.** We did not collect a labeled dataset of
"user message → correct tool call" examples and train a dedicated
classifier for pet-scheduling intent recognition. Instead, we rely on
Gemini's zero-shot understanding — its ability to interpret an intent it
was never specifically trained on, based only on general language
understanding learned from its (much larger, but generic) pre-training data.

This trade-off has real consequences:

- **No measurable task-specific accuracy.** Because we did not train a
  model ourselves, we cannot report a quantitative accuracy figure (e.g.,
  "92% of intents are classified correctly") the way a supervised model
  evaluated on a held-out test set could. Our confidence comes from a small
  number of manually reviewed test conversations (see the Reliability &
  Evaluation table in `README.md`), not from a statistically rigorous
  evaluation set.
- **Unpredictable behavior on unusual phrasing.** A model fine-tuned or
  trained specifically on pet-scheduling language would have a well-defined,
  bounded input space. A general-purpose LLM has a much larger and fuzzier
  "understood" input space, which means unusual, ambiguous, or highly
  domain-specific phrasing (e.g. regional slang, ambiguous times like "8"
  without am/pm) may be interpreted inconsistently, and we have no way to
  fully enumerate or guarantee coverage of every phrasing in advance.
- **Guardrails prevent crashes, not incorrect decisions.** The
  `try/except` wrapping and automatic retry logic (`_send_with_retry`) make
  the system robust against *transient failures* (rate limits, temporary
  server errors) but do nothing to verify that the model's *interpretation*
  of the user's intent was actually correct. There is no independent
  verification step before an action is executed against the real schedule
  — the system trusts Gemini's function-call arguments directly.
- **Third-party API dependency.** Because we use a hosted, general-purpose
  model rather than something we could run and evaluate locally, the system
  is also subject to the provider's rate limits, quota changes, and model
  deprecations (we hit three different quota/availability issues while
  building this project — see the Testing Summary in `README.md`).

A supervised model trained on a large, labeled dataset of real pet-owner
requests would likely have more predictable, measurable accuracy *within
its training distribution*, at the cost of far more up-front data
collection and much worse generalization to phrasing it hadn't seen before.
For a small, English, single-domain assistant like this one, we judged the
LLM + function-calling approach to be the more practical trade-off, but it
is a deliberate choice with real limitations, not a free win.

---

## Could your AI be misused, and how would you prevent that?

Because the system relies on a general-purpose model's understanding
rather than a narrowly-trained classifier with a well-defined input
boundary, the main misuse risk is **a user phrasing a request in an
unanticipated way that causes the agent to take an action the designer
didn't intend** — for example, ambiguous wording that gets misinterpreted
into the wrong tool call, or a request framed in a way designed to
manipulate the model into behaving outside its intended scope. Because a
supervised model has an explicitly bounded set of inputs it was trained on,
this kind of "the model understood something we didn't plan for" risk is
somewhat unique to relying on a general-purpose LLM.

There is also a simpler risk: since the chat interface can add, complete,
and reschedule tasks with no confirmation step, anyone with access to the
Streamlit session could use natural language to make rapid, wide-reaching
changes (e.g., mass-adding fake tasks, or marking real tasks complete to
hide that they were skipped).

**Mitigations already in place:**
- Function calling restricts the agent to a **fixed, auditable set of
  tools**. Even if the model misinterprets a request, the blast radius of
  any mistake is limited to what those specific tools can do — it cannot,
  for example, execute arbitrary code or access anything outside the
  `Owner`/`Pet`/`Task`/`Scheduler` objects it was given.
- Every tool call is logged to `agent.log`, so misuse or unexpected
  behavior is traceable after the fact.

**Mitigations that would be needed for a real deployment:**
- Per-owner authentication, so the agent only ever modifies the schedule of
  the currently authenticated user (today there is a single shared `Owner`
  object with no access control).
- A confirmation step before destructive or bulk actions, rather than
  immediate execution on the model's first interpretation.
- Monitoring for unusual usage patterns (e.g., dozens of tasks added in
  seconds) as a signal of possible misuse.

---

## What surprised you while testing your AI's reliability?

The most surprising result was how much of a difference the automatic
retry logic (`_send_with_retry`) made in practice, once it was added.
Before it existed, hitting Google's free-tier rate limit (which happened
repeatedly during development, especially on newer, lower-quota models)
meant the conversation simply failed with a raw error shown to the user.
After adding retry-with-backoff — which reads the server's suggested wait
time out of the 429 error and automatically waits and resends — the exact
same rate-limit conditions were handled invisibly: the app just felt
slower for a few seconds instead of broken. We hadn't expected such a small
addition (roughly 15 lines of code) to have such a large effect on the
perceived reliability and smoothness of the whole system. It reinforced
that a lot of "AI reliability" work isn't about improving the model itself
— it's about handling the mundane, external failure modes (rate limits,
transient network errors) gracefully around it.

---

## Collaboration with AI: One Helpful Suggestion, One Flawed Suggestion

**Helpful suggestion:** Early in development, the design settled on using
Gemini's function-calling (tool-use) feature rather than having the model
generate free-form text or code to describe what it wanted to do. This
constrained the agent to a fixed, auditable set of operations that map
directly onto the already-tested `Scheduler` methods from the original
Module 2 project. This turned out to be the single most important design
decision in the project: it meant every AI-driven action could be logged,
reviewed, and traced back to a specific tool call and a specific Scheduler
method, rather than trying to parse or trust arbitrary generated text.

**Flawed suggestion (and how it surfaced):** The initial version of the
agent's tool set did not include a way to register a *new* pet — only to
add tasks to pets that already existed. When a real test asked the agent to
"add a new pet named Bella," the agent could not actually do it. Instead of
failing loudly, it produced a plausible-sounding, friendly response
suggesting the user add Bella manually and offering to help with her tasks
once she existed. This response was well-written and superficially
helpful — but it was actually masking a real capability gap: the agent
*sounded* like it understood the request when it had, in fact, quietly
declined to complete it. This was caught by manually reading `agent.log`
and noticing "Add a new pet" was never followed by an `add_pet_tool` call.
The fix was to design and add a dedicated `add_pet_tool`
(see `pawpal_agent.py`), after which the same request was correctly
executed. This was a useful lesson: a fluent, polite natural-language
response can look like success even when the underlying action didn't
happen — which is exactly why logging the actual tool calls, not just the
final text reply, was essential to catching this.