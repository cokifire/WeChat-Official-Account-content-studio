#!/usr/bin/env python3
"""Initialize the Python environment required by the WeWrite skill."""

from __future__ import print_function

import os
import shutil
import subprocess
import sys
from pathlib import Path


MIN_PYTHON = (3, 10)
SKILL_ROOT = Path(__file__).resolve().parent.parent
VENV_DIR = SKILL_ROOT / ".venv"
REQUIREMENTS = SKILL_ROOT / "requirements.txt"
REQUIRED_IMPORTS = ("markdown", "bs4", "cssutils", "requests", "yaml", "pygments", "PIL")


def run(command, capture=False):
    """Run one command without invoking a shell."""
    return subprocess.run(
        [str(part) for part in command],
        check=False,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
        text=True,
    )


def venv_python():
    if os.name == "nt":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def python_candidates():
    configured = os.environ.get("WEWRITE_PYTHON", "").strip()
    if configured:
        yield [configured]

    existing_venv = venv_python()
    if existing_venv.is_file():
        yield [str(existing_venv)]

    for name in ("python3.13", "python3.12", "python3.11", "python3.10", "python3", "python"):
        executable = shutil.which(name)
        if executable:
            yield [executable]

    if os.name == "nt" and shutil.which("py"):
        for version in ("-3.13", "-3.12", "-3.11", "-3.10"):
            yield ["py", version]


def supports_required_python(command):
    try:
        check = run(
            command
            + [
                "-c",
                "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)",
            ],
            capture=True,
        )
    except OSError:
        return False
    return check.returncode == 0


def restart_with_compatible_python():
    for command in python_candidates():
        if supports_required_python(command):
            completed = run(command + [str(Path(__file__).resolve())] + sys.argv[1:])
            return completed.returncode

    print("错误：未检测到 Python 3.10 或更高版本。", file=sys.stderr)
    print("请先安装兼容版本，或通过 WEWRITE_PYTHON 指定解释器路径。", file=sys.stderr)
    return 2


def check_pwsh():
    executable = shutil.which("pwsh") or shutil.which("pwsh.exe")
    if not executable:
        return None

    result = run(
        [executable, "-NoProfile", "-Command", "$PSVersionTable.PSVersion.Major"],
        capture=True,
    )
    if result.returncode != 0:
        return None

    try:
        major = int(result.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return None
    return executable if major >= 7 else None


def main():
    if sys.version_info < MIN_PYTHON:
        return restart_with_compatible_python()

    if not (SKILL_ROOT / "SKILL.md").is_file() or not REQUIREMENTS.is_file():
        print("错误：初始化脚本必须从完整的 WeWrite Skill 目录运行。", file=sys.stderr)
        return 2

    python = venv_python()
    if python.exists() and not supports_required_python([str(python)]):
        print(f"错误：现有虚拟环境版本低于 Python 3.10：{VENV_DIR}", file=sys.stderr)
        print("请移走该虚拟环境后重新运行初始化脚本。", file=sys.stderr)
        return 2

    if not python.exists():
        print(f"[1/3] 创建虚拟环境：{VENV_DIR}", flush=True)
        result = run([sys.executable, "-m", "venv", str(VENV_DIR)])
        if result.returncode != 0:
            print("错误：虚拟环境创建失败。", file=sys.stderr)
            return result.returncode or 1
    else:
        print(f"[1/3] 使用现有虚拟环境：{VENV_DIR}", flush=True)

    print("[2/3] 安装 Python 依赖", flush=True)
    result = run(
        [str(python), "-m", "pip", "install", "--disable-pip-version-check", "-r", str(REQUIREMENTS)]
    )
    if result.returncode != 0:
        print("错误：Python 依赖安装失败。", file=sys.stderr)
        return result.returncode or 1

    import_check = "; ".join(f"import {name}" for name in REQUIRED_IMPORTS)
    result = run([str(python), "-c", import_check], capture=True)
    if result.returncode != 0:
        print("错误：Python 依赖验证失败。", file=sys.stderr)
        if result.stderr:
            print(result.stderr.strip(), file=sys.stderr)
        return 1

    print("[3/3] 检查 PowerShell 7", flush=True)
    pwsh = check_pwsh()
    if not pwsh:
        print("错误：未检测到 PowerShell 7 的 pwsh 命令。", file=sys.stderr)
        print("安装 PowerShell 7 后重新运行本脚本即可完成检查。", file=sys.stderr)
        return 2

    print("\nWeWrite Skill 初始化完成。")
    print(f"Skill 目录：{SKILL_ROOT}")
    print(f"Python：{python}")
    print(f"PowerShell：{pwsh}")
    print("下一步：在 Codex 中输入“$wewrite 重新设置风格”。")
    print("仅在需要发布到微信草稿箱时，才需要创建 config.yaml。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
