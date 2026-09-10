# ── Dreamtalk Frontend Dev Container (Podman) ─────────────────────────
# Runs Next.js in dev mode with hot module replacement.
# Backend runs separately on the host (python run_server.py).
# ──────────────────────────────────────────────────────────────────────

FROM node:22-alpine

WORKDIR /app

# Copy package files first for layer caching
COPY package.json package-lock.json* ./

# Install all dependencies (including devDependencies)
RUN npm install

# Copy the rest of the source code
COPY . .

# Expose Next.js dev server port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD wget --spider http://localhost:3000/ || exit 1

# Run in dev mode with hot reload
ENV NODE_ENV=development
ENV NEXT_TELEMETRY_DISABLED=1

CMD ["npm", "run", "dev"]
