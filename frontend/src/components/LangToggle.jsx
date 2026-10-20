import { Languages } from "lucide-react";
import { useLang } from "../lib/i18n";

export function LangToggle() {
  const { lang, setLang } = useLang();
  return (
    <div role="group" aria-label="Language" className="inline-flex items-center gap-1 rounded-full border p-1 print:hidden">
      <Languages aria-hidden="true" className="h-4 w-4 ml-2 text-amber-300" />
      {[["en", "English"], ["hi", "हिन्दी"]].map(([v, l]) => (
        <button key={v} type="button" aria-pressed={lang === v} data-testid={`lang-${v}`} onClick={() => setLang(v)}
          className={`min-h-9 px-3 rounded-full text-sm transition-colors ${lang === v ? "bg-primary text-primary-foreground font-semibold" : "text-muted-foreground"}`}>{l}</button>
      ))}
    </div>
  );
}
