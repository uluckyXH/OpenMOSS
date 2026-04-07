if [[ "${INCLUDE_FEISHU_BINDING:-0}" == "1" ]]; then
  REQUIRE_OPENCLAW=1

  section "Bind Feishu account"

  [[ -n "${FEISHU_ACCOUNT_ID:-}" ]] || die "FEISHU_ACCOUNT_ID is required"
  [[ -n "${FEISHU_APP_ID:-}" ]] || die "FEISHU_APP_ID is required"
  [[ -n "${FEISHU_APP_SECRET:-}" ]] || die "FEISHU_APP_SECRET is required"

  CONFIG_PATH="$(eval echo "${OPENCLAW_CONFIG_PATH:-$HOME/.openclaw/openclaw.json}")"
  [[ -f "${CONFIG_PATH}" ]] || die "OpenClaw config file not found: ${CONFIG_PATH}"

  python3 - "${CONFIG_PATH}" "${AGENT_ID}" "${FEISHU_ACCOUNT_ID}" "${FEISHU_APP_ID}" "${FEISHU_APP_SECRET}" "${FEISHU_ACCOUNT_NAME:-}" <<'FEISHU_PY'
import json
import pathlib
import shutil
import sys
import time

config_path = pathlib.Path(sys.argv[1])
agent_id = sys.argv[2]
account_id = sys.argv[3].strip()
app_id = sys.argv[4].strip()
app_secret = sys.argv[5].strip()
account_name = sys.argv[6].strip()

cfg = json.loads(config_path.read_text(encoding="utf-8"))

channels = cfg.setdefault("channels", {})
feishu = channels.setdefault("feishu", {})
feishu.setdefault("enabled", True)
feishu.setdefault("connectionMode", "websocket")
feishu.setdefault("defaultAccount", "default")
feishu.setdefault("dmPolicy", "pairing")
feishu.setdefault("groupPolicy", "allowlist")

if account_id == "default":
    feishu["appId"] = app_id
    feishu["appSecret"] = app_secret
    if account_name:
        feishu["name"] = account_name
else:
    acct_map = feishu.setdefault("accounts", {})
    entry = dict(acct_map.get(account_id) or {})
    entry["enabled"] = True
    entry["appId"] = app_id
    entry["appSecret"] = app_secret
    if account_name:
        entry["name"] = account_name
    acct_map[account_id] = entry

bindings = cfg.setdefault("bindings", [])
next_bindings = []
replaced = False
for binding in bindings:
    match = binding.get("match") if isinstance(binding, dict) else None
    if isinstance(match, dict) and match.get("channel") == "feishu" \
       and (match.get("accountId") or "default") == account_id \
       and "peer" not in match and "guildId" not in match:
        if not replaced:
            next_bindings.append(
                {"agentId": agent_id, "match": {"channel": "feishu", "accountId": account_id}}
            )
            replaced = True
        continue
    next_bindings.append(binding)
if not replaced:
    next_bindings.append({"agentId": agent_id, "match": {"channel": "feishu", "accountId": account_id}})
cfg["bindings"] = next_bindings

backup = config_path.with_name(f"{config_path.name}.pre-feishu-{time.strftime('%Y%m%d-%H%M%S')}.bak")
shutil.copy2(config_path, backup)
config_path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

print(f"Backup: {backup}")
print(f"Account: {account_id}")
print(f"Binding: feishu/{account_id} -> {agent_id}")
FEISHU_PY

  log "bound feishu account ${FEISHU_ACCOUNT_ID} to ${AGENT_ID}"
fi
