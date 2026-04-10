from typing import Optional

from app.email_generator import get_task1_inbox, get_task2_inbox, get_task3_inbox
from app.models import Email, EmailAction, EmailObservation, EmailReward
from app.tasks import TASKS, build_grader, clamp, clamp_scores


class EmailTriageEnv:
    def __init__(self, task_id: str):
        if task_id not in TASKS:
            raise ValueError(f"Unsupported task_id: {task_id}")

        self.task_id = task_id
        self.max_steps = int(TASKS[task_id]["max_steps"])
        self.inbox: list[Email] = []
        self.label_metadata: dict = {}
        self.processed_email_ids: set[str] = set()
        self.action_counts: dict[str, int] = {}
        self.action_history: list[dict] = []
        self.current_email: Optional[Email] = None
        self.grader = None
        self.step_count = 0
        self.emails_processed = 0
        self.time_elapsed = 0.0
        self.cumulative_score = clamp(0.0)

    def reset(self) -> EmailObservation:
        self.inbox, self.label_metadata = self._load_task_data()
        self.processed_email_ids = set()
        self.action_counts = {}
        self.action_history = []
        self.step_count = 0
        self.emails_processed = 0
        self.time_elapsed = 0.0
        self.cumulative_score = clamp(0.0)
        self.grader = build_grader(self.task_id, self.inbox, self.label_metadata)
        self.current_email = self._get_next_email()
        return self._build_observation()

    def step(self, action: EmailAction) -> tuple[EmailObservation, EmailReward, bool, dict]:
        if not self.inbox:
            raise RuntimeError("Environment has not been reset. Call reset() before step().")
        if self.grader is None:
            raise RuntimeError("Task grader is not initialized. Call reset() before step().")

        if self.current_email is None:
            observation = self._build_observation()
            final_score = self.grader.final_score()
            reward = EmailReward(
                score=clamp(0.0),
                cumulative_score=self.cumulative_score,
                partial_scores=clamp_scores({"task_reward": clamp(0.0)}),
                feedback="Episode already completed.",
                done=True,
            )
            return observation, reward, True, {"reason": "no_current_email", "final_score": final_score}

        current_email = self.current_email
        self.step_count += 1
        self.time_elapsed += 1.0

        task_reward, task_details, task_feedback = self.grader.grade_step(action)
        score_terms = {"task_reward": task_reward}
        partial_scores = clamp_scores({"task_reward": task_reward, **task_details})
        feedback_parts = [task_feedback]

        if self.action_counts.get(action.email_id, 0) > 0:
            score_terms["repeated_action_penalty"] = -0.05
            partial_scores["repeated_action_penalty"] = clamp(-0.05)
            feedback_parts.append("Repeated action penalty applied.")
        self.action_counts[action.email_id] = self.action_counts.get(action.email_id, 0) + 1

        if action.email_id != current_email.id:
            score_terms["wrong_email_penalty"] = -0.1
            partial_scores["wrong_email_penalty"] = clamp(-0.1)
            feedback_parts.append("Action email_id did not match the current email.")

        invalid_penalty = self._invalid_action_penalty(action)
        if invalid_penalty:
            score_terms["invalid_action_penalty"] = invalid_penalty
            partial_scores["invalid_action_penalty"] = clamp(invalid_penalty)
            feedback_parts.append("Invalid action context penalty applied.")

        if self.step_count > 20:
            time_penalty = -0.02 * (self.step_count - 20)
            score_terms["time_penalty"] = time_penalty
            partial_scores["time_penalty"] = clamp(time_penalty)
            feedback_parts.append("Late-episode time penalty applied.")

        raw_score = sum(score_terms.values())
        clipped_score = clamp(raw_score)
        self.cumulative_score = clamp(self.cumulative_score + clipped_score)

        self.processed_email_ids.add(current_email.id)
        self.emails_processed = len(self.processed_email_ids)
        self.action_history.append(
            {
                "step": self.step_count,
                "current_email_id": current_email.id,
                "action": action.model_dump(),
                "score": clipped_score,
            }
        )

        self.current_email = self._get_next_email()
        done = self.current_email is None or self.step_count >= self.max_steps
        observation = self._build_observation()
        reward = EmailReward(
            score=clipped_score,
            cumulative_score=self.cumulative_score,
            partial_scores=partial_scores,
            feedback=" ".join(feedback_parts),
            done=done,
        )
        info = {
            "processed_email_id": current_email.id,
            "next_email_id": self.current_email.id if self.current_email else None,
            "label_metadata": self.label_metadata,
        }
        if done:
            info["final_score"] = clamp(self.grader.final_score())
        return observation, reward, done, info

    def state(self) -> dict:
        return {
            "task_id": self.task_id,
            "task_description": TASKS[self.task_id]["description"],
            "step": self.step_count,
            "max_steps": self.max_steps,
            "emails_processed": self.emails_processed,
            "time_elapsed": self.time_elapsed,
            "cumulative_score": self.cumulative_score,
            "current_email": self.current_email.model_dump(mode="json") if self.current_email else None,
            "processed_email_ids": sorted(self.processed_email_ids),
            "label_metadata": self.label_metadata,
            "action_history": self.action_history,
            "inbox": [email.model_dump(mode="json") for email in self.inbox],
        }

    def _get_next_email(self) -> Optional[Email]:
        for email in self.inbox:
            if email.id not in self.processed_email_ids:
                return email
        return None

    def _build_observation(self) -> EmailObservation:
        return EmailObservation(
            inbox=self.inbox,
            current_email=self.current_email,
            inbox_size=len(self.inbox),
            emails_processed=self.emails_processed,
            time_elapsed=self.time_elapsed,
            task_id=self.task_id,
            task_description=TASKS[self.task_id]["description"],
            step=self.step_count,
        )

    def _load_task_data(self) -> tuple[list[Email], dict]:
        if self.task_id == "task_1":
            return get_task1_inbox(), {}
        if self.task_id == "task_2":
            return get_task2_inbox()
        return get_task3_inbox(), {}

    def _invalid_action_penalty(self, action: EmailAction) -> float:
        if action.action_type == "reply" and not action.content:
            return -0.1
        if action.action_type == "label" and not action.label:
            return -0.1
        if action.action_type == "forward" and not action.forward_to:
            return -0.1
        if action.action_type == "snooze" and (action.snooze_hours is None or action.snooze_hours <= 0):
            return -0.1
        return 0.0
