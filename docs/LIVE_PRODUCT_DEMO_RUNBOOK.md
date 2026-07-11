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

The private AMD notebook should not be the only frontend host. Notebook `localhost` is private to the notebook machine.

Use two proof paths:

1. **Live product UX:** local or hosted frontend plus deterministic backend. This must be stable and fast.
2. **AMD proof:** a short recorded/live segment showing the AMD device, vLLM/ROCm server, model endpoint, and benchmark output.

If a secure tunnel or public deployment is available, the backend can use the AMD endpoint. Otherwise, do not risk the main product demo on notebook networking. Clearly disclose that the UI demo is deterministic and the separate benchmark proves the AMD inference path.

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

The gateway logs every browser and API request. FastAPI adds `X-Request-ID` and `X-Response-Time-MS` headers and logs the same request lifecycle. The vLLM terminal shows each `/v1/chat/completions` call.

Browser diagnostics:

1. Open Developer Tools, then **Console**. Filter for `Anirvium API`.
2. Open **Network**, enable **Preserve log**, and reload.
3. Export a HAR file or capture failed `/api/*` rows, status codes, response bodies, and request IDs.

Collect files for debugging:

```bash
tail -n 200 /workspace/anirvium_frontend.log
tail -n 200 /workspace/anirvium_backend.log
```

The judged UI uses `POST /runs/async` and polls `/runs/jobs/{job_id}`. Each job exposes the actual current agent, current step, total steps, and progress percentage. The browser persists the active job ID and resumes it after refresh. Transient `429`, `502`, `503`, and `504` polling responses are retried while the server-side job continues. Completed spans and their full outputs arrive with the final result.

## Judge Demo Sequence

1. Open the dashboard and verify the sidebar says **AMD model ready**.
2. Select one high-risk payment/security case or click a prompt chip.
3. Submit the customer request.
4. Show the trajectory steps and tool/evidence trace.
5. Show the policy gate and human handoff.
6. Show the safe, cited final response.
7. Show the scorecard, diagnosed failure, and optimizer recommendation.
8. Switch to the AMD evidence slide/clip and show the real vLLM/ROCm run.

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
