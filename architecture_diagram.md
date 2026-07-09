# Anirvium AI Architecture Diagram

## System Architecture

```mermaid
flowchart LR
  subgraph Frontend["React / Vite Dashboard"]
    UI["Dashboard Workspace"]
    Queue["Ticket Queue"]
    Chat["Support Chat Console"]
    Timeline["Trajectory Timeline"]
    Trace["Tool / Trace Viewer"]
    EvidencePanel["Evidence Panel"]
    Guardrails["Compliance / Handoff Guardrails"]
    Scores["Evaluation Scorecards"]
  end

  subgraph API["FastAPI Backend"]
    Health["GET /health"]
    Tickets["GET /tickets"]
    Demo["GET /demo/winning-run"]
    Runs["POST /runs"]
    Latest["GET /runs/latest"]
    RunRead["GET /runs/{run_id}"]
    Trajectory["GET /runs/{run_id}/trajectory"]
    Evaluation["GET /runs/{run_id}/evaluation"]
    Benchmarks["GET /benchmarks/amd"]
  end

  subgraph Runner["Trajectory Intelligence Runtime"]
    AgentRunner["Agent Runner"]
    Logger["Trajectory Logger"]
    GraphDiscovery["Property Graph Discovery"]
    EvalEngine["Evaluation Engine"]
    Diagnosis["Failure Diagnosis Engine"]
    OptimizerService["Optimization Engine"]
    LLMClient["LLM Client Abstraction"]
    ModelRouter["Model Router"]
  end

  subgraph Agents["Multi-Agent Workflow"]
    Planner["1. Planner Agent"]
    Visual["2. Attachment Evidence Agent"]
    Triage["3. Intake / Triage Agent"]
    Retrieval["4. Knowledge Retrieval Agent"]
    Policy["5. Policy Checker Agent"]
    Escalation["6. Escalation Agent"]
    Response["7. Response Drafting Agent"]
    Compliance["8. Compliance Agent"]
    Handoff["9. Human Escalation Agent"]
    Critic["10. Critic / Evaluator Agent"]
    Reflection["11. Reflection Agent"]
    Learning["12. Learning Extraction Agent"]
    OptimizerAgent["13. Optimizer Agent"]
  end

  subgraph Data["Synthetic Local Data"]
    TicketsData["Support Tickets"]
    Customers["Customers"]
    KB["Knowledge Base"]
    Policies["Policies"]
    RunStore["Run JSON Store"]
  end

  subgraph AMD["AMD Compute Path"]
    VLLM["vLLM OpenAI-Compatible Server"]
    ROCm["ROCm Runtime"]
    GPU["AMD Developer Cloud GPU"]
    Profiles["Text / Critic Runtime Profiles"]
    Benchmark["Benchmark Scripts"]
    Logs["Benchmark Logs / Screenshots"]
  end

  UI --> Queue
  UI --> Chat
  UI --> Timeline
  UI --> Trace
  UI --> EvidencePanel
  UI --> Guardrails
  UI --> Scores

  UI --> Tickets
  UI --> Demo
  UI --> Runs
  UI --> Latest
  UI --> RunRead
  UI --> Trajectory
  UI --> Evaluation
  UI --> Benchmarks

  Demo --> AgentRunner
  Runs --> AgentRunner
  Latest --> RunStore
  RunRead --> RunStore
  Trajectory --> RunStore
  Evaluation --> RunStore
  Benchmarks --> Logs

  AgentRunner --> Planner
  Planner --> Visual
  Visual --> Triage
  Triage --> Retrieval
  Retrieval --> Policy
  Policy --> Escalation
  Escalation --> Response
  Response --> Compliance
  Compliance --> Handoff
  Handoff --> Critic
  Critic --> Reflection
  Reflection --> Learning
  Learning --> OptimizerAgent

  AgentRunner --> Logger
  Logger --> RunStore
  Logger --> GraphDiscovery

  Critic --> EvalEngine
  EvalEngine --> Diagnosis
  Diagnosis --> Reflection
  Diagnosis --> Learning
  Diagnosis --> OptimizerService
  OptimizerService --> OptimizerAgent

  Triage --> TicketsData
  Retrieval --> KB
  Retrieval --> Policies
  Escalation --> Customers
  Policy --> Policies

  AgentRunner --> ModelRouter
  AgentRunner --> LLMClient
  LLMClient --> VLLM
  ModelRouter --> VLLM
  VLLM --> ROCm
  Profiles --> VLLM
  ROCm --> GPU
  Benchmark --> AgentRunner
  Benchmark --> Logs
```

