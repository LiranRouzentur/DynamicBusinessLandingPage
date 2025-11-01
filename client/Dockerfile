# --- build stage ---
  FROM node:20-alpine AS build
  WORKDIR /app
  COPY package*.json ./
  RUN npm ci
  COPY . .
  
  # Inject API base URL at build time (Vite)
  ARG API_BASE_URL
  ENV API_BASE_URL=$API_BASE_URL
  
  RUN npm run build
  
  # --- serve stage ---
  FROM nginx:1.27-alpine
  # Simple SPA config; rewrite to index.html
  RUN apk add --no-cache curl
  COPY <<'NGINX' /etc/nginx/conf.d/default.conf
  server {
    listen 80;
    server_name _;
    root /usr/share/nginx/html;
    index index.html;
    location / {
      try_files $uri /index.html;
    }
  }
  NGINX
  
  COPY --from=build /app/dist /usr/share/nginx/html
  
  EXPOSE 80
  HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD curl -fsS http://localhost/ || exit 1