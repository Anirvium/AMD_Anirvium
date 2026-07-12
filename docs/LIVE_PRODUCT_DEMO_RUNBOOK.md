# Live Product Demo Runbook

## Recommended Demo Architecture

Use one browser-visible frontend URL. The frontend sends API calls to the same origin under `/api`; the local Vite server or Docker Nginx proxy forwards those requests to FastAPI.

```text
Judge browser -> frontend URL -> /api proxy -> FastAPI
                                      |
                                      -> deterministic demo or AMD/vLLM endpoint
```

This avoids exposing port 8000 to the browser and avoids the common mistake of using a remote notebook's `localhost` from a Mac browser.

## Run on a Mac Without Docker

Terminal 1:

```bash
cd backend
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Terminal 2:

```bash
cd frontend
npm install
npm run dev -- --host 127.0.0.1
```

Open:

```text
http://127.0.0.1:5173
```

Do not open the backend as the product UI. The frontend starts as a clean support conversation and proxies API requests through `/api`.

## Health Checks

Run these before opening the demo:

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/health/ready
curl http://127.0.0.1:5173/api/health
```

All three must succeed. If port 8000 is already in use, check it with the first health command before starting a second backend. If it returns the Anirvium health payload, reuse it.

## Run With Docker

```bash
docker compose up --build
```

Open only:

```text
http://127.0.0.1:5173
```

The Nginx container sends `/api/*` to the backend container. Judges do not need to open port 8000.

## AMD Demonstration Strategy

The complete judged product can run on the AMD Jupyter VM. The browser must use the AMD platform’s port-proxy URL; a Mac browser cannot open the VM’s raw `localhost`.

The required request path is:

```text
Safari on Mac
  → AMD port-proxy path /spaces/hf-415-81f7a8dd/8501/
  → production frontend gateway on VM port 8501
  → same-origin /api proxy
  → FastAPI on VM port 8000
  → vLLM/OpenAI-compatible Qwen on VM port 8001
```

The local Mac remains the editing, review, and Git push machine. GitHub is the synchronization boundary; the AMD VM pulls the tested commit and runs it.

## Run The Complete Product On The AMD VM

Keep vLLM on port `8001` and FastAPI on port `8000`. Run the production frontend gateway on port `8501` in a separate terminal:

```bash
cd /workspace/AMD_Anirvium/frontend
export FRONTEND_PORT=8501
export FRONTEND_HOST=0.0.0.0
export BACKEND_BASE_URL=http://127.0.0.1:8000
export FRONTEND_BASE_PATH=/spaces/hf-415-81f7a8dd/8501
npm ci
npm run serve:amd
```

Use `serve:amd` for the judged AMD runtime. It creates a production Vite build, serves relative static assets safely through notebook proxies, and forwards same-origin `/api` requests to `http://127.0.0.1:8000`. Do not use the Vite development server for the final notebook demo; its module and HMR paths can fail behind Jupyter proxies even when the HTML opens.

Verify inside the VM:

```bash
curl http://localhost:8501/api/health
curl http://localhost:8501/api/health/ready
curl -I http://localhost:8501
```

The health payload must report `"mode":"openai_compatible"` for the real AMD path.

Open this browser route for the current AMD instance:

```text
https://radeon-global.anruicloud.com/spaces/hf-415-81f7a8dd/8501/
```

If the instance ID changes, replace `hf-415-81f7a8dd`. The `/instances/<id>/lab` URL is the Jupyter workspace, not the frontend. Do not open `http://localhost:8501` on the Mac.

## Submission-Day AMD Restart

After the final commit is pushed from the Mac, use three AMD terminals in addition to the already-running vLLM terminal.

### AMD terminal 2 — synchronize and run FastAPI

```bash
cd /workspace/AMD_Anirvium
git status --short
git -c http.sslVerify=false fetch origin main
git merge --ff-only FETCH_HEAD
git log -1 --oneline

cd /workspace/AMD_Anirvium/backend
source .venv/bin/activate
export LLM_BASE_URL=http://localhost:8001/v1
export LLM_API_KEY=dummy
export LLM_MODEL=anirvium-text
export LLM_PROVIDER=openai_compatible
export AMD_RUNTIME_PROFILE=text_48gb
uvicorn app.main:app --host 0.0.0.0 --port 8000 --access-log --log-level info 2>&1 | tee /workspace/anirvium_backend.log
```

Use `http.sslVerify=false` only on this one fetch because the observed AMD image lacks the proxy CA chain. Do not save it as a global Git setting.

### AMD terminal 3 — build and run the production frontend

If the restarted notebook image has no Node/npm, install Node 20 once in that session:

```bash
cd /tmp
curl -fsSLO https://nodejs.org/dist/v20.20.2/node-v20.20.2-linux-x64.tar.xz
tar -xJf node-v20.20.2-linux-x64.tar.xz
cp -a node-v20.20.2-linux-x64/bin/. /usr/local/bin/
cp -a node-v20.20.2-linux-x64/lib/. /usr/local/lib/
hash -r
node --version
npm --version
```

Then start the frontend:

