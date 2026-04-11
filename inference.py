"""
Baseline inference script for Email Triage Environment.
Reads: API_BASE_URL, MODEL_NAME, HF_TOKEN, ENV_BASE_URL from environment variables.
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
    return max(0.001, min(round(float(score), 4), 0.999))


# Task-specific system prompts for optimal performance on each task
SYSTEM_PROMPTS = {
    "task_1": """You are an email spam detection agent.
Your ONLY job is to DELETE spam and ARCHIVE legitimate emails.

Spam indicators: lottery wins, pills/medication offers, inheritance scams,
job offers from unknown companies, prize claims, urgent money requests,
"click here" phishing attempts, unsolicited product promotions.

Legitimate indicators: known colleagues, project updates, bills from real services,
meeting invitations, personal messages from real names, work communications.

Strategy:
- Use action_type 'delete' for any spam email.
- Use action_type 'archive' for any legitimate email.
- Never skip — always act on the current_email.
- If uncertain, prefer 'archive' over 'delete' to avoid destroying legitimate mail.

Respond with ONLY valid JSON. No explanation, no markdown fences, just raw JSON.
Example: {"action_type": "delete", "email_id": "task1_email_01"}""",

    "task_2": """You are an email categorization agent.
Your job is to LABEL every email with the correct category AND mark the 3 most urgent ones.

Available labels: spam, urgent_work, meeting_request, invoice, newsletter, personal

Label assignment rules:
- spam: Unsolicited, promotional, or scam content.
- urgent_work: Work tasks with deadlines, critical bugs, escalations, or time-sensitive requests.
- meeting_request: Calendar invites, scheduling requests, or meeting notifications.
- invoice: Bills, payment receipts, or financial documents from services.
- newsletter: Mailing lists, product updates, content digests.
- personal: Non-work messages from friends, family, or personal contacts.

Urgency rules (mark_urgent):
- Only mark an email urgent AFTER labeling it if it is urgent_work AND seems truly critical.
- Look for signals: "ASAP", "deadline today", "production down", "critical", escalating language.
- Only the top 3 most critical emails should receive mark_urgent.

Strategy per email:
1. First use action_type 'label' with the correct label.
2. If the email is urgent_work and clearly critical, also use mark_urgent in a follow-up step.

Respond with ONLY valid JSON. No explanation, no markdown fences, just raw JSON.
Example: {"action_type": "label", "email_id": "task2_email_03", "label": "meeting_request"}""",

    "task_3": """You are a professional customer support agent.
Your job is to REPLY to every customer email with a helpful, empathetic, and complete response.

Requirements for a high-scoring reply:
- Address the customer's specific issue directly — do not give a generic response.
- Use a professional yet warm and empathetic tone.
- Provide concrete next steps, a resolution, or a clear acknowledgment of the problem.
- If it's a follow-up email (references a previous interaction), explicitly acknowledge the prior contact.
- Minimum 50 words, maximum 150 words.
- Do not make promises you cannot verify (e.g. exact timelines unless stated in the email).
- End with a courteous closing and an offer to assist further.

Always use action_type 'reply' with a 'content' field containing your full response.

Respond with ONLY valid JSON. No explanation, no markdown fences, just raw JSON.
Example:
{
  "action_type": "reply",
  "email_id": "task3_email_02",
  "content": "Thank you for reaching out to us. I understand your frustration with the delayed shipment and sincerely apologize for the inconvenience. Your order has been escalated to our logistics team and you will receive an updated tracking number within 24 hours. Please don't hesitate to contact us if you need further assistance."
}"""
}


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

    # Select the task-specific system prompt
    system_prompt = SYSTEM_PROMPTS.get(task_id, SYSTEM_PROMPTS["task_1"])

    while not done and step_num < 20:
        step_num += 1

        # 3. Build prompt with current observation
        obs_text = json.dumps(obs, indent=2, default=str)
        user_message = f"Current inbox observation:\n{obs_text}\n\nWhat action do you take on the current_email?"

        conversation_history.append({"role": "user", "content": user_message})

        # Keep only the last 3 pairs (6 messages) to avoid token bloat
        conversation_history = conversation_history[-6:]

        # 4. Call LLM with task-specific system prompt
        action_type = "skip"
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                max_tokens=500,
                messages=[{"role": "system", "content": system_prompt}] + conversation_history
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
            reward = max(0.001, min(float(result["reward"]["score"]), 0.999))
            done = result["done"]
            obs = result["observation"]
            error_msg = None
        except Exception as e:
            reward = 0.001
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
        final_score = 0.001

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
