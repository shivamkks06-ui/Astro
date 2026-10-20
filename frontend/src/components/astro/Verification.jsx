import { useRef, useState } from "react";
import { toast } from "sonner";
import { Upload, Lock } from "lucide-react";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { StatusPill } from "../States";
import { api, errMsg, fmtDate } from "../../lib/api";

const KINDS = {
  identity: { title: "Identity verification", hint: "A government ID such as Aadhaar (masked), PAN, passport or voter ID. Required before you can be listed or receive payouts.", types: ["Aadhaar (masked)", "PAN", "Passport", "Voter ID", "Driving licence"] },
  credential: { title: "Professional credentials (optional)", hint: "Certificates or degrees in Jyotish or related fields. Reviewed separately; the badge only appears once approved.", types: ["Jyotish certificate", "Degree", "Institute membership", "Other"] },
};

function KindCard({ kind, kase, docs, reload }) {
  const k = KINDS[kind];
  const [docType, setDocType] = useState(k.types[0]);
  const [busy, setBusy] = useState(false);
  const fileRef = useRef(null);
  const status = kase?.status || "not_submitted";
  const upload = async () => {
    const file = fileRef.current?.files?.[0];
    if (!file) return toast.error("Choose a file first");
    setBusy(true);
    const fd = new FormData();
    fd.append("kind", kind); fd.append("doc_type", docType); fd.append("file", file);
    try { await api.post("/astrologer/documents", fd); toast.success("Uploaded to private storage"); fileRef.current.value = ""; reload(); } catch (e) { toast.error(errMsg(e)); } finally { setBusy(false); }
  };
  const submit = async () => { try { await api.post(`/astrologer/verification/${kind}/submit`); toast.success("Submitted for review"); reload(); } catch (e) { toast.error(errMsg(e)); } };
  const mine = docs.filter((d) => d.kind === kind);
  const canEdit = !["submitted", "approved"].includes(status);
  return (
    <div className="rounded-2xl border p-6 space-y-4 bg-card/60" data-testid={`verification-${kind}`}>
      <div className="flex justify-between items-start gap-3"><h3 className="text-lg">{k.title}</h3><StatusPill status={status} testid={`verification-${kind}-status`} /></div>
      <p className="text-xs text-muted-foreground">{k.hint}</p>
      {kase?.review_notes && <p className="text-sm rounded-lg bg-secondary p-3" data-testid={`verification-${kind}-notes`}>Reviewer notes: {kase.review_notes}</p>}
      <div className="space-y-2">{mine.map((d) => <p key={d.id} className="text-xs flex items-center gap-2"><Lock className="h-3 w-3 text-emerald-400" />{d.doc_type}: {d.original_filename} · {fmtDate(d.created_at)}</p>)}</div>
      {canEdit && (
        <div className="space-y-3">
          <select data-testid={`doc-type-${kind}`} value={docType} onChange={(e) => setDocType(e.target.value)} className="w-full h-10 rounded-md border bg-background px-3 text-sm">{k.types.map((t) => <option key={t}>{t}</option>)}</select>
          <Input data-testid={`doc-file-${kind}`} ref={fileRef} type="file" accept=".pdf,.jpg,.jpeg,.png,.webp" className="bg-background" />
          <div className="flex gap-2 flex-wrap">
            <Button data-testid={`doc-upload-${kind}`} variant="outline" disabled={busy} onClick={upload}><Upload className="h-4 w-4 mr-2" />{busy ? "Uploading…" : "Upload"}</Button>
            <Button data-testid={`verification-submit-${kind}`} disabled={!mine.length} onClick={submit}>{status === "rejected" ? "Resubmit" : "Submit for review"}</Button>
          </div>
        </div>
      )}
    </div>
  );
}

export function Verification({ data, reload }) {
  const byKind = Object.fromEntries(data.cases.map((c) => [c.kind, c]));
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <KindCard kind="identity" kase={byKind.identity} docs={data.documents} reload={reload} />
      <KindCard kind="credential" kase={byKind.credential} docs={data.documents} reload={reload} />
      <p className="text-xs text-muted-foreground lg:col-span-2">Documents stay in private storage. Only authorised reviewers can open them, through 5-minute links, and every access is logged.</p>
    </div>
  );
}
