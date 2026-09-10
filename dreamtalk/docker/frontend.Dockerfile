# ── Frontend Dockerfile ───────────────────────────────────────────────
FROM node:20-alpine AS base

# ── Dependencies Stage ────────────────────────────────────────────────
FROM base AS deps
WORKDIR /app
COPY dreamtalk/frontend/package.json dreamtalk/frontend/package-lock.json ./
RUN npm ci --only=production && \
    npm cache clean --force

# ── Build Stage ─────────────────────────────────────────────────────────
FROM base AS builder
WORKDIR /app
COPY dreamtalk/frontend/ .
COPY --from=deps /app/node_modules ./node_modules
RUN npm run build

# ── Production Stage ────────────────────────────────────────────────────
FROM base AS runner
WORKDIR /app

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1

RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs
EXPOSE 3000

ENV PORT=3000 \
    HOSTNAME="0.0.0.0"

CMD ["node", "server.js"]
