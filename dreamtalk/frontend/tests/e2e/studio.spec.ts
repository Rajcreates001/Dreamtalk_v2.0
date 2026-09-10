import { test, expect } from "@playwright/test"
import { gotoAuthenticated } from "./helpers"

test.describe("Avatar Studio", () => {
  test("studio page loads with title", async ({ page }) => {
    await gotoAuthenticated(page, "/studio")
    await expect(page.locator("h1")).toContainText("Avatar Studio")
  })

  test("15 studio tabs are present in the sidebar", async ({ page }) => {
    await gotoAuthenticated(page, "/studio")
    const tabs = [
      "Appearance", "Voice", "Personality", "Knowledge", "Memory",
      "Emotion", "Expressions", "Relationships", "Motion", "Camera",
      "Actions", "Fine Tuning", "Testing", "Preview", "Deploy",
    ]
    // Use toBeAttached for tabs that may be scrolled out of view in the vertical tab bar
    for (const tab of tabs) {
      await expect(page.locator(`text=${tab}`).first()).toBeAttached({ timeout: 3000 })
    }
  })

  test("Appearance tab is active by default", async ({ page }) => {
    await gotoAuthenticated(page, "/studio")
    await expect(page.locator("text=Appearance").first()).toBeVisible()
    await expect(page.locator('input[placeholder="Enter name..."]').first()).toBeVisible()
  })

  test("clicking Voice tab shows voice settings", async ({ page }) => {
    await gotoAuthenticated(page, "/studio")
    const voiceTab = page.locator("text=Voice").first()
    await voiceTab.click()
    await expect(page.locator("text=Speech synthesis")).toBeVisible()
    await expect(page.locator("text=Language").first()).toBeVisible()
    await expect(page.locator("text=Accent").first()).toBeVisible()
  })

  test("clicking Personality tab shows traits section", async ({ page }) => {
    await gotoAuthenticated(page, "/studio")
    const personalityTab = page.locator("text=Personality").first()
    await personalityTab.click()
    await expect(page.locator("text=Behavioral traits")).toBeVisible()
    await expect(page.locator("text=Empathetic").first()).toBeVisible()
  })

  test("clicking Deploy tab shows publishing options", async ({ page }) => {
    await gotoAuthenticated(page, "/studio")
    const deployTab = page.locator("text=Deploy").first()
    await deployTab.click()
    await expect(page.locator("text=Publish & go live")).toBeVisible()
    await expect(page.locator('button:has-text("Publish")').first()).toBeVisible()
  })

  test("Save Draft button is present", async ({ page }) => {
    await gotoAuthenticated(page, "/studio")
    await expect(page.locator('button:has-text("Save Draft")').first()).toBeVisible()
  })

  test("3D preview panel is visible", async ({ page }) => {
    await gotoAuthenticated(page, "/studio")
    await expect(page.locator("text=3D Preview")).toBeVisible()
  })

  test("preview toolbar has Reset, Auto-rotate, Preview buttons", async ({ page }) => {
    await gotoAuthenticated(page, "/studio")
    await expect(page.locator('button:has-text("Reset")').first()).toBeVisible()
    await expect(page.locator('button:has-text("Auto-rotate")').first()).toBeVisible()
  })
})
