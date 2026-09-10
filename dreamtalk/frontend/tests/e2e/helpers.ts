import { Page } from "@playwright/test"

/**
 * Set up mock authentication in the browser's localStorage.
 * This prevents the (app)/layout.tsx auth check from redirecting to /login.
 */
export async function setupMockAuth(page: Page) {
  await page.addInitScript(() => {
    const mockToken =
      "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9." +
      "eyJzdWIiOiJ0ZXN0LXVzZXItaWQiLCJlbWFpbCI6InRlc3RAZXhhbXBsZS5jb20iLCJyb2xlIjoidXNlciJ9." +
      "mock-signature"

    localStorage.setItem("access_token", mockToken)
    localStorage.setItem(
      "user",
      JSON.stringify({
        id: "test-user-id",
        email: "test@example.com",
        full_name: "Test User",
        role: "user",
      })
    )
  })
}

/**
 * Navigate to an authenticated (app) route with mock auth already set up.
 * Also intercepts the auth/me API call to prevent redirects when backend is offline.
 */
export async function gotoAuthenticated(page: Page, url: string) {
  await setupMockAuth(page)

  // Intercept auth/me to prevent redirect when backend isn't running
  await page.route("**/api/v1/auth/me", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        id: "test-user-id",
        email: "test@example.com",
        full_name: "Test User",
        role: "user",
      }),
    })
  })

  await page.goto(url)
}
