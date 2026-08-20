import AxeBuilder from "@axe-core/playwright"
import { expect, test, type Page } from "@playwright/test"

async function waitForTheme(page: Page, theme: string) {
  await expect(page.locator("html")).toHaveClass(new RegExp(theme))
  // Theme tokens transition on many controls. Wait for the browser's actual
  // transition set so axe samples the settled palette, not an interpolated one.
  await page.evaluate(async () => {
    const animations = document.getAnimations({ subtree: true })
    await Promise.all(
      animations.map((animation) => animation.finished.catch(() => undefined))
    )
  })
  await page.evaluate(
    () => new Promise<void>((resolve) => requestAnimationFrame(() => resolve()))
  )
}

const finalFive = ["gamenet", "safedrug", "molerec", "retain", "leap-safedrug"]
const closedActions = [
  "refresh_authorization",
  "resolve_source_license",
  "advance_readiness",
  "refresh_remote_preflight",
  "request_reproduction",
  "submit_reproduction_evidence",
  "request_next_lane",
  "submit_human_review",
  "begin_discovery",
]

test("production desktop renders API data, URL state, themes and passes axe", async ({
  page,
  isMobile,
}) => {
  test.skip(isMobile, "desktop scenario")
  await page.goto("/?section=overview&theme=light")
  await expect(
    page.getByRole("heading", { name: "当前研究状态，一屏完成可信判断" })
  ).toBeVisible()
  await expect(
    page.getByRole("region", { name: "研究阶段与快照" }).locator("code")
  ).toHaveText(/^[a-f0-9]{64}$/)

  const lightAccessibility = await new AxeBuilder({ page }).analyze()
  expect(lightAccessibility.violations).toEqual([])

  await page.getByRole("button", { name: "候选基线" }).click()
  await expect(page).toHaveURL(/section=candidates/)
  await page.getByRole("textbox", { name: "全局搜索" }).fill("molerec")
  await expect(
    page.getByRole("row", { name: /^molerec molerec/ })
  ).toBeVisible()
  await expect(page.getByRole("row", { name: /^gamenet gamenet/ })).toHaveCount(
    0
  )
  await expect(page).toHaveURL(/q=molerec/)
  const evidence = page.getByRole("button", { name: "展开公开证据" })
  await evidence.focus()
  await page.keyboard.press("Enter")
  await expect(page.getByRole("link", { name: /molerec-source/ })).toBeVisible()

  await page.getByRole("button", { name: "深色" }).click()
  await waitForTheme(page, "dark")
  await expect(page).toHaveURL(/theme=dark/)
  await page.reload()
  await waitForTheme(page, "dark")
  await expect(page.getByRole("textbox", { name: "全局搜索" })).toHaveValue(
    "molerec"
  )

  const accessibility = await new AxeBuilder({ page }).analyze()
  expect(accessibility.violations).toEqual([])
})

