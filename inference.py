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


def run_task(task_id: str, task_description: str) -> float:
    # 1. Reset environment
    r = httpx.post(f"{ENV_BASE_URL}/reset?task_id={task_id}", timeout=30)
    data = r.json()
    session_id = data["session_id"]
    obs = data["observation"]

    # 2. Log [START]
    print(json.dumps({"type": "START", "task_id": task_id,
                      "task_description": task_description,
                      "model": MODEL_NAME}), flush=True)
    # Hackathon required format:
    print(f'[START] {{"task_id": "{task_id}", "task_description": "{task_description}", "model": "{MODEL_NAME}"}}', flush=True)

    total_reward = 0.0
    step_num = 0
    done = False
    conversation_history = []

    while not done and step_num < 20:
        step_num += 1

        # 3. Build prompt with current observation
        obs_text = json.dumps(obs, indent=2, default=str)
        user_message = f"Current inbox observation:\n{obs_text}\n\nWhat action do you take on the current_email?"

        conversation_history.append({"role": "user", "content": user_message})

        # 4. Call LLM
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
        except Exception as e:
            # Fallback action on parse failure
            action_dict = {"action_type": "skip", "email_id": obs["current_email"]["id"]}
            conversation_history.append({"role": "assistant", "content": json.dumps(action_dict)})

        # 5. Submit action to environment
        try:
            r = httpx.post(
                f"{ENV_BASE_URL}/step?session_id={session_id}",
                json=action_dict,
                timeout=60  # Task 3 grader makes LLM calls
            )
            result = r.json()
            reward = result["reward"]["score"]
            done = result["done"]
            obs = result["observation"]
            info = result.get("info", {})
        except Exception as e:
            reward = 0.0
            done = True
            info = {"error": str(e)}

        total_reward += reward

        # 6. Log [STEP] — exact hackathon format
        print(f'[STEP] {{"step": {step_num}, "action": {json.dumps(action_dict)}, "reward": {round(reward, 4)}, "done": {str(done).lower()}, "info": {json.dumps(info)}}}', flush=True)

    # Normalize total reward to 0.0-1.0
    final_score = min(round(total_reward / max(step_num, 1), 4), 1.0)
    success = final_score >= 0.5

    # 7. Log [END] — exact hackathon format
    print(f'[END] {{"task_id": "{task_id}", "total_reward": {round(total_reward, 4)}, "final_score": {final_score}, "steps": {step_num}, "success": {str(success).lower()}}}', flush=True)

    return final_score


def main():
    tasks = [
        ("task_1", "Delete or archive all spam emails without touching legitimate ones."),
        ("task_2", "Label all emails by category and mark the 3 most urgent."),
        ("task_3", "Reply to all customer emails with appropriate, helpful responses."),
    ]

    all_scores = {}
    for task_id, task_desc in tasks:
        score = run_task(task_id, task_desc)
        all_scores[task_id] = score
        print(f'[SUMMARY] {{"task_id": "{task_id}", "score": {score}}}', flush=True)

    print(f'[FINAL] {{"scores": {json.dumps(all_scores)}, "mean_score": {round(sum(all_scores.values())/3, 4)}}}', flush=True)


if __name__ == "__main__":
    main()
