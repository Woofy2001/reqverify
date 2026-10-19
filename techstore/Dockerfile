# ==============================================================================
# TechStore SUT Dockerfile — Hardened Multi-Stage Containerization
# Aligned with CIS Docker Benchmark: Pinned Node 22 Alpine, Non-Root Execution
# ==============================================================================

# Stage 1: Dependencies
FROM node:22.14-alpine AS deps
WORKDIR /app
COPY package*.json ./
RUN npm ci

# Stage 2: Builder
FROM node:22.14-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Immutable Mutant Tag Support
ARG MUTANT=""
ENV MUTANT=${MUTANT}
ENV NEXT_PUBLIC_MUTANT=${MUTANT}
ENV NEXT_TELEMETRY_DISABLED=1

# Seed deterministic benchmark SQLite database and compile Next.js production build
RUN node scripts/seed.mjs
RUN npm run build

# Stage 3: Runner (Production Runtime)
FROM node:22.14-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV PORT=3000
ENV HOSTNAME="0.0.0.0"
ENV NEXT_TELEMETRY_DISABLED=1

ARG MUTANT=""
ENV MUTANT=${MUTANT}
ENV NEXT_PUBLIC_MUTANT=${MUTANT}

# Create app directory with non-root ownership (node:node, UID/GID 1000)
RUN chown -R node:node /app

# Copy built application and required production assets
COPY --from=builder --chown=node:node /app/package*.json ./
COPY --from=builder --chown=node:node /app/node_modules ./node_modules
COPY --from=builder --chown=node:node /app/.next ./.next
COPY --from=builder --chown=node:node /app/public ./public
COPY --from=builder --chown=node:node /app/data ./data
COPY --from=builder --chown=node:node /app/next.config.mjs ./

# Drop root privilege and enforce non-root user 'node'
USER node

EXPOSE 3000

CMD ["npm", "run", "start"]
