import { useRef, useState } from "react";
import { toast } from "sonner";
import { Camera, Trash2 } from "lucide-react";
import { Button } from "../ui/button";
import { Avatar } from "../AstroCard";
import { api, errMsg } from "../../lib/api";

export function PhotoUpload({ profile, onChange }) {
  const input = useRef(null);
  const [busy, setBusy] = useState(false);
  const run = async (fn, okMsg) => {
    setBusy(true);
    try { await fn(); toast.success(okMsg); onChange(); } catch (e) { toast.error(errMsg(e)); } finally { setBusy(false); if (input.current) input.current.value = ""; }
  };
  const upload = (file) => {
    if (!file) return;
    if (file.size > 5 * 1024 * 1024) return toast.error("Photo must be under 5 MB");
    const fd = new FormData();
    fd.append("file", file);
    run(() => api.post("/astrologer/photo", fd), "Photo updated");
  };
  return (
    <div data-testid="photo-upload" className="flex items-center gap-4 rounded-xl border p-4 bg-card/40">
      <Avatar a={profile} className="h-20 w-20 text-2xl" />
      <div className="space-y-2 min-w-0">
        <p className="text-sm font-medium">Profile photo</p>
        <p className="text-xs text-muted-foreground">A clear, recent photo of your face. JPG, PNG or WEBP under 5 MB. We crop it to a square and remove location data. Customers see it on your card.</p>
        {!profile.photo_url && profile.photo_removed_reason && (
          <p data-testid="photo-removed-notice" className="text-xs text-red-300">Our team removed your last photo: {profile.photo_removed_reason}. Please upload one that follows the guidelines.</p>
        )}
        <input ref={input} type="file" accept="image/jpeg,image/png,image/webp" className="hidden" data-testid="photo-file-input" onChange={(e) => upload(e.target.files?.[0])} />
        <div className="flex flex-wrap gap-2">
          <Button type="button" size="sm" data-testid="photo-choose-button" disabled={busy} onClick={() => input.current?.click()}>
            <Camera className="h-4 w-4 mr-1.5" />{busy ? "Uploading…" : profile.photo_url ? "Change photo" : "Upload photo"}
          </Button>
          {profile.photo_url && (
            <Button type="button" size="sm" variant="ghost" data-testid="photo-remove-button" disabled={busy} onClick={() => run(() => api.delete("/astrologer/photo"), "Photo removed")}>
              <Trash2 className="h-4 w-4 mr-1.5" />Remove
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
