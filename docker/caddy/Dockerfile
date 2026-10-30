# Caddy with the rate-limit module (github.com/mholt/caddy-ratelimit), pinned by digest/commit.
FROM caddy:2.11-builder-alpine@sha256:95a5e7e2692b5eb9545aadc5b90a39f6f509bee59c9508a493f83ee902eaef63 AS builder
# Module downloads (proxy.golang.org) fail now and then – retry instead of failing CI or a deploy
RUN for attempt in 1 2 3; do \
        xcaddy build --with github.com/mholt/caddy-ratelimit@5625512f24f6f59d6f64fb3aafe5eecff0b286db \
            && exit 0; \
        echo "xcaddy build failed (attempt $attempt of 3)" >&2; \
        if [ "$attempt" -lt 3 ]; then sleep 20; fi; \
    done; exit 1

FROM caddy:2.11-alpine@sha256:e70b164da81ef698b3ad19af799ea6086ce6d9e48ed4079eb9fe26f6fbf14ee5
COPY --from=builder /usr/bin/caddy /usr/bin/caddy
