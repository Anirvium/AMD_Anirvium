# Public Dataset Strategy For Hackathon Demo

## Principal Decision

Do not commit large public datasets into this repository.

Use Anirvium's anonymized source documents plus curated synthetic tickets as the primary demo corpus. Public datasets should be used only as optional benchmark/evaluation inputs, with license checks and source attribution.

This keeps the demo:

- domain-aligned,
- privacy-safe,
- deterministic,
- easy to push to GitHub,
- easy to run in the AMD notebook,
- free from dataset redistribution risk.

## Recommended Public Datasets

### 1. ABCD: Action-Based Conversations Dataset

Link: https://github.com/asappresearch/abcd

Use for:

- policy-constrained task-oriented support dialogue,
- action/state tracking eval cases,
- checking whether the agent follows multi-step procedures,
- benchmarking routing and next-action selection.

Why it matters:

ABCD is close to our product thesis: customer support interactions where agents must follow policies and actions rather than simply answer a question.

Recommended use:

- optional eval-only dataset,
- sample 20 to 50 conversations,
- convert to Anirvium eval cases,
- do not mix directly into the real customer-support KB.

### 2. Bitext Customer Support LLM Chatbot Training Dataset

Link: https://huggingface.co/datasets/bitext/Bitext-customer-support-llm-chatbot-training-dataset

Use for:

- intent taxonomy inspiration,
- response template contrast,
- synthetic paraphrase generation,
- broad customer-support phrasing.

Why it matters:

It has around 26.9k rows, CSV format, English language, intent/category labels, and a customer-support/chatbot focus.

Recommended use:

- optional seed for paraphrases and intent mapping,
- not a policy source,
- not final response truth.

### 3. TweetSumm

Link: https://github.com/guyfe/Tweetsumm

Use for:

- conversation summarization,
- memory compression evaluation,
- trajectory summarization benchmarks,
- testing whether agent memory preserves the issue, resolution, and pending action.

Why it matters:

It contains customer-care style Twitter dialogs with human extractive and abstractive summaries.

Recommended use:

- optional memory summarization benchmark,
- do not use raw Twitter-style text as product support policy.

### 4. Customer Support On Twitter

Link: https://www.kaggle.com/datasets/thoughtvector/customer-support-on-twitter

Use for:

- noisy public support interaction patterns,
- sentiment and escalation stress tests,
- public social-support style examples.

Risk:

Kaggle and Twitter/X-origin data can create redistribution and terms concerns. Do not commit raw data into the repo. Use only locally, and cite the dataset if used in experiments.

Recommended use:

- optional local-only benchmark,
- no raw import into GitHub.

### 5. FaithDial

Link: https://huggingface.co/datasets/McGill-NLP/FaithDial

Use for:

- hallucination/faithfulness evaluation,
- grounded response checking,
- critic-agent benchmark examples.

Why it matters:

FaithDial is not customer support specific, but it is useful for evaluating whether the assistant response stays grounded in supplied knowledge.

Recommended use:

- optional critic/evaluator benchmark,
- map examples into evidence-grounding evals.

### 6. CallCenterEN

Paper: https://arxiv.org/abs/2507.02958

Use for:

- future call-center transcript realism,
- call summary and memory compression research,
- language/tone stress tests.

Risk:

The paper states the dataset is CC BY-NC 4.0. That is fine for research, but not ideal for a reusable product repo or commercial-facing demo. Do not commit it into this repo.

Recommended use:

- research-only,
- local notebook experiments only,
- not part of the GitHub demo corpus.

## What We Should Keep In This Repo

Keep:

- curated synthetic support tickets,
- anonymized source-derived KB layers,
- eval cases generated from our anonymized source material,
- dataset manifest with links,
- ingestion scripts that can optionally load external datasets if the user downloads them separately.

Do not keep:

- raw Kaggle exports,
- raw Twitter-derived conversations,
- large Hugging Face dataset dumps,
- call-center transcript corpora with non-commercial terms,
- anything with unresolved license or PII risk.

## Exact Required Demo Dataset

For the AMD hackathon, the strongest demo corpus should contain:

1. 6 to 10 high-risk support tickets:
   - missing deposit,
   - processed withdrawal not received,
   - verification restriction,
   - bonus dispute,
   - cross-account access request,
   - priority customer asking for policy exception,
   - chat closure with pending next step,
   - Hindi/mixed-language withdrawal query.

2. 30 to 60 curated KB records:
   - policies,
   - procedures,
   - templates,
   - eval cases.

3. 10 to 20 trajectory memory examples:
   - prior run summaries,
   - repeated-customer memory,
   - policy failure memory,
   - successful resolution memory.

4. 10 to 20 retrieval benchmark queries:
   - expected KB evidence IDs,
   - expected memory hits,
   - expected policy gates.

5. 5 to 10 failure-mode eval cases:
   - unsafe refund promise,
   - verification bypass,
   - withdrawal limit disclosure,
   - unsupported bonus guarantee,
   - cross-account data leakage.

## Final Recommendation

Use our own anonymized + synthetic data as the primary demo.

Use public datasets only for:

- optional benchmark augmentation,
- summarization/memory evaluation,
- grounded response evaluation,
- intent taxonomy inspiration.

This gives judges a clean story: Anirvium does not depend on a generic chatbot dataset. It turns messy support operations knowledge into evidence-grounded trajectories, memory, policy gates, and improvement loops.
