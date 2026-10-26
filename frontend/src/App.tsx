import { lazy, Suspense } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import { useAuth } from "@/store/auth";
import { AppShell } from "@/components/layout/AppShell";
import { Toasts } from "@/components/ui/Toast";

const Landing = lazy(() => import("@/pages/Landing"));
const Login = lazy(() => import("@/pages/Login"));
const Signup = lazy(() => import("@/pages/Signup"));
const ResetPassword = lazy(() => import("@/pages/ResetPassword"));
const Dashboard = lazy(() => import("@/pages/Dashboard"));
const Applications = lazy(() => import("@/pages/Applications"));
const ApplicationDetail = lazy(() => import("@/pages/ApplicationDetail"));
const NewApplication = lazy(() => import("@/pages/NewApplication"));
const Deadlines = lazy(() => import("@/pages/Deadlines"));
const Calendar = lazy(() => import("@/pages/Calendar"));
const Evc = lazy(() => import("@/pages/Evc"));
const Undertakings = lazy(() => import("@/pages/Undertakings"));
const Documents = lazy(() => import("@/pages/Documents"));
const Notifications = lazy(() => import("@/pages/Notifications"));
const Reports = lazy(() => import("@/pages/Reports"));
const Audit = lazy(() => import("@/pages/Audit"));
const AdminAccounts = lazy(() => import("@/pages/AdminAccounts"));
const AdminRules = lazy(() => import("@/pages/AdminRules"));
const AdminAlerts = lazy(() => import("@/pages/AdminAlerts"));
const AdminMonitor = lazy(() => import("@/pages/AdminMonitor"));
const Dev3D = lazy(() => import("@/pages/Dev3D"));

function Guard({ children, roles }: { children: React.ReactNode; roles?: string[] }) {
  const user = useAuth((s) => s.user);
  if (!user) return <Navigate to="/login" replace />;
  if (roles && !roles.includes(user.role) && user.role !== "super_admin") return <Navigate to="/app" replace />;
  return <>{children}</>;
}

function Fallback() {
  return (
    <div className="flex min-h-[40vh] items-center justify-center text-sm text-slate-500">
      Loading ApproveFlow…
    </div>
  );
}

export default function App() {
  const location = useLocation();
  return (
    <>
      <Toasts />
      <Suspense fallback={<Fallback />}>
        <AnimatePresence mode="wait">
          <motion.div
            key={location.pathname.split("/")[1] || "home"}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -6 }}
            transition={{ duration: 0.28 }}
          >
            <Routes location={location}>
              <Route path="/" element={<Landing />} />
              <Route path="/login" element={<Login />} />
              <Route path="/signup" element={<Signup />} />
              <Route path="/reset-password" element={<ResetPassword />} />
              <Route path="/dev/3d" element={<Dev3D />} />
              <Route
                path="/app"
                element={
                  <Guard>
                    <AppShell />
                  </Guard>
                }
              >
                <Route index element={<Dashboard />} />
                <Route path="applications" element={<Applications />} />
                <Route path="applications/new" element={<NewApplication />} />
                <Route path="applications/:id" element={<ApplicationDetail />} />
                <Route path="deadlines" element={<Deadlines />} />
                <Route path="calendar" element={<Calendar />} />
                <Route path="evc" element={<Evc />} />
                <Route path="undertakings" element={<Undertakings />} />
                <Route path="documents" element={<Documents />} />
                <Route path="notifications" element={<Notifications />} />
                <Route path="reports" element={<Reports />} />
                <Route path="audit" element={<Audit />} />
                <Route
                  path="admin/accounts"
                  element={
                    <Guard roles={["super_admin", "bureau_officer"]}>
                      <AdminAccounts />
                    </Guard>
                  }
                />
                <Route
                  path="admin/rules"
                  element={
                    <Guard roles={["super_admin", "bureau_officer"]}>
                      <AdminRules />
                    </Guard>
                  }
                />
                <Route
                  path="admin/alerts"
                  element={
                    <Guard roles={["super_admin"]}>
                      <AdminAlerts />
                    </Guard>
                  }
                />
                <Route
                  path="admin/monitor"
                  element={
                    <Guard roles={["super_admin", "bureau_officer"]}>
                      <AdminMonitor />
                    </Guard>
                  }
                />
              </Route>
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </motion.div>
        </AnimatePresence>
      </Suspense>
    </>
  );
}
