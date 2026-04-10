"""
Baseline inference script for Email Triage Environment.
Reads: API_BASE_URL, MODEL_NAME, HF_TOKEN from environment variables.
Usage: python3 inference.py
"""

import os, json, httpx
from openai import OpenAI

# Config from env vars
API_BASE_URL = os.environ.get("API_BASE_URL", "https://api.openai.com/v1")
MODEL_NAME = os.environ.get("MODEL_NAME", "gpt-4o-mini")
HF_TOKEN = os.environ.get("HF_TOKEN")
ENV_BASE_URL = os.environ.get("ENV_BASE_URL", "http://localhost:7860")

client = OpenAI(base_url=API_BASE_URL, api_key=HF_TOKEN)


def clamp_score(score: float) -> float:
    return max(0.05, min(round(float(score), 4), 0.95))


SYSTEM_PROMPT = """You are an expert email triage agent. You will be given an inbox
observation as JSON. You must respond with ONLY a valid JSON object representing
your action. No explanation, no markdown, just raw JSON.

Available action_types: reply, archive, delete, flag, label, mark_urgent, snooze, skip
Available labels: spam, urgent_work, meeting_request, invoice, newsletter, personal

Your JSON must have these fields:
- action_type: string (required)
- email_id: string (required, must be the id of current_email)
- content: string (only for reply actions, min 30 words)
- label: string (only for label actions)
- forward_to: string (only for forward actions)
- snooze_hours: integer (only for snooze actions)

Always act on the current_email's id. Be decisive and efficient."""


def run_task(task_id: str) -> None:
    # 1. Reset environment
    r = httpx.post(f"{ENV_BASE_URL}/reset?task_id={task_id}", timeout=30)
    data = r.json()
    session_id = data["session_id"]
    obs = data["observation"]

    # 2. Log [START]
    print(f"[START] task={task_id} env=email-triage model={MODEL_NAME}", flush=True)

    rewards = []
    step_num = 0
    done = False
    conversation_history = []
    error_msg = None

    while not done and step_num < 20:
        step_num += 1

        # 3. Build prompt with current observation
        obs_text = json.dumps(obs, indent=2, default=str)
        user_message = f"Current inbox observation:\n{obs_text}\n\nWhat action do you take on the current_email?"

        conversation_history.append({"role": "user", "content": user_message})

        # 4. Call LLM
        action_type = "skip"
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                max_tokens=500,
                messages=[{"role": "system", "content": SYSTEM_PROMPT}] + conversation_history
            )
            raw = response.choices[0].message.content.strip()
            # Strip markdown fences if present
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            action_dict = json.loads(raw.strip())
            conversation_history.append({"role": "assistant", "content": raw})
            action_type = action_dict.get("action_type", "skip")
        except Exception as e:
            # Fallback action on parse failure
            action_dict = {"action_type": "skip", "email_id": obs["current_email"]["id"]}
            conversation_history.append({"role": "assistant", "content": json.dumps(action_dict)})
            error_msg = str(e)
            action_type = "skip"

        # 5. Submit action to environment
        try:
            r = httpx.post(
                f"{ENV_BASE_URL}/step?session_id={session_id}",
                json=action_dict,
                timeout=60
            )
            result = r.json()
            reward = max(0.05, min(float(result["reward"]["score"]), 0.95))
            done = result["done"]
            obs = result["observation"]
            error_msg = None
        except Exception as e:
            reward = 0.05
            done = True
            error_msg = str(e)

        rewards.append(reward)

        # 6. Log [STEP]
        error_str = error_msg if error_msg else "null"
        print(f"[STEP] step={step_num} action={action_type} reward={reward:.2f} done={str(done).lower()} error={error_str}", flush=True)

    # Calculate final score
    if rewards:
        avg_reward = sum(rewards) / len(rewards)
        final_score = clamp_score(avg_reward)
    else:
        final_score = 0.05

    success = final_score >= 0.5
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)

    # 7. Log [END]
    print(f"[END] success={str(success).lower()} steps={step_num} score={final_score:.3f} rewards={rewards_str}", flush=True)


def main():
    tasks = ["task_1", "task_2", "task_3"]

    for task_id in tasks:
        run_task(task_id)


if __name__ == "__main__":
    main()
