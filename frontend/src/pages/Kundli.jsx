import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { Save, Trash2, Check } from "lucide-react";
import { toast } from "sonner";
import { Button } from "../components/ui/button";
import { BirthForm } from "../components/kundli/BirthForm";
import { KundliResult } from "../components/kundli/KundliResult";
import { Loading, ErrorState, Empty } from "../components/States";
import { useAuth } from "../context/AuthContext";
import { api, errMsg } from "../lib/api";
import { useApi } from "../lib/useApi";
import { useLang } from "../lib/i18n";
import { LangToggle } from "../components/LangToggle";

const PENDING = "nv:pending-kundli";

function Saved({ reloadKey, currentId }) {
  const { t } = useLang();
  const nav = useNavigate();
  const { data, loading, error, reload } = useApi(`/kundlis?k=${reloadKey}`);
  const del = async (id) => {
    try {
      await api.delete(`/kundlis/${id}`); toast.success("Chart deleted");
      if (id === currentId) nav("/kundli", { replace: true }); else reload();
    } catch (e) { toast.error(errMsg(e)); }
  };
  if (loading) return <Loading text={t("Loading saved charts")} />;
  if (error) return <ErrorState error={error} onRetry={reload} />;
  if (!data.items.length) return <Empty title={t("No saved charts yet")} hint={t("Calculate a Kundli and tap Save to keep it here.")} />;
  return (
    <ul data-testid="kundli-saved-list" className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
      {data.items.map((k) => (
        <li key={k.id} className="rounded-xl border bg-card/60 p-4 flex items-start justify-between gap-3">
          <Link to={`/kundli/${k.id}`} data-testid={`kundli-saved-${k.id}`} className="min-w-0 flex-1">
            <p className="font-semibold text-amber-100 truncate">{k.name || "Birth chart"}</p>
            <p className="text-xs text-muted-foreground truncate">{k.date} · {k.time} · {k.place}</p>
            <p className="text-xs mt-1">Lagna {k.ascendant} · Moon {k.moon_sign}</p>
          </Link>
          <button type="button" aria-label="Delete chart" data-testid={`kundli-delete-${k.id}`} onClick={() => del(k.id)} className="h-11 w-11 -mr-2 -mt-2 inline-flex items-center justify-center text-muted-foreground hover:text-red-300"><Trash2 className="h-4 w-4" /></button>
        </li>
      ))}
    </ul>
  );
}

function SavedView({ id }) {
  const { t } = useLang();
  const { data, loading, error, reload } = useApi(`/kundlis/${id}`);
  const nav = useNavigate();
  if (loading) return <Loading text={t("Calculating chart")} />;
  if (error) return <ErrorState error={error} onRetry={reload} />;
  return <KundliResult input={data.input} chart={data.chart} style={data.input.chart_style} onEdit={() => nav("/kundli")} />;
}

export default function Kundli() {
  const { id } = useParams();
  const { user } = useAuth();
  const { t } = useLang();
  const nav = useNavigate();
  const [res, setRes] = useState(null);
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(null);
  const [style, setStyle] = useState("north");
  const [k, setK] = useState(0);
  const [last, setLast] = useState(null);

  const calc = async (input) => {
    setBusy(true);
    try {
      const { data } = await api.post("/kundli/calculate", input);
      setRes(data); setSaved(null); setLast(input);
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (e) { toast.error(errMsg(e)); } finally { setBusy(false); }
  };

  useEffect(() => {
    const p = sessionStorage.getItem(PENDING);
    if (p && user && !id) { sessionStorage.removeItem(PENDING); calc(JSON.parse(p)); }
  }, [user, id]); // eslint-disable-line react-hooks/exhaustive-deps

  const save = async () => {
    if (!user) { sessionStorage.setItem(PENDING, JSON.stringify(res.input)); nav("/login?next=/kundli"); return; }
    setBusy(true);
    try {
      const { data } = await api.post("/kundlis", { ...res.input, chart_style: style });
      setSaved(data.id); setK(k + 1);
      toast.success(data.duplicate ? "This chart is already saved" : "Chart saved to your account");
    } catch (e) { toast.error(errMsg(e)); } finally { setBusy(false); }
  };

  const saveBtn = (
    <Button data-testid="kundli-save" onClick={save} disabled={busy || !!saved} variant={saved ? "outline" : "default"} className="rounded-full h-11">
      {saved ? <><Check className="h-4 w-4 mr-2" />{t("Saved")}</> : <><Save className="h-4 w-4 mr-2" />{t(user ? "Save" : "Log in to save")}</>}
    </Button>
  );

  return (
    <div className="max-w-7xl mx-auto px-5 sm:px-8 py-8 sm:py-12 space-y-10">
      <header className="max-w-2xl">
        <div className="flex flex-wrap items-center justify-between gap-3 mb-2"><p className="overline">{t("Free Kundli")}</p><LangToggle /></div>
        <h1 className="text-[1.875rem] leading-tight sm:text-5xl">{t("Your Vedic birth chart")}</h1>
        <p className="mt-3 text-sm sm:text-base text-muted-foreground">{t("Sidereal positions calculated from NASA JPL ephemeris data, with Lagna, houses, nakshatras and Vimshottari dasha.")}</p>
        <Link to="/kundli/match" data-testid="kundli-match-link" className="mt-4 inline-flex items-center min-h-11 rounded-full border border-amber-400/40 px-5 text-sm text-amber-200 hover:bg-amber-400/10 print:hidden">{t("Kundli matching (36 Guna Milan)")} →</Link>
      </header>
      {id ? <SavedView id={id} /> : res ? (
        <KundliResult input={res.input} chart={res.chart} onStyle={setStyle} actions={saveBtn} onEdit={() => setRes(null)} />
      ) : <BirthForm key={JSON.stringify(last)} initial={last} busy={busy} onSubmit={calc} />}
      {user && (
        <section className="space-y-4 print:hidden">
          <h2 className="text-xl sm:text-2xl">{t("Saved charts")}</h2>
          <Saved reloadKey={k} currentId={id} />
        </section>
      )}
    </div>
  );
}
