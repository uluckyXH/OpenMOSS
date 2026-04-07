if [[ "${INCLUDE_SCHEDULE:-0}" == "1" ]]; then
  REQUIRE_OPENCLAW=1

  section "Create or update OpenClaw schedule"

  [[ -n "${SCHEDULE_EXPR:-}" ]] || die "SCHEDULE_EXPR is required"
  [[ -n "${SCHEDULE_MESSAGE:-}" ]] || die "SCHEDULE_MESSAGE is required"

  JOB_NAME="${SCHEDULE_JOB_NAME:-${AGENT_ID} scheduled task (${SCHEDULE_EXPR})}"
  SCHEDULE_MODE="${SCHEDULE_MODE:-interval}"

  if [[ "${SCHEDULE_MODE}" == "cron" ]]; then
    schedule_flag="--cron"
  else
    schedule_flag="--every"
  fi

  if openclaw cron list 2>/dev/null | grep -qF "${JOB_NAME}"; then
    log "cron job already exists: ${JOB_NAME}"
  else
    cmd=(openclaw cron add
      --name "${JOB_NAME}"
      "${schedule_flag}" "${SCHEDULE_EXPR}"
      --session "${SCHEDULE_SESSION_MODE:-isolated}"
      --agent "${AGENT_ID}"
      --message "${SCHEDULE_MESSAGE}"
      --timeout-seconds "${SCHEDULE_TIMEOUT_SECONDS:-1800}")

    if [[ -n "${SCHEDULE_THINKING:-}" ]]; then
      cmd+=(--thinking "${SCHEDULE_THINKING}")
    fi

    if [[ "${SCHEDULE_ANNOUNCE:-1}" == "1" ]]; then
      cmd+=(--announce)
    else
      cmd+=(--no-deliver)
    fi

    if [[ -n "${SCHEDULE_MODEL_OVERRIDE:-}" ]]; then
      cmd+=(--model "${SCHEDULE_MODEL_OVERRIDE}")
    fi

    "${cmd[@]}"
    log "created cron job ${JOB_NAME}"
  fi
fi
