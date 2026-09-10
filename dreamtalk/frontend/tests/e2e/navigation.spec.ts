import { test, expect } from "@playwright/test"
import { gotoAuthenticated } from "./helpers"

test.describe("Sidebar Navigation", () => {
  test("sidebar is visible on (app) pages", async ({ page }) => {
    await gotoAuthenticated(page, "/home")
    await expect(page.locator("text=Home").first()).toBeVisible({ timeout: 5000 })
  })

  test("main navigation items are present", async ({ page }) => {
    await gotoAuthenticated(page, "/home")
    const navItems = ["Home", "Digital Humans", "Studio", "Conversations", "Knowledge", "Analytics", "Settings"]
    for (const item of navItems) {
      await expect(page.locator(`a:has-text("${item}")`).first()).toBeVisible({ timeout: 3000 })
    }
  })

  test("Home link navigates to /home", async ({ page }) => {
    await gotoAuthenticated(page, "/digital-humans")
    const homeLink = page.locator('a[href="/home"]').first()
    await expect(homeLink).toBeVisible({ timeout: 5000 })
    await homeLink.click()
    await expect(page).toHaveURL(/\/home/)
  })

  test("Studio link navigates to /studio", async ({ page }) => {
    await gotoAuthenticated(page, "/home")
    const studioLink = page.locator('a[href="/studio"]').first()
    await expect(studioLink).toBeVisible({ timeout: 5000 })
    await studioLink.click()
    await expect(page).toHaveURL(/\/studio/)
  })

  test("Conversations link navigates to /conversations", async ({ page }) => {
    await gotoAuthenticated(page, "/home")
    const convLink = page.locator('a[href="/conversations"]').first()
    await expect(convLink).toBeVisible({ timeout: 5000 })
    await convLink.click()
    await expect(page).toHaveURL(/\/conversations/)
  })

  test("Knowledge link navigates to /knowledge", async ({ page }) => {
    await gotoAuthenticated(page, "/home")
    const knowledgeLink = page.locator('a[href="/knowledge"]').first()
    await expect(knowledgeLink).toBeVisible({ timeout: 5000 })
    await knowledgeLink.click()
    await expect(page).toHaveURL(/\/knowledge/)
  })

  test("Analytics link navigates to /analytics", async ({ page }) => {
    await gotoAuthenticated(page, "/home")
    const analyticsLink = page.locator('a[href="/analytics"]').first()
    await expect(analyticsLink).toBeVisible({ timeout: 5000 })
    await analyticsLink.click()
    await expect(page).toHaveURL(/\/analytics/)
  })

  test("Settings link navigates to /settings", async ({ page }) => {
    await gotoAuthenticated(page, "/home")
    const settingsLink = page.locator('a[href="/settings"]').first()
    await expect(settingsLink).toBeVisible({ timeout: 5000 })
    await settingsLink.click()
    await expect(page).toHaveURL(/\/settings/)
  })
})
