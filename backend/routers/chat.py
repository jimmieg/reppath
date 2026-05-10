from fastapi import APIRouter, HTTPException
from backend.models import ChatRequest, ChatResponse
from backend.services import llm, patch as patch_service

router = APIRouter(prefix="/api")


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(body: ChatRequest):
    try:
        messages = [m.model_dump() for m in body.messages]
        result = llm.chat(messages, plan=body.plan)

        # If a patch came back, apply it now and get a confirmation reply
        if result["patch"]:
            if not body.plan:
                raise HTTPException(400, "patch_exercise called but no plan exists yet")
            updated_plan = patch_service.apply_patch(body.plan, result["patch"])
            result["plan"] = updated_plan

            # One more LLM call for the confirmation sentence
            confirm_messages = messages + [
                {
                    "role": "assistant",
                    "content": f"patch_exercise applied: {result['patch']}",
                }
            ]
            confirm = llm.chat(confirm_messages, plan=updated_plan)
            result["reply"] = confirm["reply"] or "Done — your calendar has been updated."

        return ChatResponse(**result)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))