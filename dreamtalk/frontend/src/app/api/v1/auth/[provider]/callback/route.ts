import { NextRequest, NextResponse } from "next/server"

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:5001"

const PROVIDER_CONFIG: Record<
  string,
  {
    tokenUrl: string
    clientIdEnv: string
    clientSecretEnv: string
    redirectUriEnv: string
    backendEndpoint: string
    headers?: Record<string, string>
  }
> = {
  google: {
    tokenUrl: "https://oauth2.googleapis.com/token",
    clientIdEnv: "GOOGLE_CLIENT_ID",
    clientSecretEnv: "GOOGLE_CLIENT_SECRET",
    redirectUriEnv: "GOOGLE_REDIRECT_URI",
    backendEndpoint: "/api/v1/auth/google",
  },
  github: {
    tokenUrl: "https://github.com/login/oauth/access_token",
    clientIdEnv: "GITHUB_CLIENT_ID",
    clientSecretEnv: "GITHUB_CLIENT_SECRET",
    redirectUriEnv: "GITHUB_REDIRECT_URI",
    backendEndpoint: "/api/v1/auth/github",
    headers: { Accept: "application/json" },
  },
  microsoft: {
    tokenUrl: "https://login.microsoftonline.com/common/oauth2/v2.0/token",
    clientIdEnv: "MICROSOFT_CLIENT_ID",
    clientSecretEnv: "MICROSOFT_CLIENT_SECRET",
    redirectUriEnv: "MICROSOFT_REDIRECT_URI",
    backendEndpoint: "/api/v1/auth/microsoft",
  },
}

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ provider: string }> },
) {
  const { provider } = await params
  const config = PROVIDER_CONFIG[provider]

  if (!config) {
    return NextResponse.redirect(new URL("/login?error=invalid_provider", request.url))
  }

  const { searchParams } = new URL(request.url)
  const code = searchParams.get("code")

  if (!code) {
    return NextResponse.redirect(new URL("/login?error=missing_code", request.url))
  }

  const clientId = process.env[config.clientIdEnv]
  const clientSecret = process.env[config.clientSecretEnv]
  const redirectUri = process.env[config.redirectUriEnv]

  if (!clientId || !clientSecret || !redirectUri) {
    return NextResponse.redirect(new URL(`/login?error=${provider}_not_configured`, request.url))
  }

  try {
    const tokenParams = new URLSearchParams({
      client_id: clientId,
      client_secret: clientSecret,
      code,
      redirect_uri: redirectUri,
      grant_type: "authorization_code",
    })

    const tokenRes = await fetch(config.tokenUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
        ...config.headers,
      },
      body: tokenParams,
    })

    if (!tokenRes.ok) {
      return NextResponse.redirect(new URL(`/login?error=${provider}_token_exchange_failed`, request.url))
    }

    const tokenData = await tokenRes.json()
    const accessToken = tokenData.access_token

    if (!accessToken) {
      return NextResponse.redirect(new URL(`/login?error=${provider}_missing_access_token`, request.url))
    }

    const backendRes = await fetch(`${API_BASE_URL}${config.backendEndpoint}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ access_token: accessToken }),
    })

    if (!backendRes.ok) {
      return NextResponse.redirect(new URL(`/login?error=${provider}_auth_failed`, request.url))
    }

    const data = await backendRes.json()
    const { access_token, refresh_token } = data.tokens

    const response = NextResponse.redirect(new URL(`/login?oauth_token=${access_token}&oauth_refresh=${refresh_token}`, request.url))
    response.cookies.set("access_token", access_token, {
      httpOnly: false,
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax",
      maxAge: 60 * 60 * 24,
      path: "/",
    })
    response.cookies.set("refresh_token", refresh_token, {
      httpOnly: false,
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax",
      maxAge: 60 * 60 * 24 * 30,
      path: "/",
    })

    return response
  } catch {
    return NextResponse.redirect(new URL(`/login?error=${provider}_error`, request.url))
  }
}
