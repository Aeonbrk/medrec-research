import {
  defaultViewState,
  densities,
  sections,
  sortFields,
  sortOrders,
  statusFilters,
  themes,
  type ViewState,
} from "@/lib/domain"

function enumValue<T extends string>(
  value: string | null,
  options: readonly T[],
  fallback: T
) {
  return options.includes(value as T) ? (value as T) : fallback
}

export function parseViewState(search: string): ViewState {
  const params = new URLSearchParams(search)
  return {
    section: enumValue(
      params.get("section"),
      sections,
      defaultViewState.section
    ),
    query: (params.get("q") ?? "").slice(0, 160),
    status: enumValue(
      params.get("status"),
      statusFilters,
      defaultViewState.status
    ),
    sort: enumValue(params.get("sort"), sortFields, defaultViewState.sort),
    order: enumValue(params.get("order"), sortOrders, defaultViewState.order),
    theme: enumValue(params.get("theme"), themes, defaultViewState.theme),
    density: enumValue(
      params.get("density"),
      densities,
      defaultViewState.density
    ),
  }
}

export function serializeViewState(state: ViewState) {
  const params = new URLSearchParams()
  if (state.section !== defaultViewState.section)
    params.set("section", state.section)
  if (state.query) params.set("q", state.query)
  if (state.status !== defaultViewState.status)
    params.set("status", state.status)
  if (state.sort !== defaultViewState.sort) params.set("sort", state.sort)
  if (state.order !== defaultViewState.order) params.set("order", state.order)
  if (state.theme !== defaultViewState.theme) params.set("theme", state.theme)
  if (state.density !== defaultViewState.density)
    params.set("density", state.density)
  const encoded = params.toString()
  return encoded ? `?${encoded}` : ""
}

export function mergeViewState(state: ViewState, patch: Partial<ViewState>) {
  return { ...state, ...patch }
}
