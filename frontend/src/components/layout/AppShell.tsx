import { Outlet, useLocation } from "react-router-dom"

import { Sidebar } from "./Sidebar"
import ThemeSwitcher from "../common/ThemeSwitcher"

export default function AppShell() {
  const location = useLocation()
  const isDeveloper = location.pathname.startsWith("/developer")

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 dark:bg-slate-950 dark:text-slate-100">
      <Sidebar />

      <div className="ml-64 min-h-screen">
        <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-slate-200 bg-white/95 px-6 backdrop-blur dark:border-slate-800 dark:bg-slate-950/95">
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-slate-400 dark:text-slate-500">
              {isDeveloper ? "Developer Console" : "Merchant Portal"}
            </p>
            <p className="text-sm font-medium text-slate-700 dark:text-slate-200">
              Revenue Recovery
            </p>
          </div>

          <div className="flex items-center gap-3">
            <div className="hidden items-center gap-2 rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-600 sm:flex dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300">
              <span className="h-2 w-2 rounded-full bg-blue-500" />
              Recovery Engine
            </div>

            <ThemeSwitcher />

            <div className="flex h-9 w-9 items-center justify-center rounded-full bg-slate-900 text-xs font-semibold text-white dark:bg-slate-700">
              NR
            </div>
          </div>
        </header>

        <main className="min-h-[calc(100vh-4rem)] bg-slate-50 px-6 py-6 dark:bg-slate-950">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
