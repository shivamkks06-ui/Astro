import { useState } from "react";
import { toast } from "sonner";
import { Download, Search } from "lucide-react";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { Loading, ErrorState, Empty } from "../States";
import { useApi } from "../../lib/useApi";
import { api, errMsg } from "../../lib/api";

export function DataTable({ name, columns, actions }) {
  const [q, setQ] = useState("");
  const [filters, setFilters] = useState({});
  const [page, setPage] = useState(1);
  const params = new URLSearchParams({ page, limit: 20, ...(q ? { q } : {}), ...Object.fromEntries(Object.entries(filters).filter(([, v]) => v)) });
  const { data, loading, error, reload } = useApi(`/admin/list/${name}?${params}`);
  const exportCsv = async () => {
    try {
      const res = await api.get(`/admin/export/${name}?${params}`, { responseType: "blob" });
      const a = document.createElement("a");
      a.href = URL.createObjectURL(res.data);
      a.download = `${name}.csv`;
      a.click();
    } catch (e) { toast.error(errMsg(e)); }
  };
  const pages = data ? Math.max(1, Math.ceil(data.total / 20)) : 1;
  return (
    <div className="space-y-4" data-testid={`table-${name}`}>
      <div className="flex flex-wrap gap-3 items-center">
        <div className="relative"><Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input data-testid={`table-${name}-search`} className="pl-9 w-56 bg-card" placeholder="Search / exact ID" value={q} onChange={(e) => { setPage(1); setQ(e.target.value); }} /></div>
        {(data?.filters || []).map((f) => (
          <Input key={f} data-testid={`table-${name}-filter-${f}`} className="w-40 bg-card" placeholder={f} value={filters[f] || ""} onChange={(e) => { setPage(1); setFilters({ ...filters, [f]: e.target.value }); }} />
        ))}
        <Button data-testid={`table-${name}-export`} variant="outline" size="sm" onClick={exportCsv}><Download className="h-4 w-4 mr-2" />CSV</Button>
        <span className="text-xs text-muted-foreground ml-auto">{data ? `${data.total} records` : ""}</span>
      </div>
      {loading ? <Loading /> : error ? <ErrorState error={error} onRetry={reload} /> : data.items.length === 0 ? <Empty title="Nothing here" /> : (
        <div className="overflow-x-auto rounded-xl border">
          <table className="w-full text-xs">
            <thead className="bg-secondary/60 text-left text-muted-foreground"><tr>{columns.map((c) => <th key={c.label} className="p-3 whitespace-nowrap">{c.label}</th>)}{actions && <th className="p-3">Actions</th>}</tr></thead>
            <tbody>{data.items.map((r) => (
              <tr key={r.id} className="border-t align-top" data-testid={`row-${name}-${r.id}`}>
                {columns.map((c) => <td key={c.label} className="p-3 max-w-[260px] break-words">{c.render ? c.render(r) : String(r[c.key] ?? "—")}</td>)}
                {actions && <td className="p-3"><div className="flex flex-wrap gap-1">{actions(r, reload)}</div></td>}
              </tr>))}
            </tbody>
          </table>
        </div>
      )}
      {pages > 1 && (
        <div className="flex gap-2 items-center justify-end text-sm">
          <Button size="sm" variant="outline" disabled={page <= 1} onClick={() => setPage(page - 1)}>Prev</Button><span>{page}/{pages}</span>
          <Button size="sm" variant="outline" disabled={page >= pages} onClick={() => setPage(page + 1)}>Next</Button>
        </div>
      )}
    </div>
  );
}
