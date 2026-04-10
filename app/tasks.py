import json
import os
from typing import List

from openai import OpenAI

from app.models import Email, EmailAction


def clamp(score: float) -> float:
    """Ensure score is strictly between 0 and 1, never exactly 0.0 or 1.0"""
    return max(0.0001, min(round(float(score), 4), 0.9999))


def clamp_scores(values: dict) -> dict:
    """Clamp numeric score components so exposed score fields stay validator-safe."""
    clamped = {}
    for key, value in values.items():
        if isinstance(value, (int, float)):
            clamped[key] = clamp(value)
        else:
            clamped[key] = value
    return clamped

TASKS = {
    "task_1": {
        "id": "task_1",
        "name": "Spam Cleanup",
        "difficulty": "easy",
        "description": "Delete or archive all spam emails without touching legitimate ones.",
        "max_steps": 30,
    },
    "task_2": {
        "id": "task_2",
        "name": "Priority Inbox Sorting",
        "difficulty": "medium",
        "description": "Label all emails by category and mark the 3 most urgent.",
        "max_steps": 30,
    },
    "task_3": {
        "id": "task_3",
        "name": "Customer Support Response",
        "difficulty": "hard",
        "description": "Reply to all customer emails with appropriate, helpful responses.",
        "max_steps": 30,
    },
}

DESTRUCTIVE_ACTIONS = {"delete", "archive"}
SPAM_SUBJECT_KEYWORDS = {
    "lottery",
    "pill",
    "medication",
    "inheritance",
    "winner",
    "offer",
    "claim",
    "verification",
    "crypto",
}
TASK3_SYSTEM_PROMPT = (
    "You are an expert customer support evaluator. Score the following reply on 4 criteria, "
    "each 0.0-1.0: relevance (does it address the customer's issue?), tone (is it professional "
    "and empathetic?), completeness (does it fully resolve or acknowledge the issue?), "
    "accuracy (no false promises or wrong info?). Respond ONLY with valid JSON: "
    '{"relevance": 0.0, "tone": 0.0, "completeness": 0.0, "accuracy": 0.0}'
)


class Task1Grader:
    def __init__(self, inbox: List[Email]):
        self.spam_ids = self._identify_spam(inbox)
        self.legit_ids = [email.id for email in inbox if email.id not in self.spam_ids]
        self.removed_spam = set()
        self.harmed_legit = set()

    def _identify_spam(self, inbox: List[Email]) -> List[str]:
        spam_ids = []
        for email in inbox:
            lowered_subject = email.subject.lower()
            if any(keyword in lowered_subject for keyword in SPAM_SUBJECT_KEYWORDS):
                spam_ids.append(email.id)
        return spam_ids

    def grade_step(self, action: EmailAction) -> tuple[float, dict, str]:
        email_id = action.email_id
        if email_id in self.spam_ids:
            if action.action_type in DESTRUCTIVE_ACTIONS:
                self.removed_spam.add(email_id)
                return clamp(0.15), clamp_scores({"target_type": "spam", "action_alignment": 1.0}), "Removed spam email."
            if action.action_type in {"mark_urgent", "flag", "label"}:
                return clamp(-0.05), clamp_scores({"target_type": "spam", "action_alignment": 0.0}), "Spam email was preserved instead of removed."
            return clamp(0.0), clamp_scores({"target_type": "spam", "action_alignment": 0.0}), "Spam email was not removed."

        if email_id in self.legit_ids:
            if action.action_type in DESTRUCTIVE_ACTIONS:
                self.harmed_legit.add(email_id)
                return clamp(-0.10), clamp_scores({"target_type": "legitimate", "action_alignment": 0.0}), "Legitimate email was deleted or archived."
            return clamp(0.05), clamp_scores({"target_type": "legitimate", "action_alignment": 1.0}), "Legitimate email was kept."

        return clamp(0.0), clamp_scores({"target_type": "unknown", "action_alignment": 0.0}), "Email ID not recognized by Task 1 grader."

    def final_score(self) -> float:
        correct_spam_removed = len(self.removed_spam)
        legitimate_kept = len([email_id for email_id in self.legit_ids if email_id not in self.harmed_legit])
        spam_score = (correct_spam_removed / max(len(self.spam_ids), 1)) * 0.7
        legit_score = (legitimate_kept / max(len(self.legit_ids), 1)) * 0.3
        return clamp(min(spam_score + legit_score, 1.0))


