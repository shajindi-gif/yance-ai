# Next.js Production Dockerfile
FROM node:22-alpine AS builder
WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci

COPY . .
RUN npm run build

# Runtime
FROM node:22-alpine
WORKDIR /app

RUN addgroup -g 1001 -S yance && adduser -S yance -u 1001

COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

USER yance
EXPOSE 3000

CMD ["node", "server.js"]
