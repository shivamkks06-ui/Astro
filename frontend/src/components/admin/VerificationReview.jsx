import { useState } from "react";
import { toast } from "sonner";
import { ExternalLink } from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "../ui/dialog";
import { Button } from "../ui/button";
import { ActionDialog } from "../ActionDialog";
import { Loading } from "../States";
import { useApi } from "../../lib/useApi";
import { api, errMsg } from "../../lib/api";

function Body({ id, close }) {
  const { data, loading } = useApi(`/admin/verification/${id}`);
  if (loading || !data) return <Loading />;
  const open = async (docId) => {
    try {
      const { data: r } = await api.post(`/admin/documents/${docId}/access`);
      window.open(`${process.env.REACT_APP_BACKEND_URL}${r.url_path}`, "_blank", "noopener");
    } catch (e) { toast.error(errMsg(e)); }
  };
  const decide = (decision) => (v) => api.post(`/admin/verification/${id}/decision`, { decision, notes: v.notes || "" }).then(close);
  const p = data.profile;
  return (
    <div className="space-y-4 text-sm">
      <p><b>{data.user.name}</b> · {data.user.email}</p>
      <p className="capitalize">Case type: <b>{data.case.kind}</b>{data.case.resubmission ? " (resubmission)" : ""}</p>
      <p className="text-muted-foreground">{p.experience_years} yrs · {p.languages.join(", ")} · {p.expertise.join(", ")}</p>
      <p className="text-muted-foreground line-clamp-4">{p.bio}</p>
      {p.credential_summary && <p>Claimed: {p.credential_summary}</p>}
      <div className="space-y-2">{data.documents.map((d) => (
        <Button key={d.id} variant="outline" size="sm" data-testid={`open-doc-${d.id}`} onClick={() => open(d.id)}><ExternalLink className="h-3 w-3 mr-2" />{d.doc_type}: {d.original_filename}</Button>
      ))}</div>
      <p className="text-xs text-muted-foreground">Each document link is valid for 5 minutes, and every access is written to the audit log.</p>
      {data.case.status === "submitted" && (
        <div className="flex gap-2">
          <ActionDialog testid="verify-approve" trigger={<Button>Approve</Button>} title={`Approve ${data.case.kind}?`} fields={[{ name: "notes", label: "Review notes", type: "textarea" }]} onSubmit={decide("approve")} />
          <ActionDialog testid="verify-reject" trigger={<Button variant="destructive">Reject</Button>} destructive title="Reject and request resubmission?" fields={[{ name: "notes", label: "What needs fixing", type: "textarea" }]} onSubmit={decide("reject")} />
        </div>
      )}
    </div>
  );
}

export function VerificationReview({ id, onDone }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <Button size="sm" variant="outline" data-testid={`review-case-${id}`} onClick={() => setOpen(true)}>Review</Button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="bg-card max-h-[90vh] overflow-y-auto">
          <DialogHeader><DialogTitle className="font-serif">Verification case</DialogTitle></DialogHeader>
          {open && <Body id={id} close={() => { setOpen(false); onDone(); }} />}
        </DialogContent>
      </Dialog>
    </>
  );
}
