import { test, expect } from "@playwright/test"

test.describe("Authentication Flows", () => {
  test("landing page loads and shows hero section", async ({ page }) => {
    await page.goto("/")
    await expect(page.locator("h1")).toBeVisible()
    await expect(page.locator("text=AI Companion").first()).toBeVisible()
  })

  test("login page renders correctly", async ({ page }) => {
    await page.goto("/login")
    await expect(page.locator("h1, h2").first()).toBeVisible()

    // Should have email and password fields
    const emailInput = page.locator('input[type="email"], input[name="email"]').first()
    const passwordInput = page.locator('input[type="password"], input[name="password"]').first()
    await expect(emailInput).toBeVisible()
    await expect(passwordInput).toBeVisible()
  })

  test("signup page renders correctly", async ({ page }) => {
    await page.goto("/signup")
    await expect(page.locator("h1, h2").first()).toBeVisible()

    // Should have form fields (name, email, password)
    const inputs = page.locator('input[type="text"], input[type="email"], input[type="password"]')
    const count = await inputs.count()
    expect(count).toBeGreaterThanOrEqual(2)
  })

  test("login page has link to signup", async ({ page }) => {
    await page.goto("/login")
    const signupLink = page.locator('a[href*="signup"]')
    await expect(signupLink).toBeVisible()
  })

  test("signup page has link to login", async ({ page }) => {
    await page.goto("/signup")
    const loginLink = page.locator('a[href*="login"]')
    await expect(loginLink).toBeVisible()
  })

  test("social login buttons are present", async ({ page }) => {
    await page.goto("/login")
    // Check for Google / GitHub buttons
    const socialButtons = page.locator('button:has-text("Google"), button:has-text("GitHub"), a:has-text("Google"), a:has-text("GitHub")')
    const count = await socialButtons.count()
    expect(count).toBeGreaterThanOrEqual(1)
  })
})
