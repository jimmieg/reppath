# REPORT.md

## Part 1 — What & Why

RepPath is an AI-powered training plan generator for individuals of varying experience levels who want a structured, science-backed path to their fitness goals. Whether a beginner building a consistent habit or an intermediate lifter adding structure to their training, RepPath conducts a multi-turn intake conversation to learn their goal, schedule, experience level, equipment access, and any injuries or limitations. It then generates a personalized weekly training plan shown as a visual calendar.

RepPath's core value proposition is that its plans are based on curated exercise science methodology rather than generic AI output. A ChromaDB vector database stores excerpts from peer-reviewed research and authoritative sources, including Schoenfeld et al. (2021) on loading recommendations, ACSM guidelines on fat loss and endurance, and progressive overload literature. When generating plans, relevant chunks are retrieved and injected into the system prompt to ensure the LLM's recommendations reflect actual exercise science instead of hallucinated advice.

Getting the AI behavior right is harder than it appears. The app must maintain a consistent conversational state across six intake questions without jumping ahead or skipping steps, retrieve the right methodology from a small corpus without pulling irrelevant chunks, call generate_plan() at exactly the right moment with all fields correctly populated, and support surgical single-exercise patches in adjustment mode without regenerating the entire plan. Each of these is a distinct failure mode and each required iteration to get right.

## Part 2 — Iterations

### V1

**Change:** Initial implementation retrieved RAG context on every single chat turn by concatenating all user messages into a single query string (e.g., "hi i want a strength plan a 5 beginner 12 no full gym yes").

**Motivating example:** Running the eval revealed the retrieval query for tc_01 was "hi i want a strength plan a 5 beginner 12" — a noisy, unstructured string that happened to return the right chunk first but would degrade as conversations grew longer.

**Delta:** Composite score on first eval run: 0.91 across 10 test cases. RAG fired 8 times per conversation instead of once.

**Conclusion:** The retrieval query was too noisy and fired too early. The fix was adding `_extract_goal()` in `llm.py` to scan for goal keywords before triggering retrieval. This eliminated ~7 unnecessary ChromaDB queries per conversation and ensured the retrieval query was always a clean, goal-specific string like "strength training programming" rather than the full conversation transcript. The remaining issue is corpus size — with only 10 total chunks, off-topic chunks (endurance appearing in strength queries) still surface due to limited nearest-neighbor options.

---

### V2

**Change:** Updated the system prompt's HARD RULES section to distinguish compound vs accessory rep ranges for strength plans, and added an explicit rule preventing pull movements on consecutive days for 4+ day programs.

**Motivating example:** tc_05 (strength, intermediate, 5 days) scored 0.53 on goal alignment because accessory exercises like Leg Press (8-10 reps), Calf Raise (10-12 reps), and Face Pull (10-12 reps) exceeded the strict max-6 rep rule. tc_08 (fat loss, 5 days) scored 0.0 on hard rules due to a pull pattern violation on Wednesday and Thursday.

**Delta:** Composite score improved from 0.91 → 0.99 after prompt update and eval fixes. Goal alignment improved from 0.86 → 1.00 average. Hard rules improved from 0.90 → 1.00 average.

**Conclusion:** The prompt change worked — the LLM correctly applied 1-6 reps to compound lifts and 8-12 to accessories after the distinction was made explicit. The back-to-back pull violation was eliminated. Two eval metric bugs were also discovered and fixed: time-based exercises (planks, intervals measured in minutes) were being incorrectly flagged by the rep range parser, and the consecutive day checker was using plan adjacency rather than calendar adjacency, incorrectly flagging Monday/Wednesday in a 3-day program as a violation. Next step would be adding metadata filtering in ChromaDB to restrict retrieval by goal tag, eliminating off-topic chunk retrieval entirely.

---

### V3

**Change:** Expanded corpus from 10 chunks to approximately 40 chunks by appending additional methodology content to all four goal-specific files, covering periodization models, RPE, volume landmarks, heart rate zones, HIIT vs steady state, and race-specific preparation.

**Motivating example:** Strength queries were returning endurance chunks (endurance_programming_1, endurance_programming_2) as chunks 3 and 4 because the corpus was too small for ChromaDB to find four relevant strength-specific neighbors. With only 1-3 chunks per file, the vector space was too sparse.

**Delta:** After expansion, strength queries now return two strength-specific chunks (strength_programming_0, strength_programming_1) in the top 4 results instead of one. Composite eval score held at 0.99 — no regression introduced.

**Known limitations carried forward:**
- Patch targeting relies on the LLM correctly identifying the exercise ID by day.
  If the specified exercise is not found on the requested day, the model patches
  the nearest match rather than returning an error. A production fix would add
  explicit ID validation in `patch.py` before calling the LLM.
