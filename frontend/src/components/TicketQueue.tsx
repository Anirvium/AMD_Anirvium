import { AlertTriangle, Clock3, ShieldCheck } from "lucide-react";
import type { SupportTicket } from "../api/types";

interface TicketQueueProps {
  tickets: SupportTicket[];
  selectedTicketIds: string[];
}

function slaLabel(ticket: SupportTicket) {
  if (ticket.priority === "critical") return "Critical";
  if (ticket.priority === "high" || ticket.plan === "enterprise") return "High";
  if (ticket.priority === "medium") return "Watch";
  return "Low";
}

export default function TicketQueue({ tickets, selectedTicketIds }: TicketQueueProps) {
  return (
    <section className="panel queue-panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Queue</p>
          <h2>Support Tickets</h2>
        </div>
        <span className="count-pill">{tickets.length}</span>
      </div>

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Ticket</th>
              <th>Customer</th>
              <th>Tier</th>
              <th>Priority</th>
              <th>SLA</th>
              <th>Risk</th>
            </tr>
          </thead>
          <tbody>
            {tickets.map((ticket) => {
              const selected = selectedTicketIds.includes(ticket.ticket_id);
              return (
                <tr key={ticket.ticket_id} className={selected ? "selected-row" : ""}>
                  <td>
                    <strong>{ticket.ticket_id}</strong>
                    <span>{ticket.issue_type.replaceAll("_", " ")}</span>
                  </td>
                  <td>{ticket.customer_name}</td>
                  <td>
                    <span className={`tier tier-${ticket.plan}`}>{ticket.plan}</span>
                  </td>
                  <td>
                    <span className={`priority priority-${ticket.priority}`}>
                      {ticket.priority === "critical" && <AlertTriangle size={14} />}
                      {ticket.priority}
                    </span>
                  </td>
                  <td>
                    <span className="sla-cell">
                      <Clock3 size={14} />
                      {slaLabel(ticket)}
                    </span>
                  </td>
                  <td>
                    <span className="risk-cell">
                      <ShieldCheck size={14} />
                      {ticket.expected_evidence_ids.length} evidence IDs
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}

