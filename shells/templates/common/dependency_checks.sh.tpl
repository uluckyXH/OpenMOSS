command -v bash >/dev/null 2>&1 || die "bash not found in PATH"
command -v curl >/dev/null 2>&1 || die "curl not found in PATH"
command -v python3 >/dev/null 2>&1 || die "python3 not found in PATH"

if [[ "${REQUIRE_OPENCLAW:-0}" == "1" ]]; then
  command -v openclaw >/dev/null 2>&1 || die "openclaw CLI not found in PATH"
fi
