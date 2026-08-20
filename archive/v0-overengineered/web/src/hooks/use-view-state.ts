import * as React from "react"

import type { ViewState } from "@/lib/domain"
import {
  mergeViewState,
  parseViewState,
  serializeViewState,
} from "@/lib/query-state"

let currentSearch = typeof window !== "undefined" ? window.location.search : ""
const listeners = new Set<() => void>()

function subscribe(callback: () => void) {
  listeners.add(callback)
  const onPopState = () => {
    currentSearch = window.location.search
    callback()
  }
  window.addEventListener("popstate", onPopState)
  return () => {
    listeners.delete(callback)
    window.removeEventListener("popstate", onPopState)
  }
}

function getSnapshot() {
  if (typeof window !== "undefined") {
    currentSearch = window.location.search
  }
  return currentSearch
}

function getServerSnapshot() {
  return ""
}

export function useViewState() {
  const search = React.useSyncExternalStore(
    subscribe,
    getSnapshot,
    getServerSnapshot
  )
  const state = React.useMemo(() => parseViewState(search), [search])

  const update = React.useCallback(
    (patch: Partial<ViewState>) => {
      const current = parseViewState(window.location.search)
      const next = mergeViewState(current, patch)
      const nextSearch = serializeViewState(next)
      if (nextSearch !== window.location.search) {
        window.history.replaceState(
          null,
          "",
          `${window.location.pathname}${nextSearch}`
        )
        currentSearch = nextSearch
        listeners.forEach((listener) => listener())
      }
    },
    []
  )

  return [state, update] as const
}
