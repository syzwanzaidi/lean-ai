import time


def start_action(step):
    """
    Start timing the current assembly action.
    """

    return {
        "step_id": step["id"],
        "action_name": step["title"],
        "description": step.get("action_description", step["instruction"]),
        "action_type": step.get("action_type", "VA"),
        "start_time": time.time(),
    }


def stop_action(active_action):
    """
    Stop timing and return completed action log.
    """

    end_time = time.time()
    duration = end_time - active_action["start_time"]

    return {
        "step_id": active_action["step_id"],
        "action_name": active_action["action_name"],
        "description": active_action["description"],
        "action_type": active_action["action_type"],
        "start_time": active_action["start_time"],
        "end_time": end_time,
        "duration_seconds": round(duration, 2),
    }