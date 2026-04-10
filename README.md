# Email Triage Environment

## Overview
Email triage is a strong real-world evaluation domain because it combines judgment, speed, and communication quality in a workflow that many agents will eventually need to support. A capable system has to separate noise from signal, understand intent from messy inbox data, and take the right action with limited room for error.

This environment evaluates multiple agent skills inside a single interface. It includes inbox classification, priority handling, and customer-facing response generation, which makes it more representative than narrow benchmark tasks that measure only one behavior at a time.

Because the environment is stateful and step-based, it is also useful for testing decision sequences rather than isolated answers. Agents must act consistently across an episode, preserve important emails, and generate helpful replies when language quality matters.

## Observation Space
| Field | Type | Description |
|------|------|-------------|
| `inbox` | `List[Email]` | Full inbox for the current episode. |
| `current_email` | `Optional[Email]` | Email the agent should act on at the current step. |
| `inbox_size` | `int` | Total number of emails in the episode inbox. |
| `emails_processed` | `int` | Number of emails already acted on in the episode. |
| `time_elapsed` | `float` | Simulated minutes elapsed so far. |
| `task_id` | `str` | Active task identifier. |
| `task_description` | `str` | Human-readable description of the active task. |
| `step` | `int` | Current environment step count. |

## Action Space
| Field | Type | Required | Description |
|------|------|----------|-------------|
| `action_type` | `str` | Yes | Action to take on the current email. Valid values: `reply`, `archive`, `delete`, `flag`, `label`, `forward`, `mark_urgent`, `snooze`, `skip`. |
| `email_id` | `str` | Yes | Target email identifier. Must match `current_email.id` for best results. |
| `content` | `Optional[str]` | Only for `reply` | Reply text sent to the customer or sender. |
| `label` | `Optional[str]` | Only for `label` | Category label to assign. Typical values: `spam`, `urgent_work`, `meeting_request`, `invoice`, `newsletter`, `personal`. |
| `forward_to` | `Optional[str]` | Only for `forward` | Email address to forward the message to. |
| `snooze_hours` | `Optional[int]` | Only for `snooze` | Number of hours to snooze the email. |

Valid `action_type` values:

- `reply`: Send a written response to the current email.
- `archive`: Remove the email from the active inbox without deleting it.
- `delete`: Remove the email as unwanted or resolved.
- `flag`: Mark the email for follow-up or attention.
- `label`: Apply a category label.
- `forward`: Forward the email to another recipient.
- `mark_urgent`: Mark the email as urgent.
- `snooze`: Hide the email temporarily until later.
- `skip`: Take no substantive action and move on.

## Tasks

### Task 1: Spam Cleanup (Easy)
- Objective: Delete or archive obvious spam while preserving legitimate email.
- Success criteria: Remove spam accurately and avoid destructive actions on legitimate messages.
- Scoring formula: Per-step rewards favor destructive actions on spam and penalize destructive actions on legitimate mail. Episode score is `correct_spam_removed/6 * 0.7 + legitimate_kept/4 * 0.3`.
- Expected baseline score: ~0.70

### Task 2: Priority Inbox Sorting (Medium)
- Objective: Label all emails by category and mark the truly urgent work items.
- Success criteria: Apply correct labels across the inbox and correctly mark the three `urgent_work` emails.
- Scoring formula: Correct labels earn the strongest step reward, incorrect labels receive small partial credit, incorrect urgent flags are penalized, and the episode score is `(correct_labels/15 * 0.6) + (correct_urgent/3 * 0.4)`.
- Expected baseline score: ~0.55

### Task 3: Customer Support Response (Hard)
- Objective: Reply to customer support emails with clear, helpful, and appropriate responses.
- Success criteria: Respond with replies that address the issue, maintain a professional tone, and avoid misleading promises.
- LLM-as-judge rubric explanation: Each reply is scored on relevance, tone, completeness, and accuracy from `0.0` to `1.0`. The mean score drives the per-step reward, and missing or very short replies underperform by design.
- Expected baseline score: ~0.40

## Setup & Usage

### Local Development
```bash
pip install -r requirements.txt
uvicorn app.server:app --host 0.0.0.0 --port 7860
```

### Docker
```bash
docker build -t email-triage-env .
docker run -p 7860:7860 \
  -e API_BASE_URL=your_api_base \
  -e MODEL_NAME=your_model \
  -e HF_TOKEN=your_token \
  email-triage-env
```

### Running Inference
```bash
export API_BASE_URL=https://api.openai.com/v1
export MODEL_NAME=gpt-4o-mini
export HF_TOKEN=your_key_here
export ENV_BASE_URL=http://localhost:7860
python3 inference.py
```

### Hugging Face Spaces
- Set Space Secrets: `API_BASE_URL`, `MODEL_NAME`, `HF_TOKEN`
- Space auto-deploys on push

## API Reference

### `GET /health`
Returns a simple service health payload.

```bash
curl http://localhost:7860/health
```

### `GET /tasks`
Lists the available task registry entries.

```bash
curl http://localhost:7860/tasks
```

### `POST /reset`
Creates or resets a session for a task and returns the initial observation.

```bash
curl -X POST "http://localhost:7860/reset?task_id=task_1"
```

### `POST /step`
Applies one action to the current session state.

```bash
curl -X POST "http://localhost:7860/step?session_id=your_session_id" \
  -H "Content-Type: application/json" \
  -d '{"action_type":"delete","email_id":"task1_email_01"}'
```

### `GET /state`
Returns the full current state for a session.

```bash
curl "http://localhost:7860/state?session_id=your_session_id"
```

### `GET /validate`
Runs a lightweight validation check for environment setup and task loadability.

```bash
curl http://localhost:7860/validate
```

## Baseline Scores
| Task | Difficulty | Model | Score |
|------|-----------|-------|-------|
| task_1 | Easy | gpt-4o-mini | TBD |
| task_2 | Medium | gpt-4o-mini | TBD |
| task_3 | Hard | gpt-4o-mini | TBD |

## Environment Details
- Max steps per episode: 30
- Reward range: 0.0 – 1.0
- Reproducible with seed=42
- Sessions are stateful (pass `session_id` to `/step` and `/state`)
