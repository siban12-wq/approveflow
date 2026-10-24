import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { api } from "@/lib/api";
import { useUi } from "@/store/ui";

type Action = string | { code: string; label?: string };

export function ActionBar({
  appId,
  actions,
  onDone,
}: {
  appId: number;
  actions: Action[];
  onDone: () => void;
}) {
  const toast = useUi((s) => s.toast);
  const [modal, setModal] = useState<string | null>(null);
  const [reason, setReason] = useState("");
  const [decision, setDecision] = useState("approved");
  const [order, setOrder] = useState("EOA-DEMO-001");
  const [officer, setOfficer] = useState("");
  const codes = actions.map((a) => (typeof a === "string" ? a : a.code));
  const has = (code: string) => codes.includes(code);

  async function run(kind: string) {
    try {
      if (kind === "forward") await api.post(`/api/v1/applications/${appId}/forward`, { remarks: reason || "Stage completed by authorised officer." });
      if (kind === "return") await api.post(`/api/v1/applications/${appId}/return`, { reason });
      if (kind === "respond") await api.post(`/api/v1/applications/${appId}/respond`, { response: reason, docs: [] });
      if (kind === "clarification") await api.post(`/api/v1/applications/${appId}/clarification`, { question: reason });
      if (kind === "assign") await api.post(`/api/v1/applications/${appId}/assign`, { officer_id: Number(officer), reason });
      if (kind === "decision") await api.post(`/api/v1/applications/${appId}/decision`, { decision, order_ref: order });
      toast("Action recorded in the audit trail.");
      setModal(null);
      setReason("");
      onDone();
    } catch (err) {
      toast((err as Error).message, "err");
    }
  }

  return (
    <div className="flex flex-wrap gap-2">
      {has("forward") && <Button onClick={() => setModal("forward")}>Forward to next stage</Button>}
      {has("return") && (
        <Button variant="outline" onClick={() => setModal("return")}>
          Return for deficiency
        </Button>
      )}
      {has("respond") && <Button onClick={() => setModal("respond")}>Respond to deficiency</Button>}
      {has("clarification") && (
        <Button variant="ghost" onClick={() => setModal("clarification")}>
          Request clarification
        </Button>
      )}
      {has("assign") && (
        <Button variant="ghost" onClick={() => setModal("assign")}>
          Reassign officer
        </Button>
      )}
      {has("decision") && (
        <Button onClick={() => setModal("decision")}>Record decision of competent authority</Button>
      )}

      <Modal open={modal === "forward"} title="Confirm forward" onClose={() => setModal(null)} onConfirm={() => run("forward")}>
        This records a human stage completion and routes the file. It does not approve the application.
        <textarea className="mt-3 w-full rounded-xl border border-line p-2" placeholder="Optional remarks" value={reason} onChange={(e) => setReason(e.target.value)} />
      </Modal>
      <Modal open={modal === "return"} title="Return requires a reason" onClose={() => setModal(null)} onConfirm={() => run("return")} danger>
        Minimum 15 characters. The reason is stored in history and the audit trail.
        <textarea className="mt-3 w-full rounded-xl border border-line p-2" value={reason} onChange={(e) => setReason(e.target.value)} />
      </Modal>
      <Modal open={modal === "respond"} title="Institution response" onClose={() => setModal(null)} onConfirm={() => run("respond")}>
        Describe how the deficiency was addressed.
        <textarea className="mt-3 w-full rounded-xl border border-line p-2" value={reason} onChange={(e) => setReason(e.target.value)} />
      </Modal>
      <Modal open={modal === "clarification"} title="Request clarification" onClose={() => setModal(null)} onConfirm={() => run("clarification")}>
        Question for the institution (min 10 characters).
        <textarea className="mt-3 w-full rounded-xl border border-line p-2" value={reason} onChange={(e) => setReason(e.target.value)} />
      </Modal>
      <Modal open={modal === "assign"} title="Reassign officer" onClose={() => setModal(null)} onConfirm={() => run("assign")}>
        Officer user id and reason.
        <input className="mt-3 w-full rounded-xl border border-line p-2" placeholder="Officer id" value={officer} onChange={(e) => setOfficer(e.target.value)} />
        <textarea className="mt-3 w-full rounded-xl border border-line p-2" value={reason} onChange={(e) => setReason(e.target.value)} />
      </Modal>
      <Modal open={modal === "decision"} title="Human oversight required" onClose={() => setModal(null)} onConfirm={() => run("decision")}>
        <p className="rounded-xl bg-amber-50 p-3 text-amber-900">
          Human oversight required. This action records the decision of the competent authority.
        </p>
        <select className="mt-3 w-full rounded-xl border border-line p-2" value={decision} onChange={(e) => setDecision(e.target.value)}>
          <option value="approved">Approved</option>
          <option value="rejected">Rejected</option>
          <option value="returned_with_conditions">Approved with conditions</option>
        </select>
        <input className="mt-2 w-full rounded-xl border border-line p-2" value={order} onChange={(e) => setOrder(e.target.value)} />
      </Modal>
    </div>
  );
}
