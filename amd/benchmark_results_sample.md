# Sample Benchmark Results

These values are sample output from the deterministic local benchmark path. Replace them with real logs from AMD Developer Cloud before final submission.

| Metric | Sample value |
| --- | ---: |
| Mode | mock |
| Tickets processed | 8 |
| Agent steps evaluated | 7 |
| Average trajectory score | 88.4 / 100 |
| Average tokens/sec | 24,850 |
| Average run latency | 0.18 sec |
| Average step latency | 2.7 ms |
| Policy compliance | 1.00 |
| Evidence grounding | 1.00 |

Expected AMD Developer Cloud run:

```bash
LLM_BASE_URL=http://localhost:8001/v1 \
LLM_API_KEY=dummy \
LLM_MODEL=<model-running-on-vllm> \
MODE=llm \
TICKETS=8 \
REPEATS=3 \
bash amd/run_agent_benchmark.sh
```

Attach the generated `amd/logs/benchmark_llm_*.json` file and a screenshot of the AMD GPU/vLLM session for the final hackathon repository.

