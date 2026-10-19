import { useState } from "react";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "./ui/dialog";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Textarea } from "./ui/textarea";
import { Label } from "./ui/label";
import { toast } from "sonner";
import { errMsg } from "../lib/api";

// Confirmation dialog for sensitive/financial actions; optional fields collected before submit.
export function ActionDialog({ trigger, title, description, fields = [], confirmLabel = "Confirm", destructive, onSubmit, testid }) {
  const [open, setOpen] = useState(false);
  const [vals, setVals] = useState({});
  const [busy, setBusy] = useState(false);
  const submit = async () => {
    setBusy(true);
    try {
      await onSubmit(vals);
      toast.success("Done");
      setOpen(false);
      setVals({});
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setBusy(false);
    }
  };
  return (
    <>
      <span onClick={() => setOpen(true)} data-testid={testid}>{trigger}</span>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent data-testid={`${testid}-dialog`} className="bg-card">
          <DialogHeader>
            <DialogTitle className="font-serif">{title}</DialogTitle>
            {description && <DialogDescription>{description}</DialogDescription>}
          </DialogHeader>
          <div className="space-y-4">
            {fields.map((f) => (
              <div key={f.name} className="space-y-1.5">
                <Label>{f.label}</Label>
                {f.type === "select" ? (
                  <select data-testid={`${testid}-${f.name}`} value={vals[f.name] || ""} onChange={(e) => setVals({ ...vals, [f.name]: e.target.value })} className="w-full h-10 rounded-md border bg-background px-3 text-sm">
                    <option value="">Select…</option>
                    {f.options.map((o) => <option key={o} value={o}>{o.replace(/_/g, " ")}</option>)}
                  </select>
                ) : f.type === "textarea" ? (
                  <Textarea data-testid={`${testid}-${f.name}`} value={vals[f.name] || ""} onChange={(e) => setVals({ ...vals, [f.name]: e.target.value })} />
                ) : f.type === "checkbox" ? (
                  <input type="checkbox" data-testid={`${testid}-${f.name}`} checked={!!vals[f.name]} onChange={(e) => setVals({ ...vals, [f.name]: e.target.checked })} className="ml-2 accent-amber-400" />
                ) : (
                  <Input data-testid={`${testid}-${f.name}`} type={f.type || "text"} value={vals[f.name] ?? ""} onChange={(e) => setVals({ ...vals, [f.name]: e.target.value })} />
                )}
              </div>
            ))}
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setOpen(false)}>Back</Button>
            <Button data-testid={`${testid}-confirm`} disabled={busy} variant={destructive ? "destructive" : "default"} onClick={submit}>{busy ? "Working…" : confirmLabel}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
