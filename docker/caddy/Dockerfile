# Caddy with the rate-limit module (github.com/mholt/caddy-ratelimit), pinned by digest/commit.
FROM caddy:2.11-builder-alpine@sha256:d6161a2c82fd58b3205048958fb6246d0c5d892beee8a47e90944610c4efd100 AS builder
# Module downloads (proxy.golang.org) fail now and then – retry instead of failing CI or a deploy
RUN for attempt in 1 2 3; do \
        xcaddy build --with github.com/mholt/caddy-ratelimit@5625512f24f6f59d6f64fb3aafe5eecff0b286db \
            && exit 0; \
        echo "xcaddy build failed (attempt $attempt of 3)" >&2; \
        if [ "$attempt" -lt 3 ]; then sleep 20; fi; \
    done; exit 1

FROM caddy:2.11-alpine@sha256:d8542f48d34a9cf4e4c11a478865229840e87e4c96ea3f439101f31a5d35f75f
COPY --from=builder /usr/bin/caddy /usr/bin/caddy
