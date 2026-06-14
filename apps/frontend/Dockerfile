# =====================================================================
# 멀티스테이지 빌드: node(빌드) → nginx(서빙)
#   - builder: 정적 SPA 빌드 (npm run build = tsc && vite build)
#   - prod:    nginx 로 dist 서빙 (node/툴체인 미포함 → ~50MB, ~30Mi RAM)
# 기존 Vite dev 서버(npm run dev) 대비 메모리/이미지/보안 모두 개선.
# 베이스 이미지는 모두 사설 Harbor(192.168.0.237) 에서 가져온다.
# =====================================================================

# ---- builder ----
FROM 192.168.0.237/booking_ticket/node:22-alpine AS builder
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm install
COPY . .
# VITE_* 는 빌드 타임에 번들에 박힌다(런타임 env 로는 못 바꿈).
# 클러스터 기본값 유지를 위해 기본 true. 변경 시 --build-arg 또는 재빌드 필요.
ARG VITE_GOOGLE_OAUTH_ENABLED=true
ENV VITE_GOOGLE_OAUTH_ENABLED=$VITE_GOOGLE_OAUTH_ENABLED
RUN npm run build

# ---- prod (runtime) ----
FROM 192.168.0.237/booking_ticket/nginx:alpine AS prod
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 5173
# nginx:alpine 기본 CMD(nginx -g 'daemon off;') 사용
