# Use a Node.js Alpine image for the builder stage
FROM node:22-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .

# Build-time only
ARG VITE_API_BASE_URL
ARG VITE_API_SUFFIX
ARG VITE_API_BE_BASE_URL

# Runtime and build-time, to persist args passed at build time
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
ENV VITE_API_SUFFIX=$VITE_API_SUFFIX
ENV VITE_API_BE_BASE_URL=$VITE_API_BE_BASE_URL

RUN npm run build
RUN npm prune --production

# Use another Node.js Alpine image for the final stage
FROM node:22-alpine
WORKDIR /app
COPY --from=builder /app/build build/
COPY --from=builder /app/node_modules node_modules/
COPY package.json .
EXPOSE 3000
ENV NODE_ENV=production
CMD [ "node", "build" ]

