# ACT II Final Submission Checklist

Status reflects the repository release working tree on 2026-07-13. Items requiring an external platform action remain unchecked.

## Official eligibility and form

- [ ] Team registration and eligibility were completed before the event cutoff.
- [ ] Every team member is registered as required by lablab.ai.
- [x] Track selected: **Track 3 — Unicorn Track**.
- [x] Submission title is within 50 characters.
- [x] Short description is within 255 characters and over the minimum.
- [x] Long description is within 2,000 characters, over 600 characters, and over 100 words.
- [x] Truthful category and technology tags are prepared.
- [ ] Final form is submitted before the platform deadline shown to the team.

## Code, license, and reproducibility

- [x] Public repository: `https://github.com/Anirvium/AMD_Anirvium`.
- [x] MIT license exists.
- [x] Backend and frontend Dockerfiles exist.
- [x] `docker-compose.yml` starts frontend, backend, Redis, and Qdrant.
- [x] README contains setup and usage instructions.
- [x] Deterministic synthetic-data mode works without private credentials.
- [x] GitHub CI runs backend and frontend checks.
- [x] Final CI adds a complete Docker Compose smoke test.
- [ ] Final pushed commit CI is green.
- [ ] Clean-machine `docker compose up --build` is independently reproduced or the final CI smoke job is green.

## Product verification

- [x] Backend suite: **95 passed**.
- [x] Normal frontend production build passes.
- [x] Static resilience frontend production build passes.
- [x] Frontend/API same-origin proxy is implemented for Vite, Nginx, and AMD gateway paths.
- [x] Typed routing covers greetings, exact customer/case reads, analytics, public knowledge, and governed support.
- [x] Sarvagun produces nine governed execution spans.
- [x] SuperTuriya produces four intelligence spans.
- [x] Asynchronous jobs expose recoverable progress polling.
- [x] SQLite, Redis/local fallback, and Qdrant/local fallback roles are separated.
- [x] Trace graph, metrics, diagnosis, recommendations, and memory IDs are visible.
- [x] Sensitive response states are held for human review.
- [x] Simulated connectors are labelled.
- [x] `/platform/status` exposes model/storage/benchmark truth.
- [x] `/data/cases/CS-002/context` exposes linked synthetic context.
- [x] `/runs/compare` compares persisted trajectories.

## AMD evidence

- [x] Qwen3-8B was served through vLLM/ROCm on AMD Developer Cloud.
- [x] Live backend used the OpenAI-compatible AMD model endpoint.
- [x] Human-readable measured results are committed in `amd/benchmark_results_real.md`.
- [x] Observed 47.98 GiB / `gfx1100` runtime is distinguished from the 192GB target profile.
- [x] No Fireworks, Gemma, MI300X result, or official τ score is falsely claimed.
- [ ] Optional raw AMD logs or authentic AMD screenshots are attached externally if the team retained them.

## Media and public demo

- [x] 16:9 cover image exists.
- [x] Sarvagun presentation render exists.
- [x] SuperTuriya presentation render exists.
- [x] Presentation renders disclose that they are static and not live AMD screenshots.
- [x] Ten-slide PowerPoint exists and passed slide-by-slide visual and canvas-overflow QA.
- [x] Narrated fallback MP4 is prepared at 4:08 and 5.4 MB.
- [ ] Video presentation is uploaded/public and incognito-tested.
- [ ] `docs/assets/Anirvium_AI_ACT_II_Deck.pptx` is attached/uploaded and incognito-tested if a public URL is required.
- [x] GitHub Pages resilience workflow exists.
- [ ] GitHub Pages is enabled and `https://anirvium.github.io/AMD_Anirvium/` is incognito-tested.
- [ ] Final application URL is entered in the form.

## Security, privacy, and claims

- [x] No secret credential pattern was found in tracked files.
- [x] `.env.example` contains placeholders only.
- [x] Product operational data is synthetic.
- [x] Specific wallet/payment identifiers found in reference material were redacted.
- [x] Raw reference material is excluded from runtime retrieval.
- [ ] Team confirms it has rights to redistribute all team-supplied anonymized reference material.
- [x] Prototype/production boundaries are explicit.
- [x] SuperTuriya memory is described as evaluated and advisory, not automatic self-modification.

## Recommended final external sequence

1. Push the final commit.
2. Wait for CI and Pages workflows.
3. If Pages fails because the site is disabled, choose Repository Settings → Pages → Source: GitHub Actions and rerun the workflow.
4. Open repository, Pages URL, slides, and video in a private/incognito window.
5. Paste the exact copy from `docs/FINAL_SUBMISSION_FORM.md`.
6. Submit and save the confirmation page.
