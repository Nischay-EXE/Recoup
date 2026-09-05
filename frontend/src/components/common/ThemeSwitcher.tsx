import {
  Monitor,
  Moon,
  Sun,
} from "lucide-react"

import { useTheme, type Theme } from "../../app/ThemeProvider"

const themes: {
  value: Theme
  label: string
  icon: typeof Sun
}[] = [
  {
    value: "light",
    label: "Light",
    icon: Sun,
  },
  {
    value: "dark",
    label: "Dark",
    icon: Moon,
  },
  {
    value: "system",
    label: "System",
    icon: Monitor,
  },
]

export default function ThemeSwitcher() {
  const { theme, setTheme } = useTheme()

  return (
    <div className="flex items-center rounded-lg border border-slate-200 bg-slate-50 p-1 dark:border-slate-700 dark:bg-slate-900">
      {themes.map(({ value, label, icon: Icon }) => {
        const active = theme === value

        return (
          <button
            key={value}
            type="button"
            onClick={() => setTheme(value)}
            title={`${label} theme`}
            aria-label={`${label} theme`}
            className={[
              "flex h-8 items-center gap-1.5 rounded-md px-2.5 text-xs font-medium transition-all",
              active
                ? "bg-white text-slate-900 shadow-sm dark:bg-slate-700 dark:text-white"
                : "text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-100",
            ].join(" ")}
          >
            <Icon size={14} />

            <span className="hidden sm:inline">
              {label}
            </span>
          </button>
        )
      })}
    </div>
  )
}
