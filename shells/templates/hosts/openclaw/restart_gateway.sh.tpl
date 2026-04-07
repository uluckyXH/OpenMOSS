if [[ "${RESTART_GATEWAY:-0}" == "1" ]]; then
  REQUIRE_OPENCLAW=1

  section "Restart OpenClaw gateway"
  (openclaw gateway restart || true) >/tmp/openclaw-gateway-restart.log 2>&1
  sleep 5
  openclaw gateway status || true
fi
