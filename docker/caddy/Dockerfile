# Caddy with the rate-limit module (github.com/mholt/caddy-ratelimit), pinned by digest/commit.
FROM caddy:2.10-builder-alpine@sha256:4cff3ae272ea05842adb4546e35961e4947aeea65f80fa1eb62a35b960e84971 AS builder
# Module downloads (proxy.golang.org) fail now and then – retry instead of failing CI or a deploy
RUN for attempt in 1 2 3; do \
        xcaddy build --with github.com/mholt/caddy-ratelimit@5625512f24f6f59d6f64fb3aafe5eecff0b286db \
            && exit 0; \
        echo "xcaddy build failed (attempt $attempt of 3)" >&2; \
        if [ "$attempt" -lt 3 ]; then sleep 20; fi; \
    done; exit 1

FROM caddy:2.10-alpine@sha256:4c6e91c6ed0e2fa03efd5b44747b625fec79bc9cd06ac5235a779726618e530d
COPY --from=builder /usr/bin/caddy /usr/bin/caddy
