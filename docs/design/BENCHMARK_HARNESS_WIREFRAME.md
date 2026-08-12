# Benchmark Harness Wireframe

## Authority Boundary

This document owns the local harness composition, interaction states, and accessibility behavior. It does not define scientific readiness, authorize an action, or claim that a generated request was executed. `ProjectStatus` and `ActionDecision` remain the machine-readable authorities rendered by the interface.

The temporary action-first prototype from the 2026-07-10 brainstorm informed the composition only. This repository-owned contract replaces that temporary file as the durable design reference.

## First-Viewport Hierarchy

The first viewport answers four questions in this order:

1. What research stage is current?
2. What deterministic blocker controls progress?
3. How many baselines qualify in the same comparison scope?
4. What single action may be requested next?

Candidate summaries, shared lineage, evidence, and authority digests follow below. Shared implementation lineage must never be presented as an independent-reproduction count.

### Mobile

```text
+----------------------------------+
| MR  MedRec Research Harness      |
| current              valid until |
+----------------------------------+
| research stage rail (vertical)   |
|  o audit                         |
|  O current stage                 |
|  o next                          |
+----------------------------------+
| Current stage                    |
| qualified / 5                    |
+----------------------------------+
| Deterministic primary blocker    |
| category + reason code           |
+----------------------------------+
| Next permitted action            |
| [Generate action request]        |
+----------------------------------+
| Candidate table, flat rows       |
+----------------------------------+
| Shared-lineage table, flat rows  |
+----------------------------------+
| Snapshot authority summary       |
+----------------------------------+
```

### Desktop

```text
+------------------------------------------------------------------------+
| MR MedRec Research Harness                     condition / valid until |
+------------------------------------------------------------------------+
| audit - benchmark - lane - characterize - parallel - review - discover |
+-------------------+------------------------+---------------------------+
| Current stage     | Primary blocker        | Next permitted action     |
| qualified / 5     | category / reason      | [Generate request]        |
+-------------------+------------------------+---------------------------+
| Candidate comparison table                                           |
+------------------------------------------------------------------------+
| Shared-lineage table                                                  |
+------------------------------------------------------------------------+
| Review state | Snapshot SHA-256 | Authority digests                   |
+------------------------------------------------------------------------+
```

The stage rail is the interface's one visual signature. Its line, completed markers, and current gate encode actual sequence; it is not decorative.

## Data Mapping

| Interface region | Contract field |
| --- | --- |
| Condition and freshness | `ProjectStatus.condition`, `valid_until` |
| Stage rail and stage summary | `ProjectStatus.payload.stage` |
| Qualification progress | `ProjectStatus.payload.qualified_count` |
| Primary blocker | `ProjectStatus.primary_blocker` |
| Next action | `ProjectStatus.next_action`, `permitted_actions` |
| Candidate rows | `ProjectStatus.payload.candidates` |
| Lineage rows | `ProjectStatus.payload.shared_lineage` |
| Snapshot identity | `snapshot_sha256`, `authorities` |
| Allowed result | `ActionDecision.request.request_id`, `request_sha256` |
| Blocked result | `ActionDecision.reason_code` |

Dynamic strings are inserted as text nodes. Evidence becomes clickable only after a second browser-side absolute-HTTPS and approved-host check. Clickable evidence uses `rel="noopener noreferrer"`.

## Interaction States

| State | Enabled controls | Visible message | Live region | Focus target |
| --- | --- | --- | --- | --- |
| `loading` | None | Loading project status | Polite | Preserve current focus |
| `no-action` | None | Valid status has no permitted action | Polite | Preserve focus; summary after user retry |
| `readonly` | None | Status permits an action but requests are not enabled | Polite | Preserve focus; summary after user retry |
| `ready` | Generate request | Status and action authority are current | Polite | Action button remains reachable |
| `submitting` | None; duplicate submission locked | Generating content-addressed request | Polite | Keep action-button focus |
| `allowed` | None | Request generated and not executed | Polite | Result region |
| `blocked` | Reload status | Stable reason and recovery action | Assertive | Recovery button |
| `stale` | Reload status | Snapshot expired; actions closed | Assertive | Recovery button after user transition |
| `degraded` | Reload status | Snapshot unavailable for action | Assertive | Recovery button after user transition |
| `malformed` | Reload status | Contract shape unavailable | Assertive | Recovery button after user transition |
| `transport` | Reload status | Local harness unreachable | Assertive | Recovery button after user transition |

Automatic initial loading never steals focus. A user-initiated retry has a deterministic focus target. All action controls are at least 44 by 44 CSS pixels, and submission uses both a disabled control and an in-flight guard.

## HTTP Surface

| Route | Behavior |
| --- | --- |
| `GET /` | Package-owned HTML |
| `GET /assets/app.css` | Package-owned CSS |
| `GET /assets/app.js` | Package-owned JavaScript |
| `GET /api/status` | Current, stale, or degraded `ProjectStatus` projection |
| `GET /api/action-context` | Minimal request bootstrap projected from explicit authority |
| `POST /api/action-requests` | Pure U5 opaque `ActionRequestInput` evaluation through current Action Context |

The server binds only the literal IPv4 loopback address `127.0.0.1`. Every request requires exactly one `Host` equal to the bound literal and actual port. Action POST additionally requires exactly one same-origin `Origin`. These checks occur before body parsing.

Action POST is disabled by default. When enabled, it rejects transfer encoding, non-JSON content, missing or duplicate content length, and bodies larger than 16 KiB. `Expect: 100-continue` passes through the same checks before the server acknowledges the body. Errors use fixed public-safe reason codes and never echo headers, body content, filesystem paths, or raw request targets.

The server provides no CORS response, database, registry write, command runner, subprocess, SSH connection, or remote execution endpoint.

## Responsive Contract

The layout is mobile-first at 320 CSS pixels. The stage rail is vertical and tables become flat, rule-separated rows with visible field labels. At 48 rem the rail becomes horizontal and the command surface gains two columns. At 64 rem the command surface uses three columns and tables return to conventional column headers.

No viewport may introduce horizontal page scrolling, overlapping labels, clipped action text, or a touch target below 44 CSS pixels. Body text remains at least 1 rem and secondary text at least 0.875 rem.

## Visual Tokens

| Role | Value |
| --- | --- |
| Canvas | `#f3f6f5` |
| Surface | `#ffffff` |
| Ink | `#142126` |
| Muted | `#526169` |
| Line | `#c9d3d0` |
| Action | `#00695c` |
| Warning | `#8a4b08` |
| Blocked | `#a12d4a` |

The interface uses system sans for Chinese work text and system monospace only for identifiers and digests. It uses no gradient, decorative shadow, oversized hero, or card wall. Color is always paired with text or structure. Motion is nonessential and disabled under `prefers-reduced-motion`.

## Acceptance Checks

- Landmarks, heading order, captions, row and column headers, progress labels, and live regions remain programmatic.
- Keyboard focus is visible and action results receive deterministic focus.
- Text and controls meet WCAG AA contrast.
- Evidence metadata cannot inject markup or unapproved navigation.
- Desktop and mobile preserve stage, blocker, progress, and next action without overlap.
- Allowed output states only that a request was generated; it never says the action ran.
- Installed-package resources load without the repository working directory.
