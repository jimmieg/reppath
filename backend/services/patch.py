def apply_patch(plan: dict, patch: dict) -> dict:
    """
    patch shape:
    {
      "exercise_id": "mon_ex_2",
      "updates": {
        "name": "Romanian Deadlift",
        "sets": 3,
        "reps": "8-10",
        "load_guidance": "RPE 7"
      }
    }
    Mutates a deep copy of plan and returns it.
    """
    import copy
    plan = copy.deepcopy(plan)

    exercise_id = patch["exercise_id"]
    updates = patch["updates"]

    for day in plan.get("schedule", []):
        for exercise in day.get("exercises", []):
            if exercise.get("id") == exercise_id:
                exercise.update(updates)
                return plan

    raise ValueError(f"Exercise ID '{exercise_id}' not found in plan.")