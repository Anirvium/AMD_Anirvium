import { useEffect, useMemo, useState, type ReactNode } from "react";
import ReactFlow, {
  Background,
  Controls,
  MarkerType,
  Position,
  type Edge,
  type Node
} from "reactflow";
import { BookOpen, BrainCircuit, Gauge, Network, ShieldAlert, Timer, Wrench } from "lucide-react";
import type { RunResult, TrajectorySpan } from "../api/types";

interface SuperTuriyaTraceGraphProps {
  run: RunResult | null;
}

interface TraceNodeData {
  label: ReactNode;
  phase: "sarvagun" | "superturiya";
  status: string;
}

function phaseFor(index: number): TraceNodeData["phase"] {
  return index < 9 ? "sarvagun" : "superturiya";
}

function positionFor(index: number) {
  if (index < 9) {
    const row = Math.floor(index / 3);
    const offset = index % 3;
    const column = row % 2 === 0 ? offset : 2 - offset;
    return { x: column * 230, y: row * 126 };
  }
  return { x: (3 - (index - 9)) * 230, y: 378 };
}

function nodeClass(status: string, phase: TraceNodeData["phase"], selected: boolean) {
  return `trace-graph-node phase-${phase} status-${status}${selected ? " selected" : ""}`;
}

function compact(value: string) {
  return value.replace(" Agent", "").replace("Intake / ", "").replace("Critic / Evaluator", "Critic");
}

export default function SuperTuriyaTraceGraph({ run }: SuperTuriyaTraceGraphProps) {
  const [selectedStepId, setSelectedStepId] = useState<string | null>(null);

  useEffect(() => {
    setSelectedStepId(run?.trajectory[0]?.step_id ?? null);
  }, [run?.run_id]);

  const spansById = useMemo(
    () => new Map((run?.trajectory ?? []).map((span) => [span.step_id, span])),
    [run]
  );
  const selectedSpan = selectedStepId ? spansById.get(selectedStepId) ?? null : null;

  const nodes = useMemo<Node<TraceNodeData>[]>(() => (run?.graph.nodes ?? []).map((graphNode, index) => {
    const span = spansById.get(graphNode.id);
    const phase = phaseFor(index);
    const selected = graphNode.id === selectedStepId;
    return {
      id: graphNode.id,
      position: positionFor(index),
      sourcePosition: Position.Right,
      targetPosition: Position.Left,
      className: nodeClass(graphNode.status, phase, selected),
      selected,
      draggable: false,
      selectable: true,
      ariaLabel: `${graphNode.label}, ${phase}, ${Math.round(graphNode.score * 100)} percent confidence`,
      data: {
        phase,
        status: graphNode.status,
        label: (
          <div className="trace-node-label">
            <span>{phase === "sarvagun" ? "Sarvagun" : "SuperTuriya"} · {graphNode.id.replace("step_", "#")}</span>
            <strong>{compact(graphNode.label)}</strong>
            <small>{Math.round(graphNode.score * 100)}% confidence · {span?.tools_used.length ?? 0} tools</small>
          </div>
        )
      }
    };
  }), [run, selectedStepId, spansById]);

  const edges = useMemo<Edge[]>(() => (run?.graph.edges ?? []).map((edge, index) => ({
    id: `${edge.source}-${edge.target}-${index}`,
    source: edge.source,
    target: edge.target,
    type: "smoothstep",
    label: edge.source === "step_009" ? "handoff to intelligence" : undefined,
    animated: edge.source === "step_009",
    markerEnd: { type: MarkerType.ArrowClosed, width: 14, height: 14, color: "#565d70" },
    style: { stroke: edge.source === "step_009" ? "#8b7cff" : "#394052", strokeWidth: edge.source === "step_009" ? 1.8 : 1.2 },
    labelStyle: { fill: "#9a91ee", fontSize: 8 },
    labelBgStyle: { fill: "#101219", fillOpacity: 0.94 }
  })), [run]);

  if (!run || run.trajectory.length === 0) {
    return (
      <section className="trace-graph-panel trace-graph-empty">
        <Network size={24} />
        <strong>Trajectory graph awaiting a Sarvagun run</strong>
        <span>SuperTuriya will render actual agent spans, context edges, tools, evidence, and risk signals here.</span>
      </section>
    );
  }

  return (
    <section className="trace-graph-panel" aria-label="SuperTuriya trace-driven trajectory graph">
      <header className="trace-graph-header">
        <div><span className="product-kicker">Trace-driven graph</span><h3>Inspect the path SuperTuriya observed</h3></div>
        <div className="graph-legend"><span className="sarvagun">Sarvagun execution</span><span className="superturiya">SuperTuriya intelligence</span></div>
      </header>
      <div className="trace-graph-layout">
        <div className="trace-graph-canvas">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            fitView
            fitViewOptions={{ padding: 0.14, minZoom: 0.56, maxZoom: 1 }}
            minZoom={0.42}
            maxZoom={1.4}
            nodesDraggable={false}
            nodesConnectable={false}
            zoomOnDoubleClick={false}
            onNodeClick={(_, node) => setSelectedStepId(node.id)}
            onPaneClick={() => setSelectedStepId(null)}
            proOptions={{ hideAttribution: true }}
          >
            <Background color="#252a37" gap={18} size={1} />
            <Controls showInteractive={false} position="bottom-left" />
          </ReactFlow>
        </div>
        <TraceInspector span={selectedSpan} />
      </div>
    </section>
  );
}

function TraceInspector({ span }: { span: TrajectorySpan | null }) {
  if (!span) {
    return (
      <aside className="trace-inspector empty">
        <BrainCircuit size={20} />
        <strong>Select a trace node</strong>
        <p>Inspect the recorded decision summary and operational evidence. Hidden chain-of-thought is never exposed.</p>
      </aside>
    );
  }
  return (
    <aside className="trace-inspector" aria-live="polite">
      <div className="trace-inspector-title"><span>{span.step_id}</span><strong>{span.agent_name}</strong><small>{span.approval_state.replaceAll("_", " ")}</small></div>
      <div className="trace-inspector-metrics">
        <span><Timer size={12} />{span.latency_ms}ms</span>
        <span><Gauge size={12} />{Math.round(span.confidence * 100)}%</span>
        <span>{span.tokens_in + span.tokens_out} tokens</span>
      </div>
      <div className="trace-inspector-section"><strong>Decision summary</strong><p>{span.reasoning_summary || span.output_summary}</p></div>
      <div className="trace-inspector-section"><strong>Recorded output</strong><p>{span.output_summary}</p></div>
      <TraceChips icon="tool" values={span.tools_used} empty="No tool recorded" />
      <TraceChips icon="evidence" values={span.evidence_ids} empty="No evidence reference" />
      <TraceChips icon="risk" values={span.risk_flags} empty="No risk flag" />
      <div className="trace-model">Model · {span.model_name}</div>
    </aside>
  );
}

function TraceChips({ icon, values, empty }: { icon: "tool" | "evidence" | "risk"; values: string[]; empty: string }) {
  const Icon = icon === "tool" ? Wrench : icon === "evidence" ? BookOpen : ShieldAlert;
  return (
    <div className={`trace-chip-group ${icon}`}>
      <strong><Icon size={12} />{icon === "tool" ? "Tools" : icon === "evidence" ? "Evidence" : "Risk signals"}</strong>
      <div>{values.length ? values.map((value) => <span key={value}>{value.replaceAll("_", " ")}</span>) : <small>{empty}</small>}</div>
    </div>
  );
}
