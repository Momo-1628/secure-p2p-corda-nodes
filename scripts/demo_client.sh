#!/usr/bin/env bash
# Runs the RPC DemoClient directly: scripts/demo_client.sh [all|networkmap|send|ack|privacy|untrusted|ping|bench]
cd "$(dirname "$0")/.."
exec java --add-opens java.base/java.time=ALL-UNNAMED --add-opens java.base/java.io=ALL-UNNAMED \
  --add-opens java.base/java.util=ALL-UNNAMED --add-opens java.base/java.lang=ALL-UNNAMED \
  --add-opens java.base/java.net=ALL-UNNAMED --add-opens java.base/java.nio=ALL-UNNAMED \
  -cp "$(cat clients/build/classpath.txt)" com.securep2p.clients.DemoClient "${1:-all}"
