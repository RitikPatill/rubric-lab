FROM node:22-alpine

# Install pnpm
RUN corepack enable && corepack prepare pnpm@9.15.0 --activate

WORKDIR /app

# Copy workspace config first (for pnpm workspace resolution)
COPY package.json pnpm-workspace.yaml ./
COPY packages/shared ./packages/shared
COPY apps/web ./apps/web

# Install deps for web and its workspace dependencies
RUN pnpm install --filter @rubriclab/web...

WORKDIR /app/apps/web

ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

RUN pnpm build

EXPOSE 3000

# Note: single-stage build — optimize to multi-stage in a later milestone
CMD ["pnpm", "start"]
