"""
一键打包各角色 Skill 压缩包
每个 zip 包含标准 Skill 目录：
- SKILL.md
- scripts/task-cli.py
- scripts/task_cli/...
- references/...

用法: python skills/pack-skills.py
输出: skills/dist/ 目录下生成各角色的 zip 文件
"""
import os
import shutil
import zipfile

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DIST_DIR = os.path.join(SCRIPT_DIR, "dist")
SHARED_TASK_CLI_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "tools", "task_cli")

# 角色 Skill 目录列表
SKILL_DIRS = [
    "task-planner-skill",
    "task-executor-skill",
    "task-reviewer-skill",
    "task-patrol-skill",
]

SKIP_NAMES = {".gitkeep", "README.md"}
SKIP_DIRS = {"__pycache__", "templates"}


def _should_skip_file(file_name: str) -> bool:
    return file_name in SKIP_NAMES or file_name.endswith(".pyc")


def _iter_role_files(skill_path: str):
    for root, dirs, files in os.walk(skill_path):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for file_name in files:
            if _should_skip_file(file_name):
                continue
            file_path = os.path.join(root, file_name)
            yield file_path, os.path.relpath(file_path, skill_path)


def _iter_shared_task_cli_files(shared_dir: str):
    for root, dirs, files in os.walk(shared_dir):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for file_name in files:
            if _should_skip_file(file_name):
                continue
            file_path = os.path.join(root, file_name)
            yield file_path, os.path.relpath(file_path, shared_dir)


def _write_dir_entry(zf: zipfile.ZipFile, arcname: str) -> None:
    if not arcname.endswith("/"):
        arcname = f"{arcname}/"
    zf.writestr(arcname, "")


def pack_skill(skill_dir_name, *, dist_dir=DIST_DIR, shared_task_cli_dir=SHARED_TASK_CLI_DIR):
    """打包单个角色的 Skill"""
    skill_path = os.path.join(SCRIPT_DIR, skill_dir_name)
    skill_md = os.path.join(skill_path, "SKILL.md")

    if not os.path.exists(skill_md):
        print(f"  ⚠️  跳过 {skill_dir_name}: SKILL.md 不存在")
        return None

    if not os.path.isdir(shared_task_cli_dir):
        raise FileNotFoundError(f"共享 task_cli 源码目录不存在: {shared_task_cli_dir}")

    zip_name = f"{skill_dir_name}.zip"
    zip_path = os.path.join(dist_dir, zip_name)

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        _write_dir_entry(zf, os.path.join(skill_dir_name, "scripts"))
        _write_dir_entry(zf, os.path.join(skill_dir_name, "scripts", "task_cli"))
        _write_dir_entry(zf, os.path.join(skill_dir_name, "references"))

        for file_path, rel_path in _iter_role_files(skill_path):
            zf.write(file_path, os.path.join(skill_dir_name, rel_path))

        for file_path, rel_path in _iter_shared_task_cli_files(shared_task_cli_dir):
            zf.write(file_path, os.path.join(skill_dir_name, "scripts", "task_cli", rel_path))

    return zip_path


def main():
    # 清理并创建 dist 目录
    if os.path.exists(DIST_DIR):
        shutil.rmtree(DIST_DIR)
    os.makedirs(DIST_DIR)

    print("📦 开始打包 Skill 压缩包...\n")

    for skill_dir in SKILL_DIRS:
        result = pack_skill(skill_dir)
        if result:
            size_kb = os.path.getsize(result) / 1024
            print(f"  ✅ {skill_dir}.zip ({size_kb:.1f} KB)")

    print(f"\n📁 输出目录: {DIST_DIR}")
    print("🎉 打包完成！")


if __name__ == "__main__":
    main()
