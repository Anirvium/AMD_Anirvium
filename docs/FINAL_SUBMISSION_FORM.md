# Final ACT II Submission Form

Use this file as the copy-ready source for the lablab.ai form. Counts were validated against the published limits on 2026-07-12.

## Basic Information

### Submission title

**Anirvium AI: The Control Plane for AI Agents**

- Characters: **44 / 50**
- Minimum satisfied: yes

### Short description

**An evidence-backed control plane for AI agents: Sarvagun resolves support cases on AMD-hosted Qwen while SuperTuriya traces failures, evaluates decisions, and guides future plans.**

- Characters: **179 / 255**
- Minimum satisfied: yes

### Long description

AI support agents are entering payment, identity, refund, and escalation workflows, but most platforms show only a final answer. Support leaders cannot prove which evidence was used, which tool acted, whether policy was followed, or why the same failure returned.

Anirvium AI is a trajectory-intelligence control plane for enterprise agents. Sarvagun is its governed customer-support system. It routes each request to the lowest-complexity correct path: conversation, exact customer or case data, analytics, public knowledge, or a full support workflow. SuperTuriya observes the workflow end to end. It captures agent and tool spans, evidence, approval states, safe decision summaries, latency, risk, and model provenance. It scores each run, diagnoses failures, compares trajectories, and stores evaluated lessons for future planning. Memory is advisory and never rewrites policy automatically.

The live AMD path serves Qwen3-8B with vLLM and ROCm on AMD Developer Cloud. Qwen drafts responses and routed public-knowledge answers, while deterministic policy and compliance gates reject unsafe commitments and provide a safe fallback. The containerized product uses FastAPI and React, with SQLite operational truth, Redis short-term memory, Qdrant-compatible semantic memory, and ReactFlow trace visualization. All product data is synthetic and enterprise connectors are clearly simulated.

Our demo starts with a customer's third unresolved withdrawal complaint. Sarvagun retrieves linked case history and governed evidence, detects recontact and escalation risk, and holds sensitive claims for approval. SuperTuriya reveals the thirteen-step execution, identifies failure points, and recommends measurable workflow fixes.

The beachhead customer is a support or AI-operations leader deploying agents in regulated or SLA-sensitive workflows. Customer support is the first vertical; SuperTuriya can extend the same trajectory-intelligence pattern to other enterprise agents.

- Characters including paragraph breaks: **1,976 / 2,000**
- Words: **268**
- Minimum 100 words: satisfied
- Minimum 600 characters: satisfied

### Event track

**Track 3 — Unicorn Track**

### Recommended categories

Choose the closest options actually offered in the form:

- AI Agents
- AgentOps
- Customer Support
- Enterprise AI
- Business
- Web Application
- Developer Tools
- Utility and Tools

### Technologies used

Select only technologies that are available as form tags:

- AMD Developer Cloud
- AMD ROCm
- vLLM
- Qwen / Qwen3-8B
- Docker / Docker Compose
- Python
- FastAPI
- Pydantic
- React
- TypeScript
- Vite
- ReactFlow
- SQLite
- Redis
- Qdrant

Do **not** select Fireworks AI, Gemma, LangChain, CrewAI, AutoGen, or multimodal/vision technologies; they are not part of the verified implementation.

## Media

### Cover image

Upload:

```text
docs/assets/anirvium-cover-16x9.png
```

Verified aspect ratio: 16:9.

### Product presentation screens

Use in the slide deck and video:

```text
docs/assets/anirvium-main-ui-render.png
docs/assets/anirvium-superturiya-ui-render.png
```

These are presentation renders of the implemented interface, explicitly labelled as static synthetic demo renders. Do not call them live AMD screenshots.

### Video presentation

Prepared fallback asset:

```text
docs/assets/Anirvium_AI_ACT_II_Video.mp4
```

Verified media properties: **4 minutes 8 seconds**, **5.4 MB**, 1280×720 H.264 video with AAC narration. The narration truthfully describes the presentation renders and verified AMD evidence; it does not represent the slides as a live AMD screen recording.

Official guidance: maximum five minutes and under 300 MB. Upload this asset to the form or a publicly viewable platform, paste its URL if required, and verify playback in a private/incognito window.

### Slide presentation

Upload [Anirvium_AI_ACT_II_Deck.pptx](assets/Anirvium_AI_ACT_II_Deck.pptx). [FINAL_TEAM_PITCH_DECK.md](FINAL_TEAM_PITCH_DECK.md) is the approved narrative source. The PowerPoint has been rendered slide by slide, visually reviewed, and checked for canvas overflow. If the form requires a public URL rather than a file, upload it to a public slide platform and verify access without authentication.

## Technical Details

### Public GitHub repository

```text
https://github.com/Anirvium/AMD_Anirvium
```

Repository visibility was verified as public through GitHub metadata.

### Demo application platform

If GitHub Pages deployment is enabled and verified, enter:

```text
GitHub Pages — interactive static resilience demo; live model path validated on AMD Developer Cloud
```

Otherwise enter:

```text
AMD Developer Cloud + containerized Docker Compose reproduction
```

### Demo application URL

Target static resilience URL:

```text
https://anirvium.github.io/AMD_Anirvium/
```

**Do not submit this URL until it returns the product in a private/incognito browser.** The workflow is included in `.github/workflows/pages.yml`, but GitHub Pages may still need to be enabled under Repository Settings → Pages → Source: GitHub Actions.

Do not use the expired/private AMD Jupyter URL as the judge-facing application URL.

### Additional information

Anirvium AI uses synthetic support data and simulated enterprise connectors. The reproducible Docker path runs in deterministic mode; the AMD Developer Cloud path served Qwen3-8B through vLLM/ROCm for response drafting and routed public knowledge. SuperTuriya evaluates and stores advisory intelligence but never changes policy automatically. No official τ benchmark score is claimed. Full evidence and limitations are documented in `README.md`, `docs/PRODUCT_0_1.md`, and `amd/benchmark_results_real.md`.

## Final form gate

- [x] Title within limit
- [x] Short description within limit
- [x] Long description within limit and over 100 words
- [x] Track 3 selected
- [x] Technology tags are truthful
- [x] Cover image prepared
- [x] Public repository verified
- [x] MIT license added
- [x] Containerized reproduction documented
- [x] Video file prepared within duration and size limits
- [ ] Video uploaded/URL added and incognito-tested
- [ ] Slide URL/PDF uploaded and incognito-tested
- [ ] Application URL deployed and incognito-tested
- [ ] Final submission button completed before the platform deadline