class Task2Grader:
    def __init__(self, inbox: List[Email], ground_truth_labels: dict):
        del inbox
        self.ground_truth = {
            email_id: (label_data.get("label") if isinstance(label_data, dict) else label_data)
            for email_id, label_data in ground_truth_labels.items()
        }
        self.urgent_ids = [
            email_id for email_id, label in self.ground_truth.items() if label == "urgent_work"
        ]
        self.agent_labels = {}
        self.flagged_urgent = set()

    def grade_step(self, action: EmailAction) -> tuple[float, dict, str]:
        email_id = action.email_id
        correct_label = self.ground_truth.get(email_id)

        if action.action_type == "label":
            predicted_label = (action.label or "").strip()
            if not predicted_label:
                return clamp(0.0), clamp_scores({"label_present": 0.0, "label_correct": 0.0}), "No label provided."
            self.agent_labels[email_id] = predicted_label
            if predicted_label == correct_label:
                return clamp(0.12), clamp_scores({"label_present": 1.0, "label_correct": 1.0}), "Applied the correct label."
            return clamp(0.02), clamp_scores({"label_present": 1.0, "label_correct": 0.0}), "Applied a label, but it was not correct."

        if action.action_type == "mark_urgent":
            if email_id in self.urgent_ids:
                self.flagged_urgent.add(email_id)
                return clamp(0.10), clamp_scores({"urgent_marked_correctly": 1.0}), "Marked a truly urgent email."
            return clamp(-0.05), clamp_scores({"urgent_marked_correctly": 0.0}), "Marked a non-urgent email as urgent."

        if action.action_type in {"skip", "archive"} and email_id not in self.agent_labels:
            return clamp(-0.03), clamp_scores({"label_present": 0.0}), "Skipped or archived an email without labeling it."

        return clamp(0.0), clamp_scores({"label_present": float(email_id in self.agent_labels)}), "No Task 2 reward change for this action."

    def final_score(self) -> float:
        correct_labels = sum(
            1 for email_id, label in self.agent_labels.items() if self.ground_truth.get(email_id) == label
        )
        correct_urgent = len(self.flagged_urgent.intersection(self.urgent_ids))
        label_score = (correct_labels / max(len(self.ground_truth), 1)) * 0.6
        urgent_score = (correct_urgent / max(len(self.urgent_ids), 1)) * 0.4
        return clamp(min(label_score + urgent_score, 1.0))


class Task3Grader:
    def __init__(self, inbox: List[Email]):
        self.inbox = {email.id: email for email in inbox}
        self.reply_scores = {}
        self.client = None
        self.model_name = os.environ.get("MODEL_NAME", "gpt-4.1-mini")

    def _init_client(self):
        if self.client is not None:
            return
        api_base_url = os.environ.get("API_BASE_URL")
        api_key = os.environ.get("HF_TOKEN") or os.environ.get("OPENAI_API_KEY") or "dummy"
        client_kwargs = {"api_key": api_key}
        if api_base_url:
            client_kwargs["base_url"] = api_base_url
        self.client = OpenAI(**client_kwargs)

    def _neutral_judgement(self) -> dict:
        return {
            "relevance": 0.3,
            "tone": 0.3,
            "completeness": 0.3,
            "accuracy": 0.3,
        }

    def _judge_reply(self, email: Email, reply_content: str) -> tuple[dict, str]:
        self._init_client()
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": TASK3_SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": f"Customer email: {email.body}\n\nAgent reply: {reply_content}",
                    },
                ],
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content or "{}"
            parsed = json.loads(content)
            scores = {}
            for key in ("relevance", "tone", "completeness", "accuracy"):
                value = float(parsed.get(key, 0.3))
                scores[key] = max(0.0, min(value, 1.0))
            return scores, "Reply evaluated by LLM judge."
        except Exception:
            return self._neutral_judgement(), "LLM judge unavailable; used neutral fallback."

    def grade_step(self, action: EmailAction) -> tuple[float, dict, str]:
        email = self.inbox.get(action.email_id)
        if email is None:
            return clamp(0.0), clamp_scores({"reply_mean": 0.0}), "Email ID not recognized by Task 3 grader."

        if action.action_type != "reply":
            return clamp(-0.05), clamp_scores({"reply_required": 0.0}), "Customer email required a reply."

        reply_content = (action.content or "").strip()
        if len(reply_content) < 20:
            return clamp(0.0), clamp_scores({"reply_mean": 0.0}), "Reply too short"

        scores, feedback = self._judge_reply(email, reply_content)
        mean_score = sum(scores.values()) / len(scores)
        self.reply_scores[action.email_id] = mean_score
        step_reward = mean_score * 0.2
        partial_scores = {
            "relevance": scores["relevance"],
            "tone": scores["tone"],
            "completeness": scores["completeness"],
            "accuracy": scores["accuracy"],
            "reply_mean": mean_score,
        }
        return clamp(step_reward), clamp_scores(partial_scores), feedback

    def final_score(self) -> float:
        total = sum(self.reply_scores.values())
        return clamp(min(total / max(len(self.inbox), 1), 1.0))


def build_grader(task_id: str, inbox: List[Email], label_metadata: dict):
    if task_id == "task_1":
        return Task1Grader(inbox)
    if task_id == "task_2":
        return Task2Grader(inbox, label_metadata)
    if task_id == "task_3":
        return Task3Grader(inbox)
    raise ValueError(f"Unsupported task_id: {task_id}")
