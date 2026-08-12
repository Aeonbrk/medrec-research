import * as React from "react"

import type { Theme } from "@/lib/domain"

const colorSchemeQuery = "(prefers-color-scheme: dark)"

function resolvedTheme(theme: Theme) {
  if (theme !== "system") return theme
  return window.matchMedia(colorSchemeQuery).matches ? "dark" : "light"
}

function applyTheme(theme: Theme) {
  const root = document.documentElement
  const resolved = resolvedTheme(theme)
  root.classList.remove("light", "dark")
  root.classList.add(resolved)
  root.style.colorScheme = resolved
}

export function ThemeProvider({
  children,
  theme,
}: {
  children: React.ReactNode
  theme: Theme
}) {
  React.useLayoutEffect(() => {
    applyTheme(theme)
    if (theme !== "system") return

    const query = window.matchMedia(colorSchemeQuery)
    const update = () => applyTheme("system")
    query.addEventListener("change", update)
    return () => query.removeEventListener("change", update)
  }, [theme])

  return children
}
