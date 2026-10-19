import { CheckCircle2, Circle } from "lucide-react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
import { Loading, ErrorState } from "../components/States";
import { BookingsList } from "../components/BookingsList";
import { ProfileForm } from "../components/astro/ProfileForm";
import { Verification } from "../components/astro/Verification";
import { Listing } from "../components/astro/Listing";
import { Slots } from "../components/astro/Slots";
import { Earnings } from "../components/astro/Earnings";
import { Privacy } from "../components/customer/Privacy";
import { useApi } from "../lib/useApi";

function Checklist({ d }) {
  const p = d.profile;
  const items = [
    ["Profile completed", !!(p.bio && p.languages.length && p.expertise.length)],
    ["Identity verified", p.identity_status === "approved"],
    ["Active listing", !!(p.listing_expires_at && new Date(p.listing_expires_at) > new Date())],
    ["Account in good standing", p.account_status === "active"],
  ];
  return (
    <div className="glass rounded-2xl p-6 mb-8 flex flex-col md:flex-row md:items-center gap-6 justify-between" data-testid="listing-checklist">
      <div className="flex flex-wrap gap-x-6 gap-y-2">
        {items.map(([l, ok]) => <span key={l} className={`flex items-center gap-2 text-sm ${ok ? "text-emerald-300" : "text-muted-foreground"}`}>{ok ? <CheckCircle2 className="h-4 w-4" /> : <Circle className="h-4 w-4" />}{l}</span>)}
      </div>
      <span data-testid="public-listing-state" className={`text-sm font-medium ${d.is_publicly_listed ? "text-emerald-300" : "text-amber-300"}`}>{d.is_publicly_listed ? "Publicly listed" : "Not publicly listed yet"}</span>
    </div>
  );
}

export default function AstrologerDashboard() {
  const { data, loading, error, reload } = useApi("/astrologer/profile");
  const cfg = useApi("/public/config");
  if (loading || cfg.loading) return <Loading />;
  if (error || cfg.error) return <div className="max-w-3xl mx-auto px-4 py-16"><ErrorState error={error || cfg.error} onRetry={() => { reload(); cfg.reload(); }} /></div>;
  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-8 py-10">
      <p className="overline mb-2">Astrologer studio</p>
      <h1 className="text-3xl mb-6">{data.profile.display_name}</h1>
      <Checklist d={data} />
      <Tabs defaultValue="profile">
        <TabsList className="flex flex-wrap h-auto bg-card mb-6">
          {[["profile", "Profile"], ["verification", "Verification"], ["listing", "Listing plan"], ["slots", "Availability"], ["bookings", "Bookings"], ["earnings", "Earnings & payouts"], ["privacy", "Privacy"]].map(([v, l]) => (
            <TabsTrigger key={v} value={v} data-testid={`studio-tab-${v}`}>{l}</TabsTrigger>
          ))}
        </TabsList>
        <TabsContent value="profile"><ProfileForm profile={data.profile} cfg={cfg.data} calls={data.calls} reload={reload} /></TabsContent>
        <TabsContent value="verification"><Verification data={data} reload={reload} /></TabsContent>
        <TabsContent value="listing"><Listing data={data} plans={cfg.data.plans} reload={reload} /></TabsContent>
        <TabsContent value="slots"><Slots durations={cfg.data.slot_durations} /></TabsContent>
        <TabsContent value="bookings"><BookingsList role="astrologer" /></TabsContent>
        <TabsContent value="earnings"><Earnings /></TabsContent>
        <TabsContent value="privacy"><Privacy /></TabsContent>
      </Tabs>
    </div>
  );
}