```bash
cd /workspace/AMD_Anirvium/frontend
hash -r
node --version
npm --version
export FRONTEND_PORT=8501
export FRONTEND_HOST=0.0.0.0
export BACKEND_BASE_URL=http://127.0.0.1:8000
export FRONTEND_BASE_PATH=/spaces/hf-415-81f7a8dd/8501
npm ci
npm run serve:amd 2>&1 | tee /workspace/anirvium_frontend.log
```

Node must be 20 or newer. The observed AMD VM now has Node `v20.20.2`, which is sufficient.

### AMD terminal 4 — verify the complete chain

```bash
curl -sS http://localhost:8001/v1/models
curl -sS http://localhost:8000/health
curl -sS http://localhost:8501/api/health
curl -sS http://localhost:8501/api/platform/status
curl -sS http://localhost:8501/api/data/cases/CS-002/context
curl -sS 'http://localhost:8501/api/tickets?dataset=customer_support'
curl -sS -X POST http://localhost:8501/api/conversations/turn \
  -H 'Content-Type: application/json' \
  -d '{"message":"Hi","customer_id":"CS-C002"}'
```

Only after all five checks succeed should the browser be opened. In Safari, use `Option + Command + R` to reload without the normal page cache after a new frontend build.

## Collect Correlated Logs On AMD

FastAPI terminal:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --access-log --log-level info 2>&1 | tee /workspace/anirvium_backend.log
```

Frontend terminal:

```bash
cd /workspace/AMD_Anirvium/frontend
npm run serve:amd 2>&1 | tee /workspace/anirvium_frontend.log
```

The gateway logs every browser and API request. FastAPI adds `X-Request-ID`, `X-Correlation-ID`, and `X-Response-Time-MS` headers and logs the same identifiers through queued jobs, agent steps, and model calls. The vLLM terminal shows each `/v1/chat/completions` call.

Browser diagnostics:

1. Open Developer Tools, then **Console**. Filter for `Anirvium API`.
2. Open **Network**, enable **Preserve log**, and reload.
3. Export a HAR file or capture failed `/api/*` rows, status codes, response bodies, and request IDs.

Collect files for debugging:

```bash
tail -n 200 /workspace/anirvium_frontend.log
tail -n 200 /workspace/anirvium_backend.log
```

The judged UI uses `POST /runs/async` and polls `/runs/jobs/{job_id}`. Each job exposes the actual current agent, current step, total steps, and progress percentage. The browser persists the active job ID and resumes it after refresh. Transient `429`, `502`, `503`, and `504` polling responses are retried while the server-side job continues. Completed Sarvagun execution, SuperTuriya intelligence, spans, CX signals, audited tools, and memory IDs arrive with the final result.

## Judge Demo Sequence

1. Open the dashboard and verify the sidebar says **AMD model ready**.
2. Type `Hi` and show Sarvagun’s fast backend conversation response.
3. Select `CS-002`, choose **Hybrid governed**, and submit the third-contact withdrawal prompt from the demo script.
4. Show emotion, recontact, incident, escalation, and AI-predicted satisfaction.
5. Expand provenance to show evidence, audited mock tool executions, assurance, and transcript.
6. Show the safe response and its human-review state; do not describe an approval-required draft as sent.
7. Follow the 13 real server-side steps: the first nine are Sarvagun, the final four are SuperTuriya.
8. Open SuperTuriya and show events observed, memories recalled/applied/created, scorecard, diagnosis, and improvement recommendation.
9. Compare two stored runs through `/runs/compare` and explain the safety-aware verdict.
10. Submit explicit CSAT only for a released response and point out that it remains separate from predicted satisfaction.
11. Show the vLLM terminal’s real `/v1/chat/completions` activity and AMD model identity.

Keep a prerecorded screen capture of the same sequence as the fallback.

## Hosting for Submission

The hackathon requires an application URL, public GitHub repository, video presentation, slide presentation, containerization, and runnable instructions. A localhost URL is not a submission URL.

Deploy the Dockerized frontend/backend to any public container host that supports two services, or deploy them as one service with Nginx proxying `/api`. Keep mock mode as the public default so judges do not depend on private credentials or GPU availability.

Before submission, test the public URL in an incognito browser and on a phone using mobile data. This proves it does not rely on local processes, cached credentials, or your Wi-Fi network.

## Failure Checklist

- Blank page: inspect the frontend terminal and run `npm run build`.
- “Backend unavailable”: verify `curl http://127.0.0.1:8000/health`.
- Frontend loads but no data: verify `curl http://127.0.0.1:5173/api/health`.
- AMD model degraded: verify `curl http://localhost:8001/v1/models` and `curl http://localhost:8501/api/health/ready`.
- A browser shows a transient 502 during a run: leave the backend running and reload once; the persisted job ID resumes automatically.
- Port 8000 already used: reuse a healthy Anirvium backend or stop the unrelated process.
- Port 5173 already used: use the URL Vite prints, or stop the old Vite process.
- Remote notebook works only inside notebook: use an approved tunnel/public proxy or keep AMD as separate evidence.
- Public deployment calls visitor localhost: rebuild with `VITE_API_BASE_URL=/api` and use the same-origin proxy.
