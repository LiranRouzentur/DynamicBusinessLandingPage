# --- deps cache
FROM node:20-alpine AS deps
WORKDIR /app
COPY package*.json ./
RUN npm ci

# --- build (prod)
FROM deps AS build
# Vite convention: env must start with VITE_
ARG API_BASE_URL=/
ENV API_BASE_URL=$API_BASE_URL
COPY . .
RUN npm run build

# --- dev (hot reload)
FROM deps AS dev
ENV NODE_ENV=development
COPY . .
EXPOSE 5173
CMD ["npm","run","dev","--","--host","0.0.0.0"]

# --- prod (nginx)
FROM nginx:1.25-alpine AS prod
# SPA nginx
RUN printf 'server { \
  listen 80; server_name _; \
  root /usr/share/nginx/html; index index.html; \
  location / { try_files $uri /index.html; } \
  location /health { return 200 "ok\n"; } \
}\n' > /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
HEALTHCHECK --interval=30s --timeout=10s --retries=3 CMD wget -qO- http://localhost/health || exit 1