test("pending workbench replays opaque requests through durable execution and SSE", async ({
  page,
  isMobile,
}) => {
  test.skip(isMobile, "desktop pending workbench scenario")
  let eventStreams = 0
  page.on("request", (request) => {
    if (new URL(request.url()).pathname === "/api/execution-events") {
      eventStreams += 1
    }
  })
  await page.goto("/?theme=light")
  await expect(
    page.getByRole("heading", { name: "待决工作台" }).last()
  ).toBeVisible()
  await expect(page.getByText("SSE live", { exact: true })).toBeVisible()
  await page.waitForTimeout(1_800)
  expect(eventStreams).toBe(1)

  const queue = page.getByRole("region", { name: "待决队列" })
  const detail = page.getByRole("region", { name: "待决详情" })
  const actions = page.getByRole("complementary", { name: "决策操作" })
  const [queueBox, detailBox, actionsBox] = await Promise.all([
    queue.boundingBox(),
    detail.boundingBox(),
    actions.boundingBox(),
  ])
  if (!queueBox || !detailBox || !actionsBox) {
    throw new Error("pending workbench columns must be visible")
  }
  expect(queueBox.x).toBeLessThan(detailBox.x)
  expect(detailBox.x).toBeLessThan(actionsBox.x)

  const controlResponse = await page.request.get("/api/executions")
  expect(controlResponse.ok()).toBe(true)
  const control = await controlResponse.json()
  expect(control.registry.lane_ids).toEqual(finalFive)
  expect(control.registry.action_ids).toEqual(closedActions)
  expect(control.registry.declarations).toHaveLength(45)
  for (const laneId of finalFive) {
    for (const actionId of closedActions) {
      expect(
        control.registry.declarations.some(
          (item: { action_id: string; lane_id: string }) =>
            item.lane_id === laneId && item.action_id === actionId
        )
      ).toBe(true)
    }
  }

  const packet = queue.getByRole("button", {
    name: /gamenet Decision Packet/,
  })
  await expect(packet).toHaveAttribute("aria-controls", "pending-detail")
  await packet.focus()
  await page.keyboard.press("Enter")
  await expect
    .poll(() =>
      page.evaluate(() =>
        new URL(window.location.href).searchParams.get("selected")
      )
    )
    .toBe("packet:gamenet")
  await expect(detail.getByRole("heading", { name: "gamenet" })).toBeVisible()
  await expect(
    page.getByText("已选择 gamenet Decision Packet", { exact: true })
  ).toBeAttached()
  await expect(detail.getByText("outcomes", { exact: true })).toBeVisible()
  await expect(detail.getByText("uncertainty", { exact: true })).toBeVisible()
  await expect(
    detail.getByText(/聚合 outcomes.*原始数据表未公开/)
  ).toBeVisible()

  const actionRequest = page.waitForRequest("**/api/action-requests")
  const actionResponse = page.waitForResponse("**/api/action-requests")
  await actions.getByRole("button", { name: "生成新方法研究请求" }).click()
  const [request, response] = await Promise.all([actionRequest, actionResponse])
  expect(request.postDataJSON()).toEqual({
    kind: "action_request_input",
    request_id: expect.any(String),
    schema_version: 1,
  })
  const decision = await response.json()
  expect(decision.status).toBe("allowed")

  const executionItem = queue.getByRole("button", {
    name: /gamenet \/ begin_discovery.*remote-execution-not-authorized/,
  })
  await expect(executionItem).toBeVisible({ timeout: 7_000 })
  await executionItem.click()
  await expect
    .poll(() =>
      page.evaluate(() =>
        new URL(window.location.href).searchParams.get("selected")
      )
    )
    .toBe(`execution:${decision.request.request_sha256}`)
  await expect(
    detail.getByText("remote-execution-not-authorized", { exact: true }).first()
  ).toBeVisible()
  await expect(detail.getByText("阻塞", { exact: true }).first()).toBeVisible()

  await page.reload()
  await expect(executionItem).toHaveAttribute("aria-current", "true")
  await expect(
    detail.getByText("remote-execution-not-authorized", { exact: true }).first()
  ).toBeVisible()
  await expect(page.getByText(/^SSE /)).toBeVisible()

  const accessibility = await new AxeBuilder({ page }).analyze()
  expect(accessibility.violations).toEqual([])
})

