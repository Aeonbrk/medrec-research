import * as React from "react"

import type { ViewState } from "@/lib/domain"
import {
  mergeViewState,
  parseViewState,
  serializeViewState,
} from "@/lib/query-state"

export function useViewState() {
  const [state, setState] = React.useState<ViewState>(() =>
    parseViewState(window.location.search)
  )

  React.useEffect(() => {
    const restore = () => setState(parseViewState(window.location.search))
    window.addEventListener("popstate", restore)
    return () => window.removeEventListener("popstate", restore)
  }, [])

  const update = React.useCallback((patch: Partial<ViewState>) => {
    setState((current) => {
      const next = mergeViewState(current, patch)
      const search = serializeViewState(next)
      window.history.replaceState(
        null,
        "",
        `${window.location.pathname}${search}`
      )
      return next
    })
  }, [])

  return [state, update] as const
}
