import { createReadStream, existsSync, statSync } from "node:fs";
import { createServer, request as proxyRequest } from "node:http";
import { extname, join, normalize } from "node:path";
import { fileURLToPath } from "node:url";

const host = process.env.FRONTEND_HOST ?? "0.0.0.0";
const port = Number(process.env.FRONTEND_PORT ?? 5173);
const backend = new URL(process.env.BACKEND_BASE_URL ?? "http://127.0.0.1:8000");
const root = join(fileURLToPath(new URL(".", import.meta.url)), "dist");
const configuredBasePath = process.env.FRONTEND_BASE_PATH ?? process.env.STREAMLIT_SERVER_BASE_URL_PATH ?? "";
const basePath = configuredBasePath === "/" ? "" : configuredBasePath.replace(/\/$/, "");

const contentTypes = {
  ".css": "text/css; charset=utf-8",
  ".html": "text/html; charset=utf-8",
  ".ico": "image/x-icon",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".png": "image/png",
  ".svg": "image/svg+xml",
  ".webp": "image/webp"
};

function routedUrl(rawUrl = "/") {
  if (!basePath) return rawUrl;
  if (rawUrl === basePath) return "/";
  if (rawUrl.startsWith(`${basePath}/`)) return rawUrl.slice(basePath.length) || "/";
  return rawUrl;
}

function proxyApi(req, res, route) {
  const upstreamPath = route.replace(/^\/api/, "") || "/";
  const upstream = proxyRequest({
    hostname: backend.hostname,
    port: backend.port || 80,
    path: upstreamPath,
    method: req.method,
    headers: { ...req.headers, host: backend.host }
  }, (upstreamResponse) => {
    res.writeHead(upstreamResponse.statusCode ?? 502, upstreamResponse.headers);
    upstreamResponse.pipe(res);
  });
  upstream.setTimeout(300_000, () => upstream.destroy(new Error("Backend request timed out")));
  upstream.on("error", (error) => {
    console.error(`[frontend-gateway] ${req.method} ${req.url} failed`, error.message);
    if (!res.headersSent) res.writeHead(502, { "content-type": "application/json" });
    res.end(JSON.stringify({ detail: "Backend unavailable through frontend gateway" }));
  });
  req.pipe(upstream);
}

function serveFile(route, res) {
  const rawPath = decodeURIComponent(new URL(route, "http://localhost").pathname);
  const safePath = normalize(rawPath).replace(/^(\.\.(\/|\\|$))+/, "");
  let filePath = join(root, safePath === "/" ? "index.html" : safePath);
  if (!filePath.startsWith(root) || !existsSync(filePath) || statSync(filePath).isDirectory()) {
    filePath = join(root, "index.html");
  }
  res.writeHead(200, {
    "content-type": contentTypes[extname(filePath)] ?? "application/octet-stream",
    "cache-control": filePath.endsWith("index.html") ? "no-cache" : "public, max-age=31536000, immutable"
  });
  createReadStream(filePath).pipe(res);
}

createServer((req, res) => {
  const started = Date.now();
  res.on("finish", () => console.info(`[frontend-gateway] ${req.method} ${req.url} ${res.statusCode} ${Date.now() - started}ms`));
  const route = routedUrl(req.url);
  if (route === "/api" || route.startsWith("/api/")) proxyApi(req, res, route);
  else serveFile(route, res);
}).listen(port, host, () => {
  console.info(`[frontend-gateway] UI ready on http://${host}:${port}`);
  console.info(`[frontend-gateway] Proxying /api to ${backend.origin}`);
  console.info(`[frontend-gateway] External base path ${basePath || "/"}`);
});
