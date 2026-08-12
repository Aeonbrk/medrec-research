import AxeBuilder from "@axe-core/playwright"
import { expect, test } from "@playwright/test"

test("production desktop renders API data, URL state, themes and passes axe", async ({
  page,
  isMobile,
}) => {
  test.skip(isMobile, "desktop scenario")
  await page.goto("/?theme=light")
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

  await page.getByRole("radio", { name: "深色" }).click()
  await expect(page.locator("html")).toHaveClass(/dark/)
  await expect(page).toHaveURL(/theme=dark/)
  await page.reload()
  await expect(page.locator("html")).toHaveClass(/dark/)
  await expect(page.getByRole("textbox", { name: "全局搜索" })).toHaveValue(
    "molerec"
  )

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
  await page.goto("/")
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
  await page.goto("/")
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
