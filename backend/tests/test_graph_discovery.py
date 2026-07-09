from app.schemas.run import RunRequest
from app.services.agent_runner import AgentRunner
from app.services.graph_discovery import build_trajectory_property_graph


def test_graph_discovery_exports_property_graph() -> None:
    result = AgentRunner().run(RunRequest(selection_mode="selected", selected_ticket_ids=["CS-002"], dataset="customer_support"))
    graph = build_trajectory_property_graph(result)

    labels = {label for node in graph["nodes"] for label in node["labels"]}
    edge_types = {edge["type"] for edge in graph["edges"]}

    assert graph["graph_store"] == "local_property_graph"
    assert graph["node_count"] >= len(result.trajectory)
    assert {"Run", "Span", "AgentStep", "FinalAction"} <= labels
    assert {"HAS_SPAN", "NEXT_STEP", "PRODUCES_ACTION"} <= edge_types
    assert any(node["properties"].get("reasoning_summary") for node in graph["nodes"] if "Span" in node["labels"])
    assert graph["sample_cypher"]