- Plan generation occasionally returns one extra training day on 5+ day programs.
  The `days_per_week` field in the schema has a `maximum: 6` constraint but the
  LLM does not always respect it. A post-processing step trimming the schedule
  to the requested day count would fix this reliably.

**Conclusion:** Expanding the corpus improved retrieval relevance without breaking existing behavior. The endurance chunk still occasionally appears in strength queries, which is a known limitation of a small local corpus without metadata filtering. A production implementation would use ChromaDB's `where` filter to restrict queries by a `goal` metadata field, ensuring only goal-relevant documents are ever retrieved. This was considered but not implemented to keep the stack within the grader's single-key constraint.


## Part 3 — Code Walkthrough

When the app starts, the user sees a prompt asking what type of plan they want.This opening message is set directly 
in App.jsx as the initial message, so the conversation never starts with a blank screen.

After the user enters their goal, Chat.jsx:handleSubmit captures the input. It then calls onSend(), which triggers 
App.jsx:handleSend. This function adds the user's message to the conversation history, sets the loading 
state to true (showing "Thinking…" in the chat), and calls api.js:sendMessage, which sends the full message
history and current plan state to the backend at POST /api/chat.

The backend receives the request at routers/chat.py:chat_endpoint and deserializes it using the ChatRequest 
model from models.py. It then passes it to services/llm.py:chat. There, _build_system() calls _extract_goal() 
to scan the conversation for a goal keyword. Once a goal is detected, for example "strength", it retrieves 
the four most relevant methodology chunks from ChromaDB using services/rag.py:retrieve and adds them above 
the system prompt as [RETRIEVED CONTEXT]. The full prompt and message history are then sent to the OpenAI API, 
with generate_plan and patch_exercise set up as callable tools.

When the LLM runs generate_plan, the function arguments are extracted. Then a final targeted retrieval runs 
to fill rag_sources, and a follow-up API call gets the explanation message. The plan and reply are sent back 
to the frontend, where App.jsx updates the state and Calendar.jsx shows the weekly grid from the schedule array.

Design decision: Each exercise in the plan JSON has a stable id field (for example, mon_ex_2). This was a deliberate choice to make the patch_exercise tool work precisely. It targets one exercise by ID without changing 
anything else. The alternative would be to send the full plan back to the LLM and ask it to return
a modified version. However, that approach is slow, expensive, and risks the model changing that the user 
did not want to modify. Stable IDs keep patching fast and predictably.

## Part 4 — AI Disclosure & Safety

AI Assistant Usage
Claude (Anthropic) served as the main coding assistant for this project. It generated the initial structure for the FastAPI backend and the React frontend, as well as the frontend components, system prompt, generate_plan() JSON schema, evaluation harness, and the corpus documents.
There were three specific instances where the assistant failed and needed intervention:

ChromaDB and NumPy version conflict: The initial requirements.txt file specified chromadb==0.5.0, which relied on np.float_, a feature removed in NumPy 2.0. The server crashed on startup with an AttributeError. To fix this, NumPy had to be downgraded to below version 2.0 and ChromaDB upgraded to at least 0.4.24. The assistant did not anticipate this conflict when generating the original requirements.
OpenAI client proxies error: After fixing ChromaDB, the server crashed again with a TypeError: Client.init() got an unexpected keyword argument 'proxies'. This happened because the OpenAI SDK version did not match the httpx version it depends on. The assistant originally pinned openai==1.30.1, which was incompatible with the installed httpx. Fixing this required pinning openai==1.14.3 and httpx==0.27.0 explicitly.
RAG triggered on every intake turn: The assistant's original _build_system() implementation checked if any assistant message contained the word "goal." This was always true because the system prompt uses that word frequently. As a result, RAG triggered on every chat turn starting from the first message. The solution was to rewrite the goal detection logic to look for actual goal keywords in user messages instead of checking assistant messages.

Safety Risks
The main safety risk for RepPath is the possibility of the system generating incorrect exercise science advice that could lead to injury. For example, a user with a knee injury might get a plan that ignores their limitation if the LLM does not follow the injury handling rules in the system prompt. To address this, two steps were taken: the system prompt clearly tells the model never to give medical advice and to always defer to a physiotherapist. Also, the RAG pipeline bases its recommendations on curated peer-reviewed sources instead of relying only on the LLM's built-in knowledge. The accepted limitation is that the system cannot verify whether a user's reported injury is accurately described. If a user underreports a serious condition, the plan may still be inappropriate. This is shared as a known limitation rather than a solved problem.
Another risk is prompt injection through the injuries field. A user could try to include instructions in their injury description to manipulate plan generation. To prevent this, the backend treats all user input as data passed to the LLM context, not as executable instructions. The structured JSON output format also limits the risk of injection. No user input is ever executed as code.