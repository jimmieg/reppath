import os
import json
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from .rag import retrieve

load_dotenv()

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

SYSTEM_PROMPT = (Path(__file__).parent.parent / "prompts" / "system.txt").read_text()
TOOLS = json.loads((Path(__file__).parent.parent / "tools" / "generate_plan.json").read_text())

PATCH_TOOL = {
    "name": "patch_exercise",
    "description": "Surgically update a single exercise in the existing plan by its id. Use this for any single-exercise swap, removal, or modification. Never call generate_plan for a single-exercise change.",
    "parameters": {
        "type": "object",
        "required": ["exercise_id", "updates"],
        "properties": {
            "exercise_id": {
                "type": "string",
                "description": "The id field of the exercise to update, e.g. 'mon_ex_2'.",
            },
            "updates": {
                "type": "object",
                "description": "Key-value pairs of fields to overwrite. Only include fields that change.",
                "properties": {
                    "name": {"type": "string"},
                    "sets": {"type": "integer"},
                    "reps": {"type": "string"},
                    "rest_seconds": {"type": "integer"},
                    "load_guidance": {"type": "string"},
                    "notes": {"type": "string"},
                    "progression_note": {"type": "string"},
                },
            },
        },
    },
}

# Goal keywords mapped to retrieval queries
GOAL_KEYWORDS = {
    "strength": "strength training programming",
    "hypertrophy": "hypertrophy muscle building programming",
    "muscle": "hypertrophy muscle building programming",
    "fat loss": "fat loss exercise programming",
    "fat_loss": "fat loss exercise programming",
    "lose fat": "fat loss exercise programming",
    "endurance": "endurance aerobic training programming",
}


def _extract_goal(messages: list[dict]) -> str:
    """
    Scans conversation history for a confirmed goal keyword.
    Returns a retrieval query string if found, empty string otherwise.
    Only triggers RAG once the user has stated their goal.
    """
    full_text = " ".join(
        m["content"] for m in messages if m.get("content")
    ).lower()

    for keyword, query in GOAL_KEYWORDS.items():
        if keyword in full_text:
            return query
    return ""


def _build_system(messages: list[dict]) -> str:
    """
    Inject RAG context above the system prompt only when a goal keyword
    has been detected in the conversation. Early intake turns (e.g. 'hi')
    use the plain system prompt with no retrieval.
    """
    retrieval_query = _extract_goal(messages)
    if not retrieval_query:
        return SYSTEM_PROMPT

    context, _ = retrieve(retrieval_query)
    return f"[RETRIEVED CONTEXT]\n{context}\n\n{'='*40}\n\n{SYSTEM_PROMPT}"


def chat(messages: list[dict], plan: dict | None = None) -> dict:
    """
    messages: full conversation history in OpenAI format
    plan:     current plan state from the frontend (None during intake)

    Returns:
    {
      "reply": str,
      "plan":  dict | None,
      "patch": dict | None,
      "phase": "intake" | "plan" | "adjustment"
    }
    """
    system = _build_system(messages)

    tools = [
        {"type": "function", "function": TOOLS},
        {"type": "function", "function": PATCH_TOOL},
    ]

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": system}] + messages,
        tools=tools,
        tool_choice="auto",
        temperature=0.3,
    )

    msg = response.choices[0].message

    # ── No tool call → plain reply ──────────────────────────────────────
    if not msg.tool_calls:
        phase = "adjustment" if plan else "intake"
        return {"reply": msg.content, "plan": plan, "patch": None, "phase": phase}

    tool_call = msg.tool_calls[0]
    fn_name = tool_call.function.name
    args = json.loads(tool_call.function.arguments)

    # ── generate_plan() fired ───────────────────────────────────────────
    if fn_name == "generate_plan":
        # Final retrieval with the confirmed goal from the function call args
        # This is the most precise query — uses the exact goal enum value
        goal = args.get("goal", "")
        retrieval_query = GOAL_KEYWORDS.get(goal, f"{goal} training programming")
        context, source_ids = retrieve(retrieval_query)
        args["rag_sources"] = source_ids

        # Ask the model for a follow-up explanation message
        followup_messages = messages + [
            {"role": "assistant", "content": None, "tool_calls": [tool_call]},
            {
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps({"status": "rendered", "plan": args}),
            },
        ]
        followup = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": system}] + followup_messages,
            temperature=0.4,
        )
        reply = followup.choices[0].message.content
        return {"reply": reply, "plan": args, "patch": None, "phase": "plan"}

    # ── patch_exercise() fired ──────────────────────────────────────────
    if fn_name == "patch_exercise":
        return {
            "reply": "",       # chat.py fills this after patch is applied
            "plan": plan,
            "patch": args,
            "phase": "adjustment",
        }

    # Fallback — unknown tool
    return {"reply": msg.content or "", "plan": plan, "patch": None, "phase": "intake"}