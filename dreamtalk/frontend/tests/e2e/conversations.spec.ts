import { test, expect } from "@playwright/test"
import { gotoAuthenticated } from "./helpers"

test.describe("Conversations Page", () => {
  test("conversations page loads with 3-panel layout", async ({ page }) => {
    await gotoAuthenticated(page, "/conversations")
    await expect(page.locator('input[placeholder*="Search"]').first()).toBeVisible({ timeout: 5000 })
  })

  test("chat input area is present", async ({ page }) => {
    await gotoAuthenticated(page, "/conversations")
    const chatInput = page.locator(
      'input[placeholder*="message"], textarea[placeholder*="message"], ' +
      'input[placeholder*="Ask"], textarea[placeholder*="Ask"]'
    ).first()
    await expect(chatInput).toBeVisible({ timeout: 5000 })
  })

  test("send button is present", async ({ page }) => {
    await gotoAuthenticated(page, "/conversations")
    await expect(page.locator('button:has-text("Send")').first()).toBeVisible({ timeout: 5000 })
  })

  test("new conversation button is present", async ({ page }) => {
    await gotoAuthenticated(page, "/conversations")
    await expect(page.locator('button:has-text("New Conversation")').first()).toBeVisible()
  })

  test("conversation history list area is present", async ({ page }) => {
    await gotoAuthenticated(page, "/conversations")
    await expect(page.locator('input[placeholder*="Search"]').first()).toBeVisible()
    await expect(page.locator('button:has-text("New Conversation")').first()).toBeVisible()
  })

  test("right thinking panel shows Avatar Thoughts section", async ({ page }) => {
    await gotoAuthenticated(page, "/conversations")
    await expect(page.locator("text=Avatar Thoughts").first()).toBeVisible({ timeout: 5000 })
    await expect(page.locator("text=Emotion").first()).toBeVisible()
    await expect(page.locator("text=Reasoning").first()).toBeVisible()
    await expect(page.locator("text=Sources").first()).toBeVisible()
  })
})
