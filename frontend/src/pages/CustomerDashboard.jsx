import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
import { BookingsList } from "../components/BookingsList";
import { BirthProfiles } from "../components/customer/BirthProfiles";
import { Payments } from "../components/customer/Payments";
import { Privacy, Blocks } from "../components/customer/Privacy";
import { useAuth } from "../context/AuthContext";

const TABS = [["bookings", "Bookings"], ["birth", "Birth profiles"], ["payments", "Payments"], ["safety", "Safety"], ["privacy", "Privacy"]];

export default function CustomerDashboard() {
  const { user } = useAuth();
  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-8 py-10">
      <p className="overline mb-2">My account</p>
      <h1 className="text-3xl mb-8">Namaste, {user.name.split(" ")[0]}</h1>
      <Tabs defaultValue="bookings">
        <TabsList className="flex flex-wrap h-auto bg-card mb-6">
          {TABS.map(([v, l]) => <TabsTrigger key={v} value={v} data-testid={`tab-${v}`}>{l}</TabsTrigger>)}
        </TabsList>
        <TabsContent value="bookings"><BookingsList role="customer" /></TabsContent>
        <TabsContent value="birth"><BirthProfiles /></TabsContent>
        <TabsContent value="payments"><Payments /></TabsContent>
        <TabsContent value="safety"><Blocks /></TabsContent>
        <TabsContent value="privacy"><Privacy /></TabsContent>
      </Tabs>
    </div>
  );
}
