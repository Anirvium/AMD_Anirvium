from __future__ import annotations

from typing import Any, Dict, List

from app.schemas.run import RunResult


def build_trajectory_property_graph(run: RunResult) -> Dict[str, Any]:
    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []

    run_node_id = f"run:{run.run_id}"
    nodes.append(
        {
            "id": run_node_id,
            "labels": ["Run"],
            "properties": {
                "run_id": run.run_id,
                "status": run.status,
                "dataset": run.metadata.get("dataset"),
                "score": run.evaluation.metrics.overall_score,
            },
        }
    )

    for span in run.trajectory:
        span_node_id = f"span:{run.run_id}:{span.step_id}"
        nodes.append(
            {
                "id": span_node_id,
                "labels": ["Span", "AgentStep"],
                "properties": {
                    "run_id": run.run_id,
                    "step_id": span.step_id,
                    "agent_name": span.agent_name,
                    "approval_state": span.approval_state.value,
                    "confidence": span.confidence,
                    "latency_ms": span.latency_ms,
                    "model_name": span.model_name,
                    "reasoning_summary": span.reasoning_summary,
                },
            }
        )
        edges.append({"source": run_node_id, "target": span_node_id, "type": "HAS_SPAN", "properties": {}})
        if span.parent_step_id:
            edges.append(
                {
                    "source": f"span:{run.run_id}:{span.parent_step_id}",
                    "target": span_node_id,
                    "type": "NEXT_STEP",
                    "properties": {"label": "passes structured context"},
                }
            )
        for evidence_id in span.evidence_ids:
            evidence_node_id = f"evidence:{evidence_id}"
            nodes.append({"id": evidence_node_id, "labels": ["Evidence"], "properties": {"evidence_id": evidence_id}})
            edges.append({"source": span_node_id, "target": evidence_node_id, "type": "USES_EVIDENCE", "properties": {}})
        for risk_flag in span.risk_flags:
            risk_node_id = f"risk:{risk_flag}"
            nodes.append({"id": risk_node_id, "labels": ["RiskFlag"], "properties": {"risk_flag": risk_flag}})
            edges.append({"source": span_node_id, "target": risk_node_id, "type": "EMITS_RISK", "properties": {}})
        for tool in span.tools_used:
            tool_node_id = f"tool:{tool}"
            nodes.append({"id": tool_node_id, "labels": ["Tool"], "properties": {"name": tool}})
            edges.append({"source": span_node_id, "target": tool_node_id, "type": "CALLS_TOOL", "properties": {}})

    for diagnosis in run.evaluation.diagnosis:
        diagnosis_node_id = f"diagnosis:{run.run_id}:{diagnosis.failure_type}:{diagnosis.ticket_id or 'global'}"
        nodes.append(
            {
                "id": diagnosis_node_id,
                "labels": ["Diagnosis"],
                "properties": {
                    "failure_type": diagnosis.failure_type,
                    "severity": diagnosis.severity,
                    "ticket_id": diagnosis.ticket_id,
                    "affected_agent": diagnosis.affected_agent,
                    "recommended_fix": diagnosis.recommended_fix,
                },
            }
        )
        edges.append({"source": run_node_id, "target": diagnosis_node_id, "type": "HAS_DIAGNOSIS", "properties": {}})

    for action in run.final_actions:
        action_node_id = f"action:{run.run_id}:{action.ticket_id}"
        nodes.append(
            {
                "id": action_node_id,
                "labels": ["FinalAction"],
                "properties": {
                    "ticket_id": action.ticket_id,
                    "approval_state": action.approval_state,
                    "confidence_score": action.confidence_score,
                    "compliance_status": action.compliance_status,
                    "human_escalation_required": action.human_escalation_required,
                },
            }
        )
        edges.append({"source": run_node_id, "target": action_node_id, "type": "PRODUCES_ACTION", "properties": {}})

    if run.sarvagun:
        sarvagun = run.sarvagun
        conversation_node_id = f"conversation:{sarvagun.conversation.conversation_id}"
        customer_node_id = f"customer:{sarvagun.customer_context.customer_id}"
        transcript_node_id = f"transcript:{sarvagun.transcript.transcript_id}"
        escalation_node_id = f"escalation:{sarvagun.escalation.escalation_id}"
        nodes.extend(
            [
                {
                    "id": conversation_node_id,
                    "labels": ["Conversation", "SarvagunExecution"],
                    "properties": {
                        "conversation_id": sarvagun.conversation.conversation_id,
                        "message_type": sarvagun.conversation.message_type,
                        "execution_mode": sarvagun.execution_strategy.execution_mode,
                        "resolution_stage": sarvagun.resolution_stage,
                    },
                },
                {
                    "id": customer_node_id,
                    "labels": ["Customer"],
                    "properties": {
                        "customer_id": sarvagun.customer_context.customer_id,
                        "plan": sarvagun.customer_context.plan,
                        "region": sarvagun.customer_context.region,
                    },
                },
                {
                    "id": transcript_node_id,
                    "labels": ["Transcript"],
                    "properties": {
                        "transcript_id": sarvagun.transcript.transcript_id,
                        "resolution_status": sarvagun.transcript.resolution_status,
                        "redaction_status": sarvagun.transcript.redaction_status,
                    },
                },
                {
                    "id": escalation_node_id,
                    "labels": ["Escalation"],
                    "properties": sarvagun.escalation.model_dump(),
                },
            ]
        )
        edges.extend(
            [
                {"source": run_node_id, "target": conversation_node_id, "type": "EXECUTES_CONVERSATION", "properties": {"system": "Sarvagun"}},
                {"source": customer_node_id, "target": conversation_node_id, "type": "PARTICIPATES_IN", "properties": {}},
                {"source": conversation_node_id, "target": transcript_node_id, "type": "GENERATES_TRANSCRIPT", "properties": {}},
                {"source": conversation_node_id, "target": escalation_node_id, "type": "CREATES_ESCALATION", "properties": {}},
            ]
        )
        for tool in sarvagun.tool_executions:
            tool_run_node_id = f"tool_execution:{tool.tool_execution_id}"
            nodes.append(
                {
                    "id": tool_run_node_id,
                    "labels": ["ToolExecution"],
                    "properties": {
                        "tool_execution_id": tool.tool_execution_id,
                        "tool_name": tool.tool_name,
                        "operation": tool.operation,
                        "status": tool.status,
                        "simulated": tool.simulated,
                        "audit_id": tool.audit_id,
                    },
                }
            )
            edges.append({"source": conversation_node_id, "target": tool_run_node_id, "type": "EXECUTES_TOOL", "properties": {}})
        if sarvagun.incident.detected and sarvagun.incident.incident_id:
            incident_node_id = f"incident:{sarvagun.incident.incident_id}"
            nodes.append({"id": incident_node_id, "labels": ["IncidentCluster"], "properties": sarvagun.incident.model_dump()})
            edges.append({"source": conversation_node_id, "target": incident_node_id, "type": "LINKED_TO_INCIDENT", "properties": {}})

    if run.superturiya:
        superturiya_node_id = f"superturiya:{run.run_id}"
        nodes.append(
            {
                "id": superturiya_node_id,
                "labels": ["SuperTuriya", "TrajectoryIntelligence"],
                "properties": {
                    "observed_system": run.superturiya.observed_system,
                    "feedback_loop_status": run.superturiya.feedback_loop_status,
                    "trace_count": run.superturiya.trace_count,
                    "event_count": run.superturiya.event_count,
                    "automatic_policy_mutation": run.superturiya.automatic_policy_mutation,
                },
            }
        )
        edges.append({"source": superturiya_node_id, "target": run_node_id, "type": "OBSERVES_AND_EVALUATES", "properties": {}})
        for memory_id in run.superturiya.created_memory_ids:
            memory_node_id = f"memory:{memory_id}"
            nodes.append({"id": memory_node_id, "labels": ["IntelligenceMemory"], "properties": {"memory_id": memory_id}})
            edges.append({"source": superturiya_node_id, "target": memory_node_id, "type": "CREATES_MEMORY", "properties": {}})

    return {
        "run_id": run.run_id,
        "graph_store": "local_property_graph",
        "neo4j_status": "optional_export_not_required_for_demo",
        "node_count": len({node["id"] for node in nodes}),
        "edge_count": len(edges),
        "nodes": _dedupe_nodes(nodes),
        "edges": edges,
        "sample_cypher": build_neo4j_cypher(run),
    }


