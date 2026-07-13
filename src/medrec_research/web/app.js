"use strict";

const STAGES = [
  "audit_blocked",
  "benchmark_in_progress",
  "lane_proposed",
  "lane_characterizing",
  "parallel_eligible",
  "review_pending",
  "discovery_eligible",
];

const STAGE_LABELS = {
  audit_blocked: "审计阻塞",
  benchmark_in_progress: "基线复现中",
  lane_proposed: "首个复现通道待确认",
  lane_characterizing: "首通道稳定性刻画",
  parallel_eligible: "可进入并行复现",
  review_pending: "比较范围待审查",
  discovery_eligible: "可开始新方法研究",
};

const ACTION_LABELS = {
  refresh_authorization: "刷新动作授权",
  resolve_source_license: "补齐来源与许可证证据",
  advance_readiness: "推进准备度硬门",
  refresh_remote_preflight: "刷新远端预检",
  request_reproduction: "生成复现工作请求",
  submit_reproduction_evidence: "提交复现证据请求",
  request_next_lane: "生成下一复现通道请求",
  submit_human_review: "提交比较范围审查请求",
  begin_discovery: "生成新方法研究请求",
};

const APPROVED_EVIDENCE_HOSTS = new Set([
  "aclanthology.org",
  "arxiv.org",
  "dl.acm.org",
  "doi.org",
  "github.com",
  "ieeexplore.ieee.org",
  "openreview.net",
  "proceedings.mlr.press",
  "pubmed.ncbi.nlm.nih.gov",
  "raw.githubusercontent.com",
]);

const CREDENTIAL_QUERY_KEYS = new Set([
  "access_token",
  "api_key",
  "apikey",
  "auth",
  "authorization",
  "credential",
  "key",
  "password",
  "passwd",
  "secret",
  "sig",
  "signature",
  "token",
]);

const elements = Object.fromEntries(
  [
    "action-button",
    "action-heading",
    "action-region",
    "action-result",
    "action-value",
    "authority-value",
    "blocker-code",
    "blocker-value",
    "candidate-body",
    "condition-label",
    "freshness-label",
    "lineage-body",
    "live-assertive",
    "live-polite",
    "main-content",
    "page-title",
    "qualified-value",
    "readiness-progress",
    "request-id",
    "request-identity",
    "request-sha",
    "result-message",
    "retry-button",
    "review-value",
    "snapshot-value",
    "stage-track",
    "stage-value",
    "ui-message",
  ].map((id) => [id, document.getElementById(id)])
);

let currentRequestId = null;
let inFlight = false;

