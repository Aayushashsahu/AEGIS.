FROM node:22-slim

RUN apt-get update \
  && apt-get install -y --no-install-recommends python3 \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .
RUN npm install -g corepack@latest \
  && cd webapp \
  && corepack pnpm install --frozen-lockfile \
  && corepack pnpm run build

WORKDIR /app/webapp
ENV NODE_ENV=production
ENV AEGIS_ROOT=/app
CMD ["node", "dist/index.js"]