test("H1 pending detail exposes the registered contract questionnaire", async ({
  page,
  isMobile,
}) => {
  test.skip(isMobile, "desktop contract questionnaire scenario")
  await page.route("**/api/hitl-control", async (route) => {
    const response = await route.fetch()
    const body = await response.json()
    body.h1 = { current: false, enabled: true, owner: null }
    await route.fulfill({ response, json: body })
  })
  await page.goto("/?theme=light&selected=h1")
  await page.getByRole("button", { name: /H1 研究契约/ }).click()

  const detail = page.getByRole("region", { name: "待决详情" })
  await expect(
    detail.getByRole("heading", { name: "结构化研究契约" })
  ).toBeVisible()
  for (const label of [
    "研究问题 · derived",
    "竞争性假设 · derived",
    "数据 lineage · protected",
    "证据职责 · protected",
    "停止条件 · protected",
    "资源上限 · protected",
    "契约内修复预算 · protected",
  ]) {
    await expect(detail.getByText(label, { exact: true })).toBeVisible()
  }
  await expect(detail.getByText("local-ai-bridge-not-configured")).toBeVisible()

  const aiRequest = page.waitForRequest("**/api/contract-ai")
  const aiResponse = page.waitForResponse("**/api/contract-ai")
  await page.getByRole("button", { name: "AI 草拟契约" }).click()
  const [request, response] = await Promise.all([aiRequest, aiResponse])
  expect(request.postDataJSON()).toEqual({
    kind: "contract_ai_input",
    operation: "draft",
    request_id: expect.any(String),
    schema_version: 1,
  })
  expect((await response.json()).h1_written).toBe(false)
  await expect(
    page.getByText("AI bridge 未完成", { exact: true })
  ).toBeVisible()

  const accessibility = await new AxeBuilder({ page }).analyze()
  expect(accessibility.violations).toEqual([])
})

test("action request preserves allowed, blocked, malformed and transport states", async ({
  page,
  isMobile,
}) => {
  test.skip(isMobile, "desktop action scenario")

  let actionRequests = 0
  await page.route("**/api/action-requests", async (route) => {
    actionRequests += 1
    await new Promise((resolve) => setTimeout(resolve, 150))
    await route.continue()
  })
  const requestPromise = page.waitForRequest("**/api/action-requests")
  await page.goto("/?section=overview")
  const actionButton = page.getByRole("button", { name: "生成新方法研究请求" })
  await expect(actionButton).toBeEnabled()
  await expect(actionButton).toHaveAttribute("aria-disabled", "false")
  await actionButton.focus()
  await page.keyboard.press("Enter")
  await page.keyboard.press("Enter")
  const request = await requestPromise
  expect(request.postDataJSON()).toEqual({
    kind: "action_request_input",
    request_id: expect.any(String),
    schema_version: 1,
  })
  await expect(
    page.getByText("请求已生成，尚未执行", { exact: true })
  ).toBeVisible()
  await expect(actionButton).toBeDisabled()
  expect(actionRequests).toBe(1)

  await page.unroute("**/api/action-requests")
  await page.route("**/api/action-requests", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        kind: "action_decision",
        reason_code: "authority_bundle_missing",
        request: null,
        schema_version: 1,
        status: "blocked",
      }),
    })
  )
  await page.reload()
  await page.getByRole("button", { name: "生成新方法研究请求" }).click()
  await expect(
    page.getByText("authority_bundle_missing", { exact: true })
  ).toBeVisible()

  await page.unroute("**/api/action-requests")
  await page.route("**/api/action-requests", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: '{"kind":"wrong"}',
    })
  )
  await page.reload()
  await page.getByRole("button", { name: "生成新方法研究请求" }).click()
  await expect(
    page.getByText("动作决策格式不可用；动作请求保持关闭。", { exact: true })
  ).toBeVisible()

  await page.unroute("**/api/action-requests")
  await page.route("**/api/action-requests", (route) =>
    route.abort("connectionrefused")
  )
  await page.reload()
  await page.getByRole("button", { name: "生成新方法研究请求" }).click()
  await expect(
    page.getByText("动作请求传输失败；结果未知，请重新载入当前状态。", {
      exact: true,
    })
  ).toBeVisible()
})

test("execution control failure exposes a bounded retry", async ({
  page,
  isMobile,
}) => {
  test.skip(isMobile, "desktop recovery scenario")
  let failExecution = true
  await page.route("**/api/executions", (route) => {
    if (failExecution) {
      return route.abort("connectionrefused")
    }
    return route.continue()
  })
  await page.goto("/")
  await expect(
    page.getByText("execution transport failure", { exact: true })
  ).toBeVisible()

  failExecution = false
  await page.getByRole("button", { name: "重试" }).click()
  await expect(
    page.getByText("execution transport failure", { exact: true })
  ).toHaveCount(0)
  await expect(page.getByRole("region", { name: "待决详情" })).toBeVisible()
})

