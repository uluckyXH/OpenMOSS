section "Download skill bundle"

[[ -n "${BOOTSTRAP_SKILL_BUNDLE_TOKEN:-}" ]] || die "BOOTSTRAP_SKILL_BUNDLE_TOKEN is required"
[[ -n "${BOOTSTRAP_SKILL_BUNDLE_PATH:-}" ]] || die "BOOTSTRAP_SKILL_BUNDLE_PATH is required"

curl -fsS -H "X-Bootstrap-Token: ${BOOTSTRAP_SKILL_BUNDLE_TOKEN}" \
  "${OPENMOSS_URL}${BOOTSTRAP_SKILL_BUNDLE_PATH}" \
  -o "${SKILL_BUNDLE_ARCHIVE}"
log "downloaded skill-bundle archive to ${SKILL_BUNDLE_ARCHIVE}"

python3 - <<'PY' "${SKILL_BUNDLE_ARCHIVE}" "${SKILLS_ROOT_DIR}" "${SKILL_DIR}"
import shutil
import sys
import zipfile
from pathlib import Path

archive_path = Path(sys.argv[1])
skills_root_dir = Path(sys.argv[2])
skill_dir = Path(sys.argv[3])

if skill_dir.exists():
    shutil.rmtree(skill_dir)
skills_root_dir.mkdir(parents=True, exist_ok=True)

with zipfile.ZipFile(archive_path, "r") as zf:
    zf.extractall(skills_root_dir)
PY

chmod +x "${TASK_CLI_PATH}"
log "installed skill bundle to ${SKILL_DIR}"
log "task-cli entry ready at ${TASK_CLI_PATH}"
