FROM node:22.13.0-alpine3.21 AS builder
WORKDIR /app
COPY package*.json ./

RUN npm ci 

COPY . .

ARG VITE_API_BASE_URL VITE_API_SUFFIX VITE_API_BE_BASE_URL

RUN npm run build

FROM node:22.13.0-alpine3.21
WORKDIR /app

COPY --from=builder /app/package*.json ./

RUN npm ci --only=production && npm cache clean --force

COPY --from=builder /app/build build/

EXPOSE 3000
ENV NODE_ENV=production

CMD [ "node", "build" ]