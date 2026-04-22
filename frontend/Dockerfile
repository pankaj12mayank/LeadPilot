# Static SPA + nginx (set VITE_API_URL at build time for browser-reachable API).
FROM node:22-alpine AS build
WORKDIR /app

COPY package.json package-lock.json ./
# Prefer reproducible installs once lockfile includes new dev deps (vitest, etc.).
RUN npm ci || npm install

COPY . .

ARG VITE_API_BASE_URL=http://127.0.0.1:8000/api
ARG VITE_API_URL=
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
ENV VITE_API_URL=$VITE_API_URL

RUN npm run build

FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
