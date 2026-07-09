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
