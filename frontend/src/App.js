import "@/App.css";
import { NativeShell } from "./lib/native";
import { NetworkBanner } from "./components/NetworkBanner";
import { BrowserRouter, Routes, Route, Navigate, useLocation } from "react-router-dom";
import { Toaster } from "./components/ui/sonner";
import { AuthProvider, useAuth } from "./context/AuthContext";
import { Header, Footer } from "./components/Layout";
import { Loading } from "./components/States";
import Landing from "./pages/Landing";
import Discover from "./pages/Discover";
import AstrologerPage from "./pages/AstrologerPage";
import { LoginPage, RegisterPage } from "./pages/Auth";
import Legal from "./pages/Legal";
import PayPage from "./pages/PayPage";
import BookingPage from "./pages/BookingPage";
import CustomerDashboard from "./pages/CustomerDashboard";
import AstrologerDashboard from "./pages/AstrologerDashboard";
import AdminDashboard from "./pages/AdminDashboard";

function Protected({ roles, children }) {
  const { user } = useAuth();
  const loc = useLocation();
  if (user === null) return <Loading text="Checking session" />;
  if (!user) return <Navigate to={`/login?next=${encodeURIComponent(loc.pathname)}`} replace />;
  if (roles && !roles.includes(user.role)) return <Navigate to="/" replace />;
  return children;
}

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <NativeShell />
        <div className="min-h-screen flex flex-col">
          <Header />
          <NetworkBanner />
          <main className="flex-1">
            <Routes>
              <Route path="/" element={<Landing />} />
              <Route path="/discover" element={<Discover />} />
              <Route path="/astrologers/:id" element={<AstrologerPage />} />
              <Route path="/login" element={<LoginPage />} />
              <Route path="/register" element={<RegisterPage />} />
              <Route path="/legal/:slug" element={<Legal />} />
              <Route path="/pay/:id" element={<Protected><PayPage /></Protected>} />
              <Route path="/bookings/:id" element={<Protected><BookingPage /></Protected>} />
              <Route path="/account" element={<Protected roles={["customer"]}><CustomerDashboard /></Protected>} />
              <Route path="/studio" element={<Protected roles={["astrologer"]}><AstrologerDashboard /></Protected>} />
              <Route path="/admin" element={<Protected roles={["admin"]}><AdminDashboard /></Protected>} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </main>
          <Footer />
        </div>
        <Toaster richColors position="top-center" />
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