test("transport takeover submits only an opaque fixed operation", async ({
  page,
  isMobile,
}) => {
  test.skip(isMobile, "desktop transport takeover scenario")
  const requestSha = "f".repeat(64)
  const requestId = "action-context-recovery"
  const failedRecord = {
    action_id: "request_reproduction",
    blockers: [],
    contract_sha256: "a".repeat(64),
    declaration_id: "gamenet-request_reproduction",
    events: [
      {
        event_sha256: "b".repeat(64),
        journal_sequence: 701,
        kind: "execution_event",
        occurred_at: "2026-08-18T12:00:00Z",
        outcome: "pending",
        reason_code: "aris-transport-unreachable",
        schema_version: 1,
        sequence: 1,
        state: "review_pending",
      },
    ],
    h1_approval_sha256: "c".repeat(64),
    h2_decision_sha256: null,
    lane_id: "gamenet",
    outcome: "pending",
    request_id: requestId,
    request_sha256: requestSha,
    schema_version: 1,
    state: "review_pending",
  }
  await page.route("**/api/executions", async (route) => {
    const response = await route.fetch()
    const body = await response.json()
    body.queue.records = [failedRecord]
    await route.fulfill({ response, json: body })
  })
  await page.route("**/api/execution-control", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        kind: "transport_control_result",
        operation: "resume",
        record: {
          ...failedRecord,
          events: [
            ...failedRecord.events,
            {
              event_sha256: "d".repeat(64),
              journal_sequence: 702,
              kind: "execution_event",
              occurred_at: "2026-08-18T12:00:01Z",
              outcome: "pending",
              reason_code: "aris-submission-accepted",
              schema_version: 1,
              sequence: 2,
              state: "submitting",
            },
          ],
          state: "submitting",
        },
        schema_version: 1,
      }),
    })
  })

  await page.goto(`/?selected=execution:${requestSha}`)
  const detail = page.getByRole("region", { name: "待决详情" })
  await expect(
    detail.getByText("aris-transport-unreachable", { exact: true }).first()
  ).toBeVisible()
  await expect(
    detail.getByRole("button", { name: "取消固定作业" })
  ).toBeVisible()

  const controlRequest = page.waitForRequest("**/api/execution-control")
  await detail.getByRole("button", { name: "恢复固定传输" }).click()
  expect((await controlRequest).postDataJSON()).toEqual({
    kind: "transport_control_input",
    operation: "resume",
    request_id: requestId,
    schema_version: 1,
  })
  await expect(
    detail.getByText("固定控制动作已记录", { exact: true })
  ).toBeVisible()

  const accessibility = await new AxeBuilder({ page }).analyze()
  expect(accessibility.violations).toEqual([])
})

test("production mobile uses a Sheet and progressive disclosure", async ({
  page,
  isMobile,
}) => {
  test.skip(!isMobile, "mobile scenario")
  await page.goto("/?section=candidates&density=comfortable")
  await expect(
    page.getByRole("heading", { name: "候选基线门禁" })
  ).toBeVisible()
  await expect(page.locator("table")).toBeHidden()
  await page.getByRole("button", { name: "切换导航栏" }).click()
  await expect(page.getByRole("dialog", { name: "Sidebar" })).toBeVisible()
  await page.getByRole("button", { name: "HITL 循环" }).click()
  await expect(
    page.getByRole("heading", { name: "HITL 循环" }).last()
  ).toBeVisible()
  await expect(page).toHaveURL(/section=hitl/)
})