def build_neo4j_cypher(run: RunResult) -> List[str]:
    statements = [
        "CREATE CONSTRAINT anirvium_run_id IF NOT EXISTS FOR (r:Run) REQUIRE r.run_id IS UNIQUE;",
        "CREATE CONSTRAINT anirvium_span_id IF NOT EXISTS FOR (s:Span) REQUIRE s.id IS UNIQUE;",
        "CREATE CONSTRAINT anirvium_evidence_id IF NOT EXISTS FOR (e:Evidence) REQUIRE e.evidence_id IS UNIQUE;",
        "CREATE CONSTRAINT anirvium_risk_flag IF NOT EXISTS FOR (r:RiskFlag) REQUIRE r.risk_flag IS UNIQUE;",
        "CREATE CONSTRAINT anirvium_tool_name IF NOT EXISTS FOR (t:Tool) REQUIRE t.name IS UNIQUE;",
        (
            "MERGE (r:Run {run_id: $run_id}) "
            "SET r.status = $status, r.dataset = $dataset, r.score = $score"
        ),
        (
            "UNWIND $spans AS span "
            "MERGE (s:Span {id: span.id}) "
            "SET s += span.properties "
            "WITH s, span "
            "MATCH (r:Run {run_id: span.properties.run_id}) "
            "MERGE (r)-[:HAS_SPAN]->(s)"
        ),
        (
            "UNWIND $edges AS edge "
            "MATCH (a {id: edge.source}) "
            "MATCH (b {id: edge.target}) "
            "CALL apoc.create.relationship(a, edge.type, edge.properties, b) YIELD rel "
            "RETURN count(rel)"
        ),
    ]
    return statements


def _dedupe_nodes(nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    by_id: Dict[str, Dict[str, Any]] = {}
    for node in nodes:
        node.setdefault("properties", {})["id"] = node["id"]
        existing = by_id.get(node["id"])
        if existing is None:
            by_id[node["id"]] = node
            continue
        existing["labels"] = sorted(set(existing["labels"] + node["labels"]))
        existing["properties"].update(node.get("properties", {}))
    return list(by_id.values())
