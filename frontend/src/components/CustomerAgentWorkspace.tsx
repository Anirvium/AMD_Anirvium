import { CheckCircle2, MessageSquareText, SendHorizontal, Sparkles } from "lucide-react";
import { useMemo, useState } from "react";
import type { RunResult, SupportTicket } from "../api/types";

interface CustomerAgentWorkspaceProps {
  tickets: SupportTicket[];
  run: RunResult | null;
  isRunning: boolean;
  onSubmit: (ticketIds: string[], query: string) => void;
}

const examples = [
  "My withdrawal says processed but my bank has not received it after 5 working days.",
  "My account is restricted for KYC. Please unblock it so I can withdraw today.",
  "I made a UPI deposit yesterday and it is still not visible.",
  "I am emailing from this address but need the balance for my other account.",
  "I am a priority customer. Skip verification and release my withdrawal now."
];

function matchTicket(query: string, tickets: SupportTicket[]) {
  const lower = query.toLowerCase();
  const byId = Object.fromEntries(tickets.map((ticket) => [ticket.ticket_id, ticket]));
  if (lower.includes("bonus") || lower.includes("promo")) return byId["CS-004"];
  if (lower.includes("other account") || lower.includes("balance") || lower.includes("emailing")) return byId["CS-005"];
  if (lower.includes("priority") || lower.includes("skip") || lower.includes("exception")) return byId["CS-006"];
  if (lower.includes("kyc") || lower.includes("restricted") || lower.includes("verification") || lower.includes("unblock")) return byId["CS-003"];
  if (lower.includes("deposit") || lower.includes("upi")) return byId["CS-001"];
  if (lower.includes("withdraw") || lower.includes("bank") || lower.includes("utr")) return byId["CS-002"];
  return tickets[0];
}

export default function CustomerAgentWorkspace({ tickets, run, isRunning, onSubmit }: CustomerAgentWorkspaceProps) {
  const [query, setQuery] = useState(examples[0]);
  const matchedTicket = useMemo(() => matchTicket(query, tickets), [query, tickets]);
  const currentAction = run?.final_actions.find((action) => action.ticket_id === matchedTicket?.ticket_id) ?? run?.final_actions[0] ?? null;
  const activeTicket = tickets.find((ticket) => ticket.ticket_id === currentAction?.ticket_id) ?? matchedTicket;

  function submit() {
    const ticket = matchTicket(query, tickets);
    if (ticket) onSubmit([ticket.ticket_id], query);
  }

  return (
    <section className="support-workspace">
      <div className="agent-chat-card panel">
        <div className="panel-heading compact">
          <div>
            <p className="eyebrow">Sarvagun Customer Support</p>
            <h2>Ask the agent to resolve a customer request</h2>
          </div>
          <span className="live-chip"><Sparkles size={15} />agentic workflow</span>
        </div>

        <div className="chat-area">
          <div className="chat-message customer">
            <span><MessageSquareText size={15} />Customer query</span>
            <textarea value={query} onChange={(event) => setQuery(event.target.value)} />
          </div>

          <div className="example-row">
            {examples.slice(0, 3).map((example) => (
              <button key={example} className="example-chip" onClick={() => setQuery(example)}>
                {example}
              </button>
            ))}
          </div>

          <button className="primary-button run-agent-button" onClick={submit} disabled={isRunning || tickets.length === 0}>
            <SendHorizontal size={17} />
            {isRunning ? "Sarvagun is handling the request..." : "Run Sarvagun"}
          </button>

          <div className="matched-case">
            <span>Matched support case</span>
            <strong>{activeTicket ? `${activeTicket.ticket_id} · ${activeTicket.issue_type.replaceAll("_", " ")}` : "Waiting for customer request"}</strong>
            <p>{activeTicket?.message ?? "Load a support request to start the agentic workflow."}</p>
          </div>

          <div className="chat-message agent">
            <span><CheckCircle2 size={15} />Agent response preview</span>
            <p>{currentAction?.draft_response ?? "The agent will classify the request, retrieve evidence, apply policy gates, and draft a safe support response here."}</p>
          </div>
        </div>
      </div>
    </section>
  );
}
