section "Register runtime on OpenMOSS"

if [[ -z "${API_KEY:-}" ]]; then
  [[ -n "${BOOTSTRAP_REGISTER_TOKEN:-}" ]] || die "BOOTSTRAP_REGISTER_TOKEN is required"

  REG_RESPONSE="$(curl -fsS -X POST "${OPENMOSS_URL}${BOOTSTRAP_REGISTER_PATH}" \
    -H "X-Bootstrap-Token: ${BOOTSTRAP_REGISTER_TOKEN}")"

  API_KEY="$(echo "${REG_RESPONSE}" | grep -oP '"api_key"\s*:\s*"\K[^"]+' || true)"
  if [[ -z "${API_KEY}" ]]; then
    API_KEY="$(echo "${REG_RESPONSE}" | grep -oP '"apiKey"\s*:\s*"\K[^"]+' || true)"
  fi
  if [[ -z "${API_KEY}" ]]; then
    API_KEY="$(echo "${REG_RESPONSE}" | grep -oP '"key"\s*:\s*"\K[^"]+' || true)"
  fi

  [[ -n "${API_KEY}" ]] || die "Unable to extract API key from register response"
  log "registered runtime agent on OpenMOSS"
else
  log "using existing API key"
fi

export API_KEY
