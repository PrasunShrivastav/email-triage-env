---
title: Email Triage Env
emoji: 📧
colorFrom: blue
colorTo: green
sdk: docker
pinned: false
---

# 📧 Email Triage Environment

> **A real-world OpenEnv environment for training and evaluating AI agents on email triage, prioritization, and customer support.**

[![OpenEnv Compatible](https://img.shields.io/badge/OpenEnv-compatible-4B8BBE?style=flat-square&logo=python&logoColor=white)](https://openenv.dev)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Docker Ready](https://img.shields.io/badge/Docker-ready-2496ED?style=flat-square&logo=docker&logoColor=white)](https://www.docker.com/)
[![HF Space Live](https://img.shields.io/badge/HF%20Space-live-FF9D00?style=flat-square&logo=huggingface&logoColor=white)](https://huggingface.co/spaces/PrasunPragya/email-triage-env)

---

## 🌍 Motivation & Real-World Value

Email triage is one of the most universally applicable benchmarks for AI agents. Unlike narrow coding challenges or arcade games, every knowledge worker — regardless of domain — spends meaningful time managing their inbox. A capable agent must read, classify, prioritize, and often compose professional responses, all within a single coherent workflow. This makes email triage a uniquely rich test of multi-skill reasoning: it combines natural language understanding, contextual judgment, urgency detection, and communication quality in one realistic environment.

This environment directly tests the skills that matter for autonomous agents in the real world. **Reading comprehension** is required to understand email intent from minimal context. **Categorization** demands distinguishing spam from legitimate work at a glance. **Urgency detection** requires reasoning about time sensitivity and business impact. **Professional writing** — the ability to generate empathetic, accurate, and concise customer support replies — tests open-ended generation quality at a level that rule-based evaluators cannot capture.

Most existing agent benchmarks focus on games (Atari, NetHack), code generation (SWE-bench, HumanEval), or narrow Q&A tasks. Communication benchmarks — especially those evaluating multi-step, stateful inbox management — remain extremely underrepresented. This environment fills that gap by providing a reproducible, scalable, and grader-verified OpenEnv environment that closely mirrors tasks agents will be deployed on in production.

---

## 🗺️ Environment Overview

| Property | Value |
|---|---|
| **Observation Space** | `EmailObservation` (inbox, current_email, step, task metadata) |
| **Action Space** | `EmailAction` (9 action types) |
| **Reward Range** | `(0.0, 1.0)` continuous |
| **Episodes** | 3 tasks, up to 30 steps each |
| **Reproducibility** | Seeded with `seed=42` |
| **Transport** | REST/JSON over HTTP (OpenEnv standard) |
| **Deployment** | Docker / Hugging Face Spaces |

---

## 👁️ Observation Space

### `EmailObservation` Fields

| Field | Type | Description |
|---|---|---|
| `inbox` | `List[Email]` | Full inbox for the current episode |
| `current_email` | `Optional[Email]` | The email the agent must act on at this step |
| `inbox_size` | `int` | Total number of emails in the episode inbox |
| `emails_processed` | `int` | Number of emails already acted on |
| `time_elapsed` | `float` | Simulated minutes elapsed in the episode |
| `task_id` | `str` | Active task identifier (`task_1`, `task_2`, `task_3`) |
| `task_description` | `str` | Human-readable description of the active task |
| `step` | `int` | Current environment step count |

### `Email` Model Fields

| Field | Type | Description |
|---|---|---|
| `id` | `str` | Unique email identifier (e.g., `task1_email_01`) |
| `sender` | `str` | Sender name or address |
| `subject` | `str` | Email subject line |
| `body` | `str` | Full email body text |
| `timestamp` | `str` | ISO 8601 timestamp when the email was received |
| `is_spam` | `Optional[bool]` | Ground-truth spam label (used by grader) |
| `category` | `Optional[str]` | Ground-truth category label (used by grader) |
| `is_urgent` | `Optional[bool]` | Ground-truth urgency flag (used by grader) |
| `thread_id` | `Optional[str]` | Thread identifier for email chains |

---

## ⚡ Action Space

| `action_type` | Description | Required Fields |
|---|---|---|
| `reply` | Send a written response to the email sender | `email_id`, `content` |
| `archive` | Move email out of inbox without deleting | `email_id` |
| `delete` | Permanently remove the email | `email_id` |
| `flag` | Mark email for follow-up attention | `email_id` |
| `label` | Assign a category label | `email_id`, `label` |
| `mark_urgent` | Flag email as time-sensitive or critical | `email_id` |
| `forward` | Forward email to another recipient | `email_id`, `forward_to` |
| `snooze` | Hide email temporarily for later | `email_id`, `snooze_hours` |
| `skip` | Take no action and move to the next email | `email_id` |

**Available labels for `label` action:**

| Label | Use When |
|---|---|
| `spam` | Unsolicited, irrelevant, or scam emails |
| `urgent_work` | Time-sensitive work items requiring immediate attention |
| `meeting_request` | Invitations, scheduling, or calendar requests |
| `invoice` | Billing, payment, or financial documents |
| `newsletter` | Subscriptions, announcements, or mailing lists |
| `personal` | Non-work personal correspondence |

---

## 📋 Tasks

### Task 1: Spam Cleanup 🟢 Easy

**Objective:** Clean the inbox by deleting spam and archiving legitimate email — without accidentally destroying anything important.

**Inbox composition:** 10 emails — 6 spam, 4 legitimate

**Grader formula:**
```
episode_score = (correct_spam_removed / 6) * 0.7 + (legitimate_kept / 4) * 0.3
```

**What makes it easy:** Spam emails contain highly identifiable signals — lottery win notifications, pill/medication offers, inheritance scams, prize claims, and unsolicited job offers. Legitimate emails are clearly from known contacts or contain recognizable content (bills, project updates, personal messages).

**Expected agent score:** ~0.75 (strong LLMs reliably identify obvious spam)

---

### Task 2: Priority Inbox Sorting 🟡 Medium

**Objective:** Label every email with the correct category AND identify the 3 most critical emails as urgent.

**Inbox composition:** 15 emails spread across all 6 label categories, with 3 marked as truly urgent.

**Grader formula:**
```
episode_score = (correct_labels / 15) * 0.6 + (correct_urgent / 3) * 0.4
```

**What makes it medium:** Many emails require reading body context — not just the subject line — to determine whether a `meeting_request` is also `urgent_work`, or whether an `invoice` actually escalated. Keyword-only approaches fail on ambiguous cases.

**Expected agent score:** ~0.55 (labeling is decent but urgency detection weak without reasoning)

---

### Task 3: Customer Support Response 🔴 Hard

**Objective:** Reply to all customer support emails with professional, empathetic, and accurate responses.

**Inbox composition:** 8 customer emails including 2 thread follow-ups referencing prior interactions.

**Grader:** LLM-as-judge scoring on 4 criteria (each 0.0–1.0, averaged):
| Criterion | What it measures |
|---|---|
| **Relevance** | Does the reply address the customer's actual issue? |
| **Tone** | Is the response professional, warm, and empathetic? |
| **Completeness** | Are next steps, solutions, or acknowledgments included? |
| **Accuracy** | Does the reply avoid misleading or incorrect information? |

**What makes it hard:** Generating high-quality replies requires understanding the customer's problem, referencing thread history for follow-ups, using an appropriate register, and providing actionable resolution — all within a concise response. Short or generic replies score poorly.

**Expected agent score:** ~0.40 (requires careful, context-aware generation)

---

## 🎯 Reward Design

Reward shaping is a first-class concern in this environment. The philosophy:

- **Dense rewards, not sparse:** Every step returns a real reward signal. Agents are not left guessing until episode end — each action on a spam, label, or support reply generates immediate feedback.

- **Partial credit:** Rewards are continuous in `(0.0, 1.0)`. A partially correct label earns more than a wrong one. A decent reply earns more than no reply at all.

- **Penalties for destructive mistakes:** Deleting or archiving a legitimate email in Task 1 triggers a negative step reward. Mislabeling and urgency errors are penalized proportionally.

- **Time penalties for inefficiency:** Steps beyond 20 incur a small per-step deduction, encouraging agents to act decisively rather than stalling with `skip` actions.

- **LLM-as-judge for open-ended generation:** Task 3 replies cannot be evaluated with string matching. A judge LLM scores each reply on the four criteria above — the only principled way to measure free-text communication quality.

- **Bounded outputs:** All scores are strictly within `(0.01, 0.99)` — never exactly `0` or `1` — to ensure numerical safety for downstream training pipelines.

---

## 🚀 Quick Start

### Local

```bash
git clone https://github.com/PrasunShrivastav/email-triage-env
cd email-triage-env
pip install -r requirements.txt
uvicorn app.server:app --host 0.0.0.0 --port 7860
```

### Docker

```bash
docker build -t email-triage-env .
docker run -p 7860:7860 \
  -e API_BASE_URL=https://api.openai.com/v1 \
  -e MODEL_NAME=gpt-4o-mini \
  -e HF_TOKEN=your_token \
  email-triage-env
```

### Run Inference

```bash
export API_BASE_URL=https://api.openai.com/v1
export MODEL_NAME=gpt-4o-mini
export HF_TOKEN=your_key
export ENV_BASE_URL=http://localhost:7860
python3 inference.py
```

### Hugging Face Spaces

Set Space Secrets: `API_BASE_URL`, `MODEL_NAME`, `HF_TOKEN` — the Space auto-deploys on push.

---

## 📡 API Reference

### `GET /health`

Returns service health status.

```bash
curl http://localhost:7860/health
# {"status":"ok","environment":"email-triage-env"}
```

---

### `GET /tasks`

Lists all available tasks with metadata.

```bash
curl http://localhost:7860/tasks
# {"tasks": [{"id":"task_1","name":"Spam Cleanup","difficulty":"easy"}, ...]}
```

---

### `POST /reset?task_id=task_1`

Initializes a new episode for the given task. Returns a `session_id` and the initial observation.

```bash
curl -X POST "http://localhost:7860/reset?task_id=task_1"
# {"session_id":"abc123","observation":{...}}
```

---

### `POST /step?session_id=xxx`

Submits one action for the current step. Returns reward, done flag, and next observation.

```bash
curl -X POST "http://localhost:7860/step?session_id=abc123" \
  -H "Content-Type: application/json" \
  -d '{
    "action_type": "delete",
    "email_id": "task1_email_01"
  }'
# {"reward":{"score":0.85},"done":false,"observation":{...}}
```

**Example `label` action:**
```bash
curl -X POST "http://localhost:7860/step?session_id=abc123" \
  -H "Content-Type: application/json" \
  -d '{
    "action_type": "label",
    "email_id": "task2_email_07",
    "label": "urgent_work"
  }'
```

**Example `reply` action:**
```bash
curl -X POST "http://localhost:7860/step?session_id=abc123" \
  -H "Content-Type: application/json" \
  -d '{
    "action_type": "reply",
    "email_id": "task3_email_03",
    "content": "Thank you for reaching out. I have reviewed your case and ..."
  }'
```

---

### `GET /state?session_id=xxx`

Returns the full current state for an active session.

```bash
curl "http://localhost:7860/state?session_id=abc123"
# {"session_id":"abc123","observation":{...},"step":4,"done":false}
```

---

### `GET /validate`

Runs a lightweight end-to-end environment validation check. Used by the OpenEnv automated validator.

```bash
curl http://localhost:7860/validate
# {"status":"ok","tasks_validated":3,"all_scores_in_range":true}
```

---

## 📊 Baseline Scores

| Task | Difficulty | Model | Score | Notes |
|------|-----------|-------|-------|-------|
| Spam Cleanup | Easy | Qwen2.5-72B | 0.110 | Correctly identifies spam patterns |
| Priority Sorting | Medium | Qwen2.5-72B | 0.114 | Good labeling with urgency detection |
| Customer Support | Hard | Qwen2.5-72B | 0.160 | LLM-as-judge rewards quality replies |
| **Mean** | | | **0.128** | Reproducible with inference.py |

---

## 🗂️ Project Structure

```
email-triage-env/
│
├── app/                        # Core environment package
│   ├── __init__.py
│   ├── server.py               # FastAPI app — all HTTP endpoints
│   ├── environment.py          # Session management & step logic
│   ├── models.py               # Pydantic models: Email, EmailObservation, EmailAction
│   ├── email_generator.py      # Deterministic synthetic email factory (seed=42)
│   └── tasks.py                # Task registry + per-task graders
│
├── inference.py                # Baseline LLM agent (task-specific prompts)
├── requirements.txt            # Runtime Python dependencies
├── pyproject.toml              # Project metadata
├── Dockerfile                  # Container build for HF Spaces / Docker
├── openenv.yaml                # OpenEnv environment descriptor
└── README.md                   # This file
```

---

## Evaluation Philosophy

This environment is designed so that **scores reflect genuine agent capability**:

- A random agent scores ~0.05 (near zero, not zero — avoids sparse reward problems)
- A rule-based agent scores ~0.11–0.16 (current baseline)  
- A strong reasoning agent should score 0.4–0.7
- A perfect agent scores ~0.95 (capped below 1.0 for numerical stability)

This scoring range means the environment **discriminates well** between weak and 
strong agents — exactly what a good benchmark should do.

---

## 🧠 Design Decisions

### Why Email Triage?

Email is a universal, high-stakes communication medium. Unlike toy benchmarks, an agent that masters email triage is immediately useful: it can handle inbox zero, route customer support tickets, flag urgent issues, and draft replies autonomously. The tasks in this environment directly mirror real-world workflows.

### Why LLM-as-Judge for Task 3?

Customer support replies are open-ended — there is no single "correct" answer. Traditional metrics like BLEU or exact match fail catastrophically on free-text generation. An LLM judge evaluating on semantic dimensions (relevance, tone, completeness, accuracy) is far more aligned with what humans actually care about. This is the same approach used by state-of-the-art evaluation systems like MT-Bench and AlpacaEval.

### Why `seed=42`?

Reproducibility is not optional for agent benchmarks. Every researcher running inference should get the same inbox, same email ordering, and same ground-truth labels. A fixed seed ensures that score differences between agents reflect true capability differences — not randomness in environment generation.

### Why Partial / Dense Rewards?

Sparse rewards — where the agent only learns at episode end — slow convergence and make credit assignment nearly impossible for multi-step tasks. Partial rewards at every step give the agent immediate feedback on each action, enabling faster learning and richer gradient signal for reinforcement learning pipelines. This is consistent with reward shaping best practices in the RL literature.

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.
