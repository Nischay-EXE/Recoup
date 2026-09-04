import {
  Activity,
  AlertTriangle,
  BarChart3,
  BriefcaseBusiness,
  Layers3,
  ChevronDown,
  Code2,
  CreditCard,

  HeartPulse,
  LayoutDashboard,
  ListChecks,
  Settings2,
  ShieldCheck,
  Terminal,
} from "lucide-react"
import { NavLink, useLocation } from "react-router-dom"

type NavItem = {
  label: string
  path: string
  icon: React.ComponentType<{ size?: number; strokeWidth?: number }>
}

const merchantItems: NavItem[] = [
  {
    label: "Overview",
    path: "/merchant",
    icon: LayoutDashboard,
  },
  {
    label: "Recovery Cases",
    path: "/merchant/cases",
    icon: BriefcaseBusiness,
  },
  {
    label: "Escalations",
    path: "/merchant/escalations",
    icon: AlertTriangle,
  },
  {
    label: "Batches",
    path: "/merchant/batches",
    icon: Layers3,
  },
]

const developerItems: NavItem[] = [
  {
    label: "Overview",
    path: "/developer",
    icon: LayoutDashboard,
  },
  {
    label: "Events",
    path: "/developer/events",
    icon: Activity,
  },
  {
    label: "AI Decisions",
    path: "/developer/decisions",
    icon: ShieldCheck,
  },
  {
    label: "Executions",
    path: "/developer/executions",
    icon: Terminal,
  },
  {
    label: "Cases",
    path: "/developer/cases",
    icon: ListChecks,
  },
  {
    label: "Escalations",
    path: "/developer/escalations",
    icon: AlertTriangle,
  },
  {
    label: "System Health",
    path: "/developer/health",
    icon: HeartPulse,
  },
]

function SidebarLink({ item }: { item: NavItem }) {
  return (
    <NavLink
      to={item.path}
      end={item.path === "/merchant" || item.path === "/developer"}
      className={({ isActive }) =>
        [
          "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition",
          isActive
            ? "bg-white/10 text-white"
            : "text-slate-400 hover:bg-white/5 hover:text-white",
        ].join(" ")
      }
    >
      <item.icon size={17} strokeWidth={1.8} />
      <span>{item.label}</span>
    </NavLink>
  )
}

export function Sidebar() {
  const location = useLocation()
  const isDeveloper = location.pathname.startsWith("/developer")

  const items = isDeveloper ? developerItems : merchantItems

  return (
    <aside className="fixed inset-y-0 left-0 z-40 flex w-64 flex-col bg-[#111827] text-white">
      <div className="flex h-16 items-center border-b border-white/10 px-5">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-600">
          <CreditCard size={19} />
        </div>

        <div className="ml-3">
          <div className="text-sm font-semibold">Revenue Recovery</div>
          <div className="text-xs text-slate-400">
            Recovery Engine
          </div>
        </div>
      </div>

      <div className="border-b border-white/10 px-4 py-4">
        <div className="mb-2 px-2 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
          Workspace
        </div>

        <div className="flex items-center justify-between rounded-lg bg-white/5 px-3 py-2.5">
          <div className="flex items-center gap-3">
            {isDeveloper ? (
              <Code2 size={17} className="text-blue-400" />
            ) : (
              <BarChart3 size={17} className="text-blue-400" />
            )}

            <div>
              <div className="text-sm font-medium">
                {isDeveloper ? "Developer Console" : "Merchant Portal"}
              </div>
              <div className="text-[11px] text-slate-500">
                {isDeveloper ? "Engine control plane" : "Business operations"}
              </div>
            </div>
          </div>

          <ChevronDown size={15} className="text-slate-500" />
        </div>
      </div>

      <nav className="flex-1 overflow-y-auto px-4 py-5">
        <div className="mb-2 px-2 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
          {isDeveloper ? "Developer" : "Merchant"}
        </div>

        <div className="space-y-1">
          {items.map((item) => (
            <SidebarLink key={item.path} item={item} />
          ))}
        </div>
      </nav>

      <div className="border-t border-white/10 p-4">
        <NavLink
          to={isDeveloper ? "/merchant" : "/developer"}
          className="flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm text-slate-400 transition hover:bg-white/5 hover:text-white"
        >
          {isDeveloper ? (
            <BarChart3 size={17} strokeWidth={1.8} />
          ) : (
            <Code2 size={17} strokeWidth={1.8} />
          )}

          <span>
            {isDeveloper
              ? "Switch to Merchant"
              : "Developer Console"}
          </span>
        </NavLink>

        <div className="mt-2 flex items-center gap-3 rounded-lg px-3 py-2.5 text-slate-500">
          <Settings2 size={17} strokeWidth={1.8} />
          <span className="text-sm">Settings</span>
        </div>
      </div>
    </aside>
  )
}