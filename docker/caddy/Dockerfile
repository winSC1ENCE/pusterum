# Caddy with the rate-limit module (github.com/mholt/caddy-ratelimit), pinned by digest/commit.
FROM caddy:2.11-builder-alpine@sha256:ef9b65adf9a224770c6d5f6d1ae1bf99bc3caaa78d8c4bae3ea949ee6984f301 AS builder
# Module downloads (proxy.golang.org) fail now and then – retry instead of failing CI or a deploy
RUN for attempt in 1 2 3; do \
        xcaddy build --with github.com/mholt/caddy-ratelimit@5625512f24f6f59d6f64fb3aafe5eecff0b286db \
            && exit 0; \
        echo "xcaddy build failed (attempt $attempt of 3)" >&2; \
        if [ "$attempt" -lt 3 ]; then sleep 20; fi; \
    done; exit 1

FROM caddy:2.11-alpine@sha256:eb4d35b7452d1ab6171fbdbe8d9275b2301dad6dad92115d91e19fb9b24d510f
COPY --from=builder /usr/bin/caddy /usr/bin/caddy
