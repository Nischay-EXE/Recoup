import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react"

export type Theme = "system" | "light" | "dark"

type ThemeContextValue = {
  theme: Theme
  setTheme: (theme: Theme) => void
  resolvedTheme: "light" | "dark"
}

const ThemeContext = createContext<ThemeContextValue | undefined>(
  undefined,
)

function getStoredTheme(): Theme {
  const stored = localStorage.getItem("revenue-recovery-theme")

  if (
    stored === "light" ||
    stored === "dark" ||
    stored === "system"
  ) {
    return stored
  }

  return "system"
}

function getSystemTheme(): "light" | "dark" {
  return window.matchMedia("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light"
}

function applyTheme(theme: "light" | "dark") {
  document.documentElement.classList.toggle("dark", theme === "dark")
}

export function ThemeProvider({
  children,
}: {
  children: ReactNode
}) {
  const [theme, setThemeState] = useState<Theme>(() => {
    if (typeof window === "undefined") {
      return "system"
    }

    return getStoredTheme()
  })

  const [resolvedTheme, setResolvedTheme] = useState<
    "light" | "dark"
  >(() => {
    if (typeof window === "undefined") {
      return "light"
    }

    const stored = getStoredTheme()

    return stored === "system"
      ? getSystemTheme()
      : stored
  })

  useEffect(() => {
    const mediaQuery = window.matchMedia(
      "(prefers-color-scheme: dark)",
    )

    const updateTheme = () => {
      const resolved =
        theme === "system"
          ? mediaQuery.matches
            ? "dark"
            : "light"
          : theme

      setResolvedTheme(resolved)
      applyTheme(resolved)
    }

    updateTheme()

    mediaQuery.addEventListener("change", updateTheme)

    return () => {
      mediaQuery.removeEventListener("change", updateTheme)
    }
  }, [theme])

  const setTheme = (nextTheme: Theme) => {
    localStorage.setItem(
      "revenue-recovery-theme",
      nextTheme,
    )

    setThemeState(nextTheme)
  }

  return (
    <ThemeContext.Provider
      value={{
        theme,
        setTheme,
        resolvedTheme,
      }}
    >
      {children}
    </ThemeContext.Provider>
  )
}

export function useTheme() {
  const context = useContext(ThemeContext)

  if (!context) {
    throw new Error(
      "useTheme must be used inside ThemeProvider",
    )
  }

  return context
}
