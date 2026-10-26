import { useState, useRef } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  FileText,
  Upload,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Building,
  Calendar,
  Sparkles,
  RefreshCw,
  Search,
  Eye,
  ShieldCheck,
  FileCheck,
} from "lucide-react";
import { api } from "@/lib/api";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { useAuth } from "@/store/auth";
import { useUi } from "@/store/ui";

type Doc = {
  id: number;
  institution: string;
  doc_type: string;
  document_number: string;
  expiry_date: string;
  status: string;
  days_left: number;
  hash: string;
};

type ExtractionItem = {
  id: number;
  document_id: number;
  extracted_commencement_date: string | null;
  extracted_expiry_date: string | null;
  extracted_lessor: string | null;
  extracted_lessee: string | null;
  extracted_premises: string | null;
  extracted_renewal_clause: string | null;
  confidence_score: number;
  source_page: number;
  verification_status: string;
  reviewer_notes: string | null;
  institution_name?: string;
  document_number?: string;
};

export default function Documents() {
  const user = useAuth((s) => s.user)!;
  const toast = useUi((s) => s.toast);
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [activeTab, setActiveTab] = useState<"list" | "ocr" | "pending">("list");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [docType, setDocType] = useState<string>("Lease Deed");

  // Review state
  const [reviewingExtraction, setReviewingExtraction] = useState<ExtractionItem | null>(null);
  const [editCommencement, setEditCommencement] = useState("");
  const [editExpiry, setEditExpiry] = useState("");
  const [editPremises, setEditPremises] = useState("");
  const [reviewerNotes, setReviewerNotes] = useState("");

  const q = useQuery({ queryKey: ["docs"], queryFn: () => api.get<Doc[]>("/api/v1/documents") });
  const summary = useQuery({
    queryKey: ["docs-sum"],
    queryFn: () => api.get<Record<string, number>>("/api/v1/documents/expiry-summary"),
  });

  const pendingExtractions = useQuery({
    queryKey: ["pending-extractions"],
    queryFn: () => api.get<ExtractionItem[]>("/api/v1/documents/extractions/pending"),
  });

  const uploadOcrMutation = useMutation({
    mutationFn: async () => {
      if (!selectedFile) throw new Error("No file selected");
      const formData = new FormData();
      formData.append("file", selectedFile);
      formData.append("document_type", docType);
      return api.upload<{ message: string; extraction: ExtractionItem }>("/api/v1/documents/ocr-upload-and-extract", formData);
    },
    onSuccess: (data) => {
      toast("Lease Deed processed via PyMuPDF OCR successfully");
      setSelectedFile(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
      queryClient.invalidateQueries({ queryKey: ["docs"] });
      queryClient.invalidateQueries({ queryKey: ["pending-extractions"] });
      // Open verification pane immediately
      startReview(data.extraction);
    },
    onError: (err: any) => {
      toast(err.message || "OCR Extraction failed");
    },
  });

  const verifyMutation = useMutation({
    mutationFn: ({
      docId,
      extractionId,
      action,
    }: {
      docId: number;
      extractionId: number;
      action: "accept" | "reject";
    }) =>
      api.post(`/api/v1/documents/${docId}/verify-extraction/${extractionId}`, {
        action,
        verified_commencement_date: editCommencement ? new Date(editCommencement).toISOString() : null,
        verified_expiry_date: editExpiry ? new Date(editExpiry).toISOString() : null,
        verified_premises: editPremises,
        reviewer_notes: reviewerNotes,
      }),
    onSuccess: () => {
      toast("Human verification submitted and document validity synced");
      setReviewingExtraction(null);
      queryClient.invalidateQueries({ queryKey: ["docs"] });
      queryClient.invalidateQueries({ queryKey: ["docs-sum"] });
      queryClient.invalidateQueries({ queryKey: ["pending-extractions"] });
      queryClient.invalidateQueries({ queryKey: ["deadlines"] });
    },
    onError: (err: any) => {
      toast(err.message || "Verification failed");
    },
  });

  const official = ["regional_officer", "bureau_officer", "super_admin"].includes(user.role);

  const startReview = (ext: ExtractionItem) => {
    setReviewingExtraction(ext);
    setEditCommencement(ext.extracted_commencement_date ? ext.extracted_commencement_date.split("T")[0] : "");
    setEditExpiry(ext.extracted_expiry_date ? ext.extracted_expiry_date.split("T")[0] : "");
    setEditPremises(ext.extracted_premises || "");
    setReviewerNotes(ext.reviewer_notes || "");
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-extrabold text-ink flex items-center gap-2">
            <Building className="h-7 w-7 text-primary" />
            Lease & Land Document Validity Hub
          </h1>
          <p className="text-sm text-slate-500">
            PyMuPDF OCR extraction of lease commencement, expiry, premises, and statutory Human-in-the-Loop verification.
          </p>
        </div>

        {/* Tab switchers */}
        <div className="flex items-center gap-1 rounded-xl bg-canvas p-1 border border-line">
          <button
            type="button"
            onClick={() => setActiveTab("list")}
            className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition-all ${
              activeTab === "list" ? "bg-white shadow text-ink" : "text-slate-600 hover:text-ink"
            }`}
          >
            Valid Documents
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("ocr")}
            className={`rounded-lg px-3 py-1.5 text-xs font-semibold flex items-center gap-1.5 transition-all ${
              activeTab === "ocr" ? "bg-white shadow text-ink" : "text-slate-600 hover:text-ink"
            }`}
          >
            <Sparkles className="h-3.5 w-3.5 text-primary" />
            OCR Extraction
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("pending")}
            className={`rounded-lg px-3 py-1.5 text-xs font-semibold flex items-center gap-1.5 transition-all ${
              activeTab === "pending" ? "bg-white shadow text-ink" : "text-slate-600 hover:text-ink"
            }`}
          >
            Review Queue
            {(pendingExtractions.data?.length ?? 0) > 0 && (
              <span className="rounded-full bg-rose-500 px-1.5 py-0.2 text-[10px] text-white">
                {pendingExtractions.data?.length}
              </span>
            )}
          </button>
        </div>
      </div>

      {/* Expiry Window Summary Chips */}
      <div className="flex flex-wrap items-center gap-3 text-sm">
        <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Statutory Expiry Horizons:</span>
        {Object.entries(summary.data ?? {}).map(([windowKey, count]) => (
          <span
            key={windowKey}
            className="rounded-full border border-line bg-white px-3 py-1 text-xs font-semibold text-ink shadow-sm"
          >
            {windowKey} Days: <span className="text-primary font-bold">{count}</span>
          </span>
        ))}
      </div>

      {/* TAB 1: Valid Documents List */}
      {activeTab === "list" && (
        <div className="space-y-3">
          {(q.data ?? []).map((d) => (
            <Card key={d.id} className="hover:border-primary/40 transition-colors">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <Badge tone={d.days_left < 30 ? "danger" : d.days_left < 90 ? "warning" : "success"}>
                      {d.status}
                    </Badge>
                    <span className="font-bold text-ink">{d.institution}</span>
                    <span className="text-xs text-slate-400">· {d.doc_type}</span>
                  </div>
                  <p className="text-xs text-slate-600 font-mono">
                    Doc No: <span className="font-semibold">{d.document_number}</span>
                  </p>
                  <p className="text-xs text-slate-500 flex items-center gap-3">
                    <span className="flex items-center gap-1">
                      <Calendar className="h-3.5 w-3.5 text-slate-400" />
                      Expires: {new Date(d.expiry_date).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" })}
                    </span>
                    <span className={d.days_left < 60 ? "font-bold text-rose-600" : "font-medium text-slate-700"}>
                      ({d.days_left} calendar days left)
                    </span>
                    <span className="text-[11px] text-slate-400 font-mono">
                      SHA: {d.hash?.slice(0, 12)}…
                    </span>
                  </p>
                </div>

                <div className="flex items-center gap-2">
                  {user.role === "institution_user" && (
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={async () => {
                        const exp = new Date();
                        exp.setFullYear(exp.getFullYear() + 5);
                        await api.post(`/api/v1/documents/${d.id}/renew`, {
                          issue_date: new Date().toISOString(),
                          expiry_date: exp.toISOString(),
                          sha256: "renewed-demo-hash",
                        });
                        toast("Renewal submitted successfully");
                        q.refetch();
                      }}
                    >
                      Submit Renewal
                    </Button>
                  )}
                  {official && (
                    <Button
                      size="sm"
                      onClick={async () => {
                        await api.post(`/api/v1/documents/${d.id}/verify`, { accept: true });
                        toast("Document statutory verification accepted");
                        q.refetch();
                      }}
                    >
                      <ShieldCheck className="mr-1 h-3.5 w-3.5" />
                      Verify Status
                    </Button>
                  )}
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* TAB 2: OCR Upload & Extraction */}
      {activeTab === "ocr" && (
        <div className="grid gap-6 lg:grid-cols-12">
          <Card className="lg:col-span-5 border-t-4 border-t-primary">
            <h2 className="text-lg font-bold text-ink flex items-center gap-2">
              <Upload className="h-5 w-5 text-primary" />
              Upload Lease Deed for OCR Extraction
            </h2>
            <p className="mt-1 text-xs text-slate-500">
              Upload PDF or scanned lease agreements. PyMuPDF extracts commencement, expiry, registered premises, and renewal clauses automatically.
            </p>

            <div className="mt-4 space-y-4">
              <div>
                <label className="text-xs font-semibold text-slate-700">Document Type</label>
                <select
                  value={docType}
                  onChange={(e) => setDocType(e.target.value)}
                  className="mt-1 w-full rounded-xl border border-line bg-white px-3 py-2 text-sm focus:border-primary focus:outline-none"
                >
                  <option value="Lease Deed">Registered Land Lease Deed</option>
                  <option value="Building Safety Certificate">Building Safety Certificate</option>
                  <option value="Fire Safety NOC">Fire Safety NOC</option>
                  <option value="Occupancy Certificate">Occupancy / Completion Certificate</option>
                </select>
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-700">Select Document File (PDF / Scanned)</label>
                <div
                  onClick={() => fileInputRef.current?.click()}
                  className="mt-1 flex flex-col items-center justify-center rounded-2xl border-2 border-dashed border-line bg-canvas p-6 text-center hover:bg-slate-100/60 cursor-pointer transition-colors"
                >
                  <FileText className="h-10 w-10 text-primary mb-2" />
                  {selectedFile ? (
                    <div>
                      <p className="text-sm font-semibold text-ink">{selectedFile.name}</p>
                      <p className="text-xs text-slate-400">{(selectedFile.size / 1024).toFixed(1)} KB</p>
                    </div>
                  ) : (
                    <div>
                      <p className="text-sm font-semibold text-ink">Click or drag file to upload</p>
                      <p className="text-xs text-slate-400">Supports PDF up to 25MB</p>
                    </div>
                  )}
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".pdf,.png,.jpg,.jpeg"
                    className="hidden"
                    onChange={(e) => {
                      if (e.target.files?.[0]) setSelectedFile(e.target.files[0]);
                    }}
                  />
                </div>
              </div>

              <Button
                className="w-full flex items-center justify-center gap-2"
                onClick={() => uploadOcrMutation.mutate()}
                disabled={!selectedFile || uploadOcrMutation.isPending}
              >
                <Sparkles className="h-4 w-4" />
                {uploadOcrMutation.isPending ? "Executing PyMuPDF OCR..." : "Extract Candidate Metadata"}
              </Button>
            </div>
          </Card>

          <Card className="lg:col-span-7">
            <h2 className="text-lg font-bold text-ink flex items-center gap-2">
              <FileCheck className="h-5 w-5 text-emerald-600" />
              Statutory Requirement Guidelines
            </h2>
            <div className="mt-3 space-y-3 text-xs text-slate-600">
              <div className="rounded-xl bg-slate-50 p-3 border border-line">
                <span className="font-bold text-ink block mb-1">AICTE Approval Process Handbook (APH) Rule 4.2</span>
                Lease deeds must be registered for a minimum statutory period of 30 continuous years (rural/mega cities) or 99 years (concession land) with perpetual renewal provisions.
              </div>
              <div className="rounded-xl bg-slate-50 p-3 border border-line">
                <span className="font-bold text-ink block mb-1">Human-in-the-Loop Principle</span>
                OCR models assist with rapid field extraction. AICTE regulations strictly mandate that all extracted dates, premises clauses, and lessee identities are explicitly reviewed and signed off by a designated Scrutiny or Regional Officer.
              </div>
            </div>
          </Card>
        </div>
      )}

      {/* TAB 3: Review Queue */}
      {activeTab === "pending" && (
        <div className="space-y-4">
          <Card className="p-0 overflow-hidden">
            <div className="border-b border-line bg-canvas p-4 flex items-center justify-between">
              <h2 className="text-lg font-bold text-ink flex items-center gap-2">
                <Eye className="h-5 w-5 text-primary" />
                Extractions Awaiting Human Review
              </h2>
              <Badge tone="warning">{pendingExtractions.data?.length ?? 0} Pending</Badge>
            </div>

            <div className="divide-y divide-line">
              {(pendingExtractions.data ?? []).length === 0 ? (
                <div className="p-8 text-center text-slate-400">
                  No OCR extractions currently waiting for verification.
                </div>
              ) : (
                (pendingExtractions.data ?? []).map((ext) => (
                  <div key={ext.id} className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4 hover:bg-canvas/50">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-ink">Doc #{ext.document_id}</span>
                        <Badge tone="primary">Confidence: {(ext.confidence_score * 100).toFixed(1)}%</Badge>
                      </div>
                      <p className="text-xs text-slate-600">
                        Premises: <span className="font-medium text-ink">{ext.extracted_premises || "Not detected"}</span>
                      </p>
                      <p className="text-xs text-slate-500">
                        Commencement: {ext.extracted_commencement_date ? ext.extracted_commencement_date.split("T")[0] : "—"} · 
                        Expiry: {ext.extracted_expiry_date ? ext.extracted_expiry_date.split("T")[0] : "—"}
                      </p>
                    </div>

                    <Button size="sm" onClick={() => startReview(ext)} className="flex items-center gap-1">
                      <Eye className="h-3.5 w-3.5" /> Review & Confirm
                    </Button>
                  </div>
                ))
              )}
            </div>
          </Card>
        </div>
      )}

      {/* Human Verification Modal / Drawer */}
      {reviewingExtraction && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
          <div className="w-full max-w-2xl max-h-[90vh] overflow-y-auto rounded-2xl bg-white p-6 shadow-2xl border border-line">
            <div className="flex items-center justify-between border-b border-line pb-3">
              <h3 className="text-lg font-bold text-ink flex items-center gap-2">
                <ShieldCheck className="h-5 w-5 text-primary" />
                Human-in-the-Loop Document Verification
              </h3>
              <Badge tone="primary">
                OCR Confidence: {(reviewingExtraction.confidence_score * 100).toFixed(1)}%
              </Badge>
            </div>

            <p className="mt-2 text-xs text-slate-500">
              Verify and confirm the extracted values below before updating statutory expiry dates.
            </p>

            <div className="mt-4 grid gap-4 md:grid-cols-2">
              <div>
                <label className="text-xs font-semibold text-slate-700">Commencement Date</label>
                <input
                  type="date"
                  value={editCommencement}
                  onChange={(e) => setEditCommencement(e.target.value)}
                  className="mt-1 w-full rounded-xl border border-line bg-white px-3 py-2 text-sm focus:border-primary focus:outline-none"
                />
                <span className="text-[11px] text-slate-400">
                  Extracted: {reviewingExtraction.extracted_commencement_date?.split("T")[0] ?? "None"}
                </span>
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-700">Lease Expiry Date</label>
                <input
                  type="date"
                  value={editExpiry}
                  onChange={(e) => setEditExpiry(e.target.value)}
                  className="mt-1 w-full rounded-xl border border-line bg-white px-3 py-2 text-sm focus:border-primary focus:outline-none"
                />
                <span className="text-[11px] text-slate-400">
                  Extracted: {reviewingExtraction.extracted_expiry_date?.split("T")[0] ?? "None"}
                </span>
              </div>

              <div className="md:col-span-2">
                <label className="text-xs font-semibold text-slate-700">Premises / Land Address</label>
                <input
                  type="text"
                  value={editPremises}
                  onChange={(e) => setEditPremises(e.target.value)}
                  className="mt-1 w-full rounded-xl border border-line bg-white px-3 py-2 text-sm focus:border-primary focus:outline-none"
                />
              </div>

              <div className="md:col-span-2">
                <label className="text-xs font-semibold text-slate-700">Detected Renewal Clause</label>
                <div className="mt-1 p-2.5 rounded-xl bg-canvas border border-line text-xs text-slate-700 italic">
                  {reviewingExtraction.extracted_renewal_clause || "No explicit renewal clause text identified."}
                </div>
              </div>

              <div className="md:col-span-2">
                <label className="text-xs font-semibold text-slate-700">Reviewer Verification Notes</label>
                <textarea
                  rows={2}
                  value={reviewerNotes}
                  onChange={(e) => setReviewerNotes(e.target.value)}
                  placeholder="e.g. Inspected registrar seal on Page 4; confirmed 30-year lease term."
                  className="mt-1 w-full rounded-xl border border-line bg-canvas p-2.5 text-sm focus:border-primary focus:outline-none"
                />
              </div>
            </div>

            <div className="mt-6 flex justify-end gap-2 border-t border-line pt-4">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setReviewingExtraction(null)}
              >
                Close
              </Button>
              <Button
                variant="danger"
                size="sm"
                onClick={() =>
                  verifyMutation.mutate({
                    docId: reviewingExtraction.document_id,
                    extractionId: reviewingExtraction.id,
                    action: "reject",
                  })
                }
                disabled={verifyMutation.isPending}
                className="flex items-center gap-1"
              >
                <XCircle className="h-4 w-4" />
                Reject Extraction
              </Button>
              <Button
                size="sm"
                onClick={() =>
                  verifyMutation.mutate({
                    docId: reviewingExtraction.document_id,
                    extractionId: reviewingExtraction.id,
                    action: "accept",
                  })
                }
                disabled={verifyMutation.isPending}
                className="flex items-center gap-1 bg-emerald-600 hover:bg-emerald-700 text-white"
              >
                <CheckCircle2 className="h-4 w-4" />
                Accept & Confirm Expiry
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