## Agent Workflow

```mermaid
sequenceDiagram
  participant Manager as Support Manager
  participant API as FastAPI /runs
  participant Runner as Agent Runner
  participant Planner as Planner Agent
  participant Visual as Attachment Evidence Agent
  participant Triage as Triage Agent
  participant Retrieval as Retrieval Agent
  participant Policy as Policy Agent
  participant Escalation as Escalation Agent
  participant Response as Response Agent
  participant Compliance as Compliance Agent
  participant Handoff as Human Escalation Agent
  participant Critic as Critic Agent
  participant Reflection as Reflection Agent
  participant Learning as Learning Extraction Agent
  participant Optimizer as Optimizer Agent
  participant Store as Run Store

  Manager->>API: Analyze high-priority support queue
  API->>Runner: Create run
  Runner->>Planner: Build plan, evidence contract, and stop conditions
  Planner-->>Runner: Public reasoning summary and workflow plan
  Runner->>Visual: Extract attachment findings, text, logs, and metadata
  Visual-->>Runner: Attachment evidence cards and policy-check flags
  Runner->>Triage: Classify urgency, sentiment, SLA risk
  Triage-->>Runner: Ticket classifications and risk flags
  Runner->>Retrieval: Retrieve KB and policy evidence
  Retrieval-->>Runner: KB, policy, and attachment evidence IDs
  Runner->>Policy: Apply refund, security, SLA, and evidence rules
  Policy-->>Runner: Approval states and policy constraints
  Runner->>Escalation: Select owner, route, urgency, next action
  Escalation-->>Runner: Escalation recommendation
  Runner->>Response: Draft safe customer response
  Response-->>Runner: Final actions and approval state
  Runner->>Compliance: Check legal, regulatory, company, privacy, and evidence rules
  Compliance-->>Runner: Compliance status and safe rewrites
  Runner->>Handoff: Apply confidence threshold and approval routing
  Handoff-->>Runner: Human handoff decision and summary
  Runner->>Critic: Evaluate full trajectory
  Critic-->>Runner: Scorecard and failure diagnosis
  Runner->>Reflection: Review completed responses and repeated mistakes
  Reflection-->>Runner: Reflection signals and durable improvements
  Runner->>Learning: Extract lessons from human handoffs and transcripts
  Learning-->>Runner: Learning artifacts and eval-case suggestions
  Runner->>Optimizer: Recommend workflow improvements
  Optimizer-->>Runner: Prompt, routing, checklist, and threshold fixes
  Runner->>Store: Persist structured trajectory JSON
  Runner-->>API: Completed run result
  API-->>Manager: Actions, trace, scores, diagnosis, optimizations
```

## Evaluation And Optimization Loop

```mermaid
flowchart TD
  Span["Structured Agent Spans"] --> Evidence["Evidence Grounding Check"]
  Span --> AttachmentEvidence["Attachment Evidence Check"]
  Span --> Policy["Policy Compliance Check"]
  Span --> Handoff["Human Handoff Check"]
  Span --> Reflection["Reflection Check"]
  Span --> Learning["Learning Artifact Check"]
  Span --> Escalation["Escalation Quality Check"]
  Span --> Efficiency["Token / Latency Efficiency Check"]
  Span --> Tone["Customer Tone Check"]

  Evidence --> Metrics["Deterministic Scorecard"]
  AttachmentEvidence --> Metrics
  Policy --> Metrics
  Handoff --> Metrics
  Reflection --> Metrics
  Learning --> Metrics
  Escalation --> Metrics
  Efficiency --> Metrics
  Tone --> Metrics

  Metrics --> Failures["Failure Diagnosis"]
  Failures --> Fixes["Optimization Recommendations"]
  Fixes --> Workflow["Improved Agent Workflow"]
  Workflow --> Span
```

## AMD Benchmark Path

```mermaid
flowchart LR
  Benchmark["amd/benchmark_agent_eval.py"] --> Runner["Agent Runner"]
  Runner --> LLMClient["OpenAI-Compatible LLM Client"]
  Profiles["amd/run_runtime_profile.sh"] --> VLLM["vLLM API Server"]
  LLMClient --> VLLM["vLLM API Server"]
  VLLM --> ROCm["ROCm"]
  ROCm --> GPU["AMD Developer Cloud GPU"]
  Runner --> Metrics["tokens/sec, latency, throughput, score"]
  Metrics --> Logs["amd/logs/benchmark_llm_*.json"]
  GPU --> Screenshots["amd/screenshots/"]
```
