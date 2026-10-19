import { useState } from "react";
import { DataTable } from "../components/admin/DataTable";
import { ADMIN_TABS } from "../components/admin/tabs";
import { Overview, SettingsPanel } from "../components/admin/Overview";

const NAV = [{ v: "overview", l: "Overview" }, ...ADMIN_TABS, { v: "settings", l: "Settings" }];

export default function AdminDashboard() {
  const [tab, setTab] = useState("overview");
  const cfg = ADMIN_TABS.find((t) => t.v === tab);
  return (
    <div className="max-w-[1400px] mx-auto px-4 sm:px-8 py-10 grid grid-cols-1 lg:grid-cols-[220px_1fr] gap-8">
      <aside className="lg:sticky lg:top-24 h-fit min-w-0">
        <p className="overline mb-4">Admin console</p>
        <nav className="flex lg:flex-col gap-1 overflow-x-auto pb-2">
          {NAV.map((t) => (
            <button key={t.v} data-testid={`admin-tab-${t.v}`} onClick={() => setTab(t.v)}
              className={`text-left whitespace-nowrap rounded-lg px-3 py-2 text-sm transition-colors duration-200 ${tab === t.v ? "bg-amber-500/15 text-amber-200" : "text-slate-300 hover:bg-secondary"}`}>{t.l}</button>
          ))}
        </nav>
      </aside>
      <section className="min-w-0">
        <h1 className="text-2xl sm:text-3xl mb-6">{NAV.find((t) => t.v === tab).l}</h1>
        {tab === "overview" ? <Overview /> : tab === "settings" ? <SettingsPanel /> : <DataTable key={tab} name={tab} columns={cfg.cols} actions={cfg.actions} />}
      </section>
    </div>
  );
}
