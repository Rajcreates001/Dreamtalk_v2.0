import { test, expect } from "@playwright/test"
import { gotoAuthenticated } from "./helpers"

test.describe("Digital Humans Page", () => {
  test("page loads with title", async ({ page }) => {
    await gotoAuthenticated(page, "/digital-humans")
    await expect(page.locator("h1")).toContainText("Digital Humans")
  })

  test("Create New button links to studio", async ({ page }) => {
    await gotoAuthenticated(page, "/digital-humans")
    const createBtn = page.locator('a:has-text("Create New")')
    await expect(createBtn).toBeVisible()
    await expect(createBtn).toHaveAttribute("href", "/studio")
  })

  test("avatar cards display stat labels", async ({ page }) => {
    await gotoAuthenticated(page, "/digital-humans")
    await expect(page.locator("text=/Memory/").first()).toBeVisible({ timeout: 5000 })
    await expect(page.locator("text=/Relationship/").first()).toBeVisible({ timeout: 3000 })
    await expect(page.locator("text=/Languages/").first()).toBeVisible({ timeout: 3000 })
  })

  test("create new avatar placeholder card is present", async ({ page }) => {
    await gotoAuthenticated(page, "/digital-humans")
    await expect(page.locator("text=Create New Avatar").first()).toBeVisible()
  })

  test("total avatar count is shown in subtitle", async ({ page }) => {
    await gotoAuthenticated(page, "/digital-humans")
    await expect(page.locator("p:has-text('Manage your AI workforce')").first()).toBeVisible()
  })
})
