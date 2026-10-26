import { NavLink, Outlet, useNavigate } from "react-router-dom";
import {
  Bell,
  Calendar,
  ClipboardList,
  Clock,
  FileText,
  Gavel,
  LayoutDashboard,
  Map,
  Menu,
  ScrollText,
  Settings,
  Shield,
  Users,
} from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { useAuth } from "@/store/auth";
import { useUi } from "@/store/ui";
import { api, DEMO_ROLES, ROLE_LABELS } from "@/lib/api";
import { loginAsDemo } from "@/store/auth";
import { Safeguard } from "./Safeguard";
import { CommandPalette } from "@/components/CommandPalette";
import { DemoTour } from "@/components/DemoTour";
import { cn } from "@/lib/cn";
import { useEffect } from "react";

const NAV = [
  { to: "/app", label: "Dashboard", icon: LayoutDashboard },
  { to: "/app/applications", label: "Applications", icon: ClipboardList },
  { to: "/app/deadlines", label: "Deadlines", icon: Clock },
  { to: "/app/calendar", label: "Working calendar", icon: Calendar },
  { to: "/app/evc", label: "EVC", icon: Map },
  { to: "/app/undertakings", label: "Undertakings", icon: FileText },
  { to: "/app/documents", label: "Documents", icon: ScrollText },
  { to: "/app/notifications", label: "Notifications", icon: Bell },
  { to: "/app/reports", label: "Reports", icon: Gavel },
  { to: "/app/audit", label: "Audit trail", icon: Shield },
];

export function AppShell() {
  const user = useAuth((s) => s.user)!;
  const logout = useAuth((s) => s.logout);
  const { sidebarOpen, toggleSidebar, setCommand, setTour } = useUi();
  const nav = useNavigate();
  const notes = useQuery({
    queryKey: ["notes-unread"],
    queryFn: () => api.get<{ unread: number }>("/api/v1/notifications?unread=true"),
    refetchInterval: 15000,
  });

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setCommand(true);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [setCommand]);

  const admin = user.role === "super_admin" || user.role === "bureau_officer";

  return (
    <div className="min-h-screen bg-canvas">
      <CommandPalette />
      <DemoTour />
      <div className="flex">
        <aside
          className={cn(
            "sticky top-0 h-screen border-r border-line bg-white/80 backdrop-blur transition-all",
            sidebarOpen ? "w-64 p-4" : "w-0 overflow-hidden p-0",
          )}
        >
          <div className="mb-6 flex items-center gap-2 font-extrabold">
            <span className="grid h-9 w-9 place-items-center rounded-xl bg-ink text-white">AF</span>
            ApproveFlow
          </div>
          <nav className="space-y-1 text-sm">
            {NAV.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === "/app"}
                className={({ isActive }) =>
                  cn("flex items-center gap-2 rounded-xl px-3 py-2", isActive ? "bg-canvas font-semibold" : "text-slate-600")
                }
              >
                <item.icon size={16} />
                {item.label}
                {item.to === "/app/notifications" && (notes.data?.unread ?? 0) > 0 && (
                  <span className="ml-auto rounded-full bg-rose-500 px-1.5 text-[10px] text-white">{notes.data?.unread}</span>
                )}
              </NavLink>
            ))}
            {admin && (
              <>
                <p className="px-3 pt-4 text-xs uppercase tracking-wide text-slate-400">Admin</p>
                <NavLink to="/app/admin/accounts" className="flex items-center gap-2 rounded-xl px-3 py-2 text-slate-600">
                  <Users size={16} /> User accounts
                </NavLink>
                <NavLink to="/app/admin/rules" className="flex items-center gap-2 rounded-xl px-3 py-2 text-slate-600">
                  <Settings size={16} /> Workflow rules
                </NavLink>
                {user.role === "super_admin" && (
                  <NavLink to="/app/admin/alerts" className="flex items-center gap-2 rounded-xl px-3 py-2 text-slate-600">
                    <Bell size={16} /> Alert rules
                  </NavLink>
                )}
                <NavLink to="/app/admin/monitor" className="flex items-center gap-2 rounded-xl px-3 py-2 text-slate-600">
                  <Shield size={16} /> Monitoring
                </NavLink>
              </>
            )}
          </nav>
        </aside>
        <div className="min-w-0 flex-1">
          <header className="sticky top-0 z-30 flex items-center gap-3 border-b border-line bg-white/70 px-4 py-3 backdrop-blur">
            <button type="button" onClick={toggleSidebar} className="rounded-lg p-2 hover:bg-canvas" aria-label="Toggle sidebar">
              <Menu size={18} />
            </button>
            <button type="button" onClick={() => setCommand(true)} className="hidden rounded-xl border border-line px-3 py-1.5 text-sm text-slate-500 md:block">
              Search applications · Ctrl+K
            </button>
            <div className="ml-auto flex items-center gap-2">
              <select
                className="rounded-xl border border-line bg-white px-2 py-1.5 text-xs"
                value={user.email}
                onChange={async (e) => {
                  await loginAsDemo(e.target.value);
                  nav("/app");
                }}
                aria-label="Demo role switcher"
              >
                {DEMO_ROLES.map((r) => (
                  <option key={r.email} value={r.email}>
                    Demo: {r.label}
                  </option>
                ))}
              </select>
              <button type="button" onClick={() => setTour(true)} className="rounded-xl border border-line px-3 py-1.5 text-xs">
                Demo tour
              </button>
              <button type="button" onClick={() => nav("/app/notifications")} className="relative rounded-xl border border-line p-2">
                <Bell size={16} />
                {(notes.data?.unread ?? 0) > 0 && <span className="absolute right-1 top-1 h-2 w-2 rounded-full bg-rose-500" />}
              </button>
              <div className="text-right text-xs">
                <div className="font-semibold">{user.full_name}</div>
                <div className="text-slate-500">{ROLE_LABELS[user.role] ?? user.role}</div>
              </div>
              <button type="button" className="text-xs text-slate-500" onClick={() => { logout(); nav("/"); }}>
                Sign out
              </button>
            </div>
          </header>
          <main className="p-4 md:p-6">
            <p className="mb-3 text-xs text-amber-700">Simulated demo data.</p>
            <Outlet />
          </main>
          <footer className="px-6 pb-6">
            <Safeguard compact />
          </footer>
        </div>
      </div>
    </div>
  );
}
