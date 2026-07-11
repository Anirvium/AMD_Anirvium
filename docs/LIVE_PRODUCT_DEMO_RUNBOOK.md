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

Do not open the backend as the product UI. The frontend automatically loads the curated support demo and proxies API requests through `/api`.

## Health Checks

Run these before opening the demo:

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:5173/api/health
curl http://127.0.0.1:5173/api/demo/customer-support-run
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

## Judge Demo Sequence

1. Open the dashboard and show that a live run is loaded.
2. Select the high-risk payment/security cases.
3. Click **Run selected cases**.
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
- Port 8000 already used: reuse a healthy Anirvium backend or stop the unrelated process.
- Port 5173 already used: use the URL Vite prints, or stop the old Vite process.
- Remote notebook works only inside notebook: use an approved tunnel/public proxy or keep AMD as separate evidence.
- Public deployment calls visitor localhost: rebuild with `VITE_API_BASE_URL=/api` and use the same-origin proxy.