function isRecord(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function requiredString(value, field) {
  if (typeof value !== "string" || value.length === 0) {
    throw new Error(`malformed:${field}`);
  }
  return value;
}

function validateStatus(value) {
  if (!isRecord(value) || value.kind !== "project_status" || value.schema_version !== 1) {
    throw new Error("malformed:status");
  }
  requiredString(value.condition, "condition");
  requiredString(value.snapshot_sha256, "snapshot_sha256");
  if (!isRecord(value.payload) || !Array.isArray(value.payload.candidates)) {
    throw new Error("malformed:payload");
  }
  requiredString(value.payload.stage, "stage");
  if (!Number.isInteger(value.payload.qualified_count)) {
    throw new Error("malformed:qualified_count");
  }
  if (!Array.isArray(value.payload.shared_lineage) || !Array.isArray(value.authorities)) {
    throw new Error("malformed:collections");
  }
  if (!Array.isArray(value.permitted_actions) || !Array.isArray(value.blockers)) {
    throw new Error("malformed:gates");
  }
  return value;
}

function validateContext(value) {
  if (!isRecord(value) || value.kind !== "action_context" || value.schema_version !== 1) {
    throw new Error("malformed:context");
  }
  if (typeof value.enabled !== "boolean") {
    throw new Error("malformed:context");
  }
  const fields = value.enabled
    ? ["enabled", "kind", "request_id", "schema_version"]
    : ["enabled", "kind", "schema_version"];
  if (Object.keys(value).sort().join("|") !== fields.join("|")) {
    throw new Error("malformed:context_fields");
  }
  if (value.enabled) requiredString(value.request_id, "context.request_id");
  return value;
}

function validateHarnessState(value) {
  if (!isRecord(value) || value.kind !== "harness_state" || value.schema_version !== 1) {
    throw new Error("malformed:harness_state");
  }
  if (Object.keys(value).sort().join("|") !== ["action_context", "kind", "schema_version", "status"].join("|")) {
    throw new Error("malformed:harness_state_fields");
  }
  return {
    context: validateContext(value.action_context),
    status: validateStatus(value.status),
  };
}

function safeEvidenceUrl(value) {
  try {
    const decoded = decodeURIComponent(value);
    if ([...decoded].some((character) => character.charCodeAt(0) < 32 || character.charCodeAt(0) === 127)) {
      return null;
    }
    const parsed = new URL(value);
    if (
      parsed.protocol !== "https:" ||
      parsed.username ||
      parsed.password ||
      parsed.port ||
      parsed.hash ||
      !APPROVED_EVIDENCE_HOSTS.has(parsed.hostname)
    ) {
      return null;
    }
    for (const key of parsed.searchParams.keys()) {
      if (CREDENTIAL_QUERY_KEYS.has(key.toLowerCase())) return null;
    }
    return parsed.href;
  } catch {
    return null;
  }
}

function textCell(label, text) {
  const cell = document.createElement("td");
  cell.dataset.label = label;
  cell.textContent = text;
  return cell;
}

function gateCell(label, value) {
  const cell = document.createElement("td");
  cell.dataset.label = label;
  const badge = document.createElement("span");
  badge.className = `gate gate-${["pass", "fail"].includes(value) ? value : "unresolved"}`;
  badge.textContent = value;
  cell.append(badge);
  return cell;
}

function evidenceCell(label, evidence) {
  const cell = document.createElement("td");
  cell.dataset.label = label;
  const list = document.createElement("ul");
  list.className = "evidence-list";
  if (!Array.isArray(evidence)) throw new Error("malformed:evidence");
  evidence.forEach((item) => {
    if (!isRecord(item)) throw new Error("malformed:evidence_item");
    const name = requiredString(item.label, "evidence.label");
    const url = safeEvidenceUrl(requiredString(item.url, "evidence.url"));
    const row = document.createElement("li");
    if (url === null) {
      row.textContent = `${name}（链接不可用）`;
    } else {
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.target = "_blank";
      anchor.rel = "noopener noreferrer";
      anchor.textContent = name;
      row.append(anchor);
    }
    list.append(row);
  });
  cell.append(list);
  return cell;
}

function renderStage(stage) {
  const index = STAGES.indexOf(stage);
  if (index < 0) throw new Error("malformed:stage");
  elements["stage-track"].querySelectorAll("li").forEach((item, itemIndex) => {
    item.classList.toggle("is-complete", itemIndex < index);
    item.classList.toggle("is-current", itemIndex === index);
    if (itemIndex === index) item.setAttribute("aria-current", "step");
    else item.removeAttribute("aria-current");
  });
  elements["stage-value"].textContent = STAGE_LABELS[stage];
}

function renderCandidates(candidates) {
  elements["candidate-body"].replaceChildren();
  candidates.forEach((candidate) => {
    if (!isRecord(candidate)) throw new Error("malformed:candidate");
    const row = document.createElement("tr");
    const name = document.createElement("th");
    name.scope = "row";
    name.textContent = requiredString(candidate.display_name, "candidate.display_name");
    row.append(
      name,
      gateCell("准备度", requiredString(candidate.readiness, "candidate.readiness")),
      gateCell("来源", requiredString(candidate.source_gate, "candidate.source_gate")),
      gateCell("许可证", requiredString(candidate.license_gate, "candidate.license_gate")),
      evidenceCell("证据", candidate.evidence)
    );
    elements["candidate-body"].append(row);
  });
}

function renderLineage(lineage) {
  elements["lineage-body"].replaceChildren();
  lineage.forEach((item) => {
    if (!isRecord(item) || !Array.isArray(item.candidate_ids)) {
      throw new Error("malformed:lineage");
    }
    const repository = safeEvidenceUrl(
      requiredString(item.upstream_repository, "lineage.upstream_repository")
    );
    const row = document.createElement("tr");
    const layer = document.createElement("th");
    layer.scope = "row";
    layer.textContent = requiredString(item.layer, "lineage.layer");
    const repositoryCell = document.createElement("td");
    repositoryCell.dataset.label = "上游仓库";
    if (repository === null) {
      repositoryCell.textContent = "链接不可用";
    } else {
      const anchor = document.createElement("a");
      anchor.href = repository;
      anchor.target = "_blank";
      anchor.rel = "noopener noreferrer";
      anchor.textContent = new URL(repository).hostname;
      repositoryCell.append(anchor);
    }
    row.append(
      layer,
      repositoryCell,
      textCell("候选", item.candidate_ids.map((value) => requiredString(value, "candidate_id")).join("、")),
      evidenceCell("证据", item.evidence)
    );
    elements["lineage-body"].append(row);
  });
}

function renderStatus(status) {
  renderStage(status.payload.stage);
  renderCandidates(status.payload.candidates);
  renderLineage(status.payload.shared_lineage);
  elements["condition-label"].textContent = status.condition;
  elements["freshness-label"].textContent = `有效至 ${requiredString(status.valid_until, "valid_until")}`;
  const qualified = status.payload.qualified_count;
  elements["qualified-value"].textContent = `${qualified} / 6`;
  elements["readiness-progress"].value = qualified;
  elements["readiness-progress"].textContent = `${qualified} / 6`;
  elements["review-value"].textContent = requiredString(status.payload.review_state, "review_state");
  elements["snapshot-value"].textContent = status.snapshot_sha256;
  elements["authority-value"].textContent = status.authorities
    .map((item) => `${requiredString(item.authority_id, "authority_id")}:${requiredString(item.sha256, "authority.sha256")}`)
    .join(" · ");

  if (status.primary_blocker === null) {
    elements["blocker-value"].textContent = "无当前阻塞";
    elements["blocker-code"].textContent = "";
  } else {
    if (!isRecord(status.primary_blocker)) throw new Error("malformed:blocker");
    const category = requiredString(status.primary_blocker.category, "blocker.category");
    const candidate = status.primary_blocker.candidate_id;
    elements["blocker-value"].textContent = candidate ? `${category} · ${candidate}` : category;
    elements["blocker-code"].textContent = requiredString(
      status.primary_blocker.reason_code,
      "blocker.reason_code"
    );
  }
}

function announce(message, assertive) {
  const target = elements[assertive ? "live-assertive" : "live-polite"];
  target.textContent = "";
  window.setTimeout(() => {
    target.textContent = message;
  }, 0);
}

function setState(state, message, { announceChange = true, focus = null } = {}) {
  document.body.dataset.uiState = state;
  elements["ui-message"].textContent = message;
  elements["main-content"].setAttribute("aria-busy", state === "loading" ? "true" : "false");
  elements["action-region"].setAttribute("aria-busy", state === "submitting" ? "true" : "false");
  if (announceChange) announce(message, ["blocked", "stale", "degraded", "malformed", "transport"].includes(state));
  if (focus) focus.focus();
}

function resetAction() {
  inFlight = false;
  elements["action-button"].disabled = true;
  elements["action-button"].textContent = "等待状态";
  elements["retry-button"].hidden = true;
  elements["action-result"].hidden = true;
  elements["request-identity"].hidden = true;
  currentRequestId = null;
}

function configureAction(status, context, focusAfter) {
  const next = status.next_action;
  if (status.condition === "stale") {
    elements["action-value"].textContent = "状态已过期";
    elements["retry-button"].hidden = false;
    setState("stale", "项目状态已过期；动作请求保持关闭。", { focus: focusAfter ? elements["retry-button"] : null });
    return;
  }
  if (status.condition === "degraded") {
    elements["action-value"].textContent = "状态不可用于动作";
    elements["retry-button"].hidden = false;
    setState("degraded", "项目状态已降级；动作请求保持关闭。", { focus: focusAfter ? elements["retry-button"] : null });
    return;
  }
  if (next === null) {
    elements["action-value"].textContent = "当前没有允许动作";
    setState("no-action", "状态有效，当前没有允许请求的动作。", { focus: focusAfter ? elements["page-title"] : null });
    return;
  }
  if (!isRecord(next)) throw new Error("malformed:next_action");
  const actionId = requiredString(next.action_id, "next_action.action_id");
  const label = ACTION_LABELS[actionId] || requiredString(next.label, "next_action.label");
  elements["action-value"].textContent = label;
  elements["action-button"].textContent = label;
  if (!context.enabled) {
    elements["retry-button"].hidden = false;
    setState("readonly", "状态允许下一步，但当前动作上下文不可用；可重新载入。", {
      focus: focusAfter ? elements["retry-button"] : null,
    });
    return;
  }
  currentRequestId = requiredString(context.request_id, "context.request_id");
  elements["action-button"].disabled = false;
  setState("ready", "状态与动作授权均为当前版本。", { focus: focusAfter ? elements["page-title"] : null });
}

async function fetchJson(path, options) {
  const response = await fetch(path, { cache: "no-store", ...options });
  if (!response.ok) throw new Error(`transport:${response.status}`);
  return response.json();
}

async function loadHarness({ focusAfter = false } = {}) {
  resetAction();
  setState("loading", "正在载入项目状态。", { announceChange: false });
  try {
    const state = validateHarnessState(await fetchJson("/api/harness-state"));
    renderStatus(state.status);
    configureAction(state.status, state.context, focusAfter);
  } catch (error) {
    const malformed = error instanceof Error && error.message.startsWith("malformed:");
    const state = malformed ? "malformed" : "transport";
    const message = malformed
      ? "项目状态格式不可用；动作请求保持关闭。"
      : "无法连接本机 harness；动作请求保持关闭。";
    elements["condition-label"].textContent = "unavailable";
    elements["freshness-label"].textContent = "";
    elements["action-value"].textContent = "不可用";
    elements["retry-button"].hidden = false;
    setState(state, message, { focus: focusAfter ? elements["retry-button"] : null });
  }
}

async function requestAction() {
  if (inFlight || currentRequestId === null) return;
  inFlight = true;
  elements["action-button"].disabled = true;
  elements["retry-button"].hidden = true;
  setState("submitting", "正在生成内容寻址动作请求。", { focus: elements["action-button"] });
  const request = {
    schema_version: 1,
    kind: "action_request_input",
    request_id: currentRequestId,
  };
  try {
    const decision = await fetchJson("/api/action-requests", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    });
    if (!isRecord(decision) || decision.kind !== "action_decision" || decision.schema_version !== 1) {
      throw new Error("malformed:decision");
    }
    const reason = requiredString(decision.reason_code, "decision.reason_code");
    elements["action-result"].hidden = false;
    if (decision.status === "allowed" && isRecord(decision.request)) {
      elements["result-message"].textContent = "动作请求已生成，尚未执行。";
      elements["request-id"].textContent = requiredString(decision.request.request_id, "request_id");
      elements["request-sha"].textContent = requiredString(decision.request.request_sha256, "request_sha256");
      elements["request-identity"].hidden = false;
      setState("allowed", "动作请求已生成，尚未执行。", { focus: elements["action-result"] });
      return;
    }
    if (decision.status !== "blocked" || decision.request !== null) {
      throw new Error("malformed:decision_shape");
    }
    elements["result-message"].textContent = `请求被 gate 阻塞：${reason}`;
    elements["retry-button"].hidden = false;
    setState("blocked", "动作请求被 gate 阻塞；请重新载入当前状态。", { focus: elements["retry-button"] });
  } catch (error) {
    const malformed = error instanceof Error && error.message.startsWith("malformed:");
    elements["action-result"].hidden = false;
    elements["result-message"].textContent = malformed ? "动作决策格式不可用。" : "动作请求传输失败。";
    elements["retry-button"].hidden = false;
    setState(malformed ? "malformed" : "transport", elements["result-message"].textContent, {
      focus: elements["retry-button"],
    });
  }
}

elements["action-button"].addEventListener("click", requestAction);
elements["retry-button"].addEventListener("click", () => loadHarness({ focusAfter: true }));
loadHarness();