test("pending mobile supports packet review and H2 hold", async ({
  page,
  isMobile,
}) => {
  test.skip(!isMobile, "mobile pending scenario")
  await page.goto("/?theme=light")
  await expect(
    page.getByRole("heading", { name: "待决工作台" }).last()
  ).toBeVisible()

  const queue = page.getByRole("region", { name: "待决队列" })
  const detail = page.getByRole("region", { name: "待决详情" })
  const actions = page.getByRole("complementary", { name: "决策操作" })
  const [queueBox, detailBox, actionsBox] = await Promise.all([
    queue.boundingBox(),
    detail.boundingBox(),
    actions.boundingBox(),
  ])
  if (!queueBox || !detailBox || !actionsBox) {
    throw new Error("pending mobile regions must be visible")
  }
  expect(queueBox.x).toBe(detailBox.x)
  expect(detailBox.x).toBe(actionsBox.x)

  await queue.getByRole("button", { name: /gamenet Decision Packet/ }).click()
  await expect(detail.getByRole("heading", { name: "gamenet" })).toBeVisible()
  const researcher = actions.getByLabel("研究负责人 ID")
  await researcher.fill("production-e2e-mobile")
  const decisions = [
    ["gamenet", "hold"],
    ["safedrug", "go"],
    ["molerec", "revise"],
    ["retain", "kill"],
    ["leap-safedrug", "hold"],
  ] as const
  for (const [lane, decision] of decisions) {
    await researcher.fill("production-e2e-mobile")
    await actions.getByRole("combobox", { name: "lane" }).selectOption(lane)
    await actions.getByRole("combobox", { name: "决策" }).selectOption(decision)
    await actions
      .getByLabel("决策理由（公开安全、单行）")
      .fill(`synthetic packet ${decision}`)
    await expect(actions.getByRole("combobox", { name: "lane" })).toHaveValue(
      lane
    )
    const h2Response = page.waitForResponse("**/api/h2")
    await expect(
      actions.getByRole("button", { name: "创建 H2 决策" })
    ).toBeEnabled()
    await actions.getByRole("button", { name: "创建 H2 决策" }).click()
    const response = await h2Response
    expect(response.status()).toBe(201)
    await expect(response.json()).resolves.toMatchObject({ action: decision })
  }

  await waitForTheme(page, "light")
  const accessibility = await new AxeBuilder({ page }).analyze()
  expect(accessibility.violations).toEqual([])
})

test("stale status closes actions without inventing a disabled reason", async ({
  page,
  isMobile,
}) => {
  test.skip(isMobile, "desktop state scenario")
  await page.route("**/api/harness-state", async (route) => {
    const response = await route.fetch()
    const body = await response.json()
    body.status.condition = "stale"
    body.status.permitted_actions = []
    body.action_context = {
      enabled: false,
      kind: "action_context",
      schema_version: 1,
    }
    await route.fulfill({ response, json: body })
  })
  await page.goto("/?section=overview")
  await expect(page.getByText("项目状态已过期", { exact: true })).toBeVisible()
  const action = page.getByRole("button", { name: "生成新方法研究请求" })
  await expect(action).toBeDisabled()
  await expect(action).toHaveAttribute("aria-disabled", "true")
  await expect(page.getByText(/服务未公开具体原因/)).toHaveCount(0)
})

test("malformed and transport failures fail closed", async ({
  page,
  isMobile,
}) => {
  test.skip(isMobile, "desktop state scenario")
  await page.route("**/api/harness-state", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: '{"kind":"wrong"}',
    })
  )
  await page.goto("/")
  await expect(page.getByText("状态格式不可用", { exact: true })).toBeVisible()
  await expect(page.getByRole("button", { name: /生成/ })).toHaveCount(0)

  await page.unroute("**/api/harness-state")
  await page.route("**/api/harness-state", (route) =>
    route.abort("connectionrefused")
  )
  await page.getByRole("button", { name: "重新载入" }).click()
  await expect(
    page.getByText("无法连接本机 harness", { exact: true })
  ).toBeVisible()
})
