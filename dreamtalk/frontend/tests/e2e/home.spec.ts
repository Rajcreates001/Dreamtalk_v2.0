import { test, expect } from "@playwright/test"
import { gotoAuthenticated } from "./helpers"

test.describe("Home Page", () => {
  test("home page loads with greeting", async ({ page }) => {
    await gotoAuthenticated(page, "/home")
    await expect(page.locator("h1")).toBeVisible()
    const h1 = page.locator("h1")
    await expect(h1).toContainText(/Good (Morning|Afternoon|Evening)/)
  })

  test("status badges are visible", async ({ page }) => {
    await gotoAuthenticated(page, "/home")
    const badges = page.locator("text=/Active|Today|Availability/")
    await expect(badges.first()).toBeVisible({ timeout: 5000 })
  })

  test("quick actions section has 6 action cards", async ({ page }) => {
    await gotoAuthenticated(page, "/home")
    await expect(page.locator("text=Quick Actions")).toBeVisible()
    const actions = [
      "Create Digital Human", "Start Conversation", "Upload Knowledge",
      "Clone Voice", "Import Documents", "Analytics",
    ]
    for (const action of actions) {
      await expect(page.locator(`text=${action}`).first()).toBeVisible()
    }
  })

  test("'Start talking instantly' CTA navigates to conversations", async ({ page }) => {
    await gotoAuthenticated(page, "/home")
    const cta = page.locator('a:has-text("Start talking instantly")')
    await expect(cta).toBeVisible()
    await expect(cta).toHaveAttribute("href", "/conversations")
  })

  test("Create Digital Human card links to studio", async ({ page }) => {
    await gotoAuthenticated(page, "/home")
    const createCard = page.locator('a:has-text("Create Digital Human")')
    await expect(createCard).toHaveAttribute("href", "/studio")
  })

  test("current avatar section is present", async ({ page }) => {
    await gotoAuthenticated(page, "/home")
    await expect(page.locator("text=Current Avatar")).toBeVisible({ timeout: 5000 })
  })

  test("AI insights section is present", async ({ page }) => {
    await gotoAuthenticated(page, "/home")
    await expect(page.locator("text=AI Insights")).toBeVisible({ timeout: 5000 })
  })
})
