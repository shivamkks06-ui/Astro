import { useState } from "react";
import { Search } from "lucide-react";
import { Input } from "../components/ui/input";
import { Switch } from "../components/ui/switch";
import { Button } from "../components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import { AstroCard } from "../components/AstroCard";
import { Loading, ErrorState, Empty } from "../components/States";
import { useApi } from "../lib/useApi";

const ANY = "any";

function Pick({ value, onChange, items, placeholder, testid }) {
  return (
    <Select value={value} onValueChange={onChange}>
      <SelectTrigger data-testid={testid} className="bg-card"><SelectValue placeholder={placeholder} /></SelectTrigger>
      <SelectContent>
        <SelectItem value={ANY}>{placeholder}</SelectItem>
        {items.map((i) => <SelectItem key={i} value={i}>{i}</SelectItem>)}
      </SelectContent>
    </Select>
  );
}

export default function Discover() {
  const cfg = useApi("/public/config");
  const [f, setF] = useState({ language: ANY, expertise: ANY, sort: "rating", min_exp: "", q: "", verified_credential: false });
  const [page, setPage] = useState(1);
  const params = new URLSearchParams({ page, limit: 12, sort: f.sort });
  if (f.language !== ANY) params.set("language", f.language);
  if (f.expertise !== ANY) params.set("expertise", f.expertise);
  if (f.min_exp) params.set("min_exp", f.min_exp);
  if (f.q) params.set("q", f.q);
  if (f.verified_credential) params.set("verified_credential", "true");
  const list = useApi(`/astrologers?${params}`);
  const set = (k) => (v) => { setPage(1); setF({ ...f, [k]: v }); };
  const pages = list.data ? Math.max(1, Math.ceil(list.data.total / 12)) : 1;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-8 py-12">
      <p className="overline mb-2">Discover</p>
      <h1 className="text-3xl sm:text-4xl mb-8">Find your astrologer</h1>
      <div className="glass rounded-2xl p-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-6 items-center mb-10">
        <div className="relative lg:col-span-2">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input data-testid="filter-search" className="pl-9 bg-card" placeholder="Search by name" value={f.q} onChange={(e) => set("q")(e.target.value)} />
        </div>
        <Pick testid="filter-language" value={f.language} onChange={set("language")} items={cfg.data?.languages || []} placeholder="Any language" />
        <Pick testid="filter-expertise" value={f.expertise} onChange={set("expertise")} items={cfg.data?.expertise || []} placeholder="Any expertise" />
        <Input data-testid="filter-min-exp" type="number" min="0" className="bg-card" placeholder="Min. years" value={f.min_exp} onChange={(e) => set("min_exp")(e.target.value)} />
        <label className="flex items-center gap-2 text-sm"><Switch data-testid="filter-credential-verified" checked={f.verified_credential} onCheckedChange={set("verified_credential")} />Credentials reviewed</label>
      </div>
      <div className="flex justify-between items-center mb-6 text-sm text-muted-foreground">
        <span data-testid="results-count">{list.data ? `${list.data.total} astrologers` : ""}</span>
        <Select value={f.sort} onValueChange={set("sort")}>
          <SelectTrigger data-testid="sort-select" className="w-44 bg-card"><SelectValue /></SelectTrigger>
          <SelectContent><SelectItem value="rating">Top rated</SelectItem><SelectItem value="experience">Most experienced</SelectItem><SelectItem value="price">Lowest chat rate</SelectItem></SelectContent>
        </Select>
      </div>
      {list.loading ? <Loading /> : list.error ? <ErrorState error={list.error} onRetry={list.reload} /> : list.data.items.length === 0 ? (
        <Empty title="No astrologers match these filters" hint="Try removing a filter." />
      ) : (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">{list.data.items.map((a, i) => <AstroCard key={a.id} a={a} i={i} />)}</div>
      )}
      {pages > 1 && (
        <div className="flex justify-center gap-3 mt-10">
          <Button data-testid="page-prev" variant="outline" disabled={page <= 1} onClick={() => setPage(page - 1)}>Previous</Button>
          <span className="self-center text-sm">{page} / {pages}</span>
          <Button data-testid="page-next" variant="outline" disabled={page >= pages} onClick={() => setPage(page + 1)}>Next</Button>
        </div>
      )}
    </div>
  );
}
