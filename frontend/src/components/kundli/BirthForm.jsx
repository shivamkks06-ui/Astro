import { useState } from "react";
import { Loader2 } from "lucide-react";
import { Input } from "../ui/input";
import { Label } from "../ui/label";
import { Button } from "../ui/button";
import { PlaceSearch } from "./PlaceSearch";
import { useLang } from "../../lib/i18n";

export function BirthForm({ initial, busy, onSubmit, submitLabel = "Calculate Kundli" }) {
  const { t } = useLang();
  const [f, setF] = useState({ name: initial?.name || "", date: initial?.date || "", time: initial?.time || "" });
  const [place, setPlace] = useState(initial?.place ? { label: initial.place, lat: initial.lat, lon: initial.lon, tz: initial.tz } : null);
  const [err, setErr] = useState("");
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });

  const submit = (e) => {
    e.preventDefault();
    if (!f.date || !f.time) return setErr(t("Enter the birth date and time."));
    if (!place) return setErr(t("Choose the birthplace from the list."));
    setErr("");
    onSubmit({ name: f.name.trim() || null, date: f.date, time: f.time, place: place.label, lat: place.lat, lon: place.lon, tz: place.tz });
  };

  return (
    <form data-testid="kundli-form" onSubmit={submit} noValidate className="glass rounded-2xl p-5 sm:p-7 space-y-4">
      <div className="space-y-1.5">
        <Label htmlFor="birth-name">{t("Name")} <span className="text-muted-foreground">{t("(optional)")}</span></Label>
        <Input id="birth-name" data-testid="kundli-name-input" maxLength={60} value={f.name} onChange={set("name")} className="h-12" autoComplete="name" />
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="space-y-1.5">
          <Label htmlFor="birth-date">{t("Date of birth")}</Label>
          <Input id="birth-date" type="date" required min="1900-01-01" max="2049-12-31" data-testid="kundli-date-input" value={f.date} onChange={set("date")} className="h-12" />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="birth-time">{t("Time of birth (local)")}</Label>
          <Input id="birth-time" type="time" required data-testid="kundli-time-input" value={f.time} onChange={set("time")} className="h-12" />
        </div>
      </div>
      <div className="space-y-1.5">
        <Label htmlFor="birth-place">{t("Place of birth")}</Label>
        <PlaceSearch value={place} onChange={setPlace} />
      </div>
      {err && <p role="alert" data-testid="kundli-form-error" className="text-sm text-red-300">{err}</p>}
      <Button type="submit" data-testid="kundli-submit" disabled={busy} className="w-full sm:w-auto rounded-full h-12 px-8 text-base">
        {busy && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}{t(submitLabel)}
      </Button>
      <p className="text-xs text-muted-foreground">{t("Your birth details are used only to calculate the chart. They are stored only if you save the chart to your account.")}</p>
    </form>
  );
}
