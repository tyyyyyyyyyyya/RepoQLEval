import os
import subprocess
import re
from pathlib import Path
#添加c语言标准库

def create_qlpack_file(project_dir):
    """在指定项目目录下创建 qlpack.yml 文件"""
    qlpack_content = """name: test
dependencies:
  # 必须包含cpp标准库
  codeql/cpp-all: "0.4.0"
"""
    qlpack_path = project_dir / "qlpack.yml"
    try:
        with open(qlpack_path, "w", encoding="utf-8") as f:
            f.write(qlpack_content)
        return True, ""
    except Exception as e:
        return False, f"Failed to create qlpack.yml: {str(e)}"


def run_codeql_pack_install(project_dir):
    """在指定项目目录下运行 codeql pack install 命令"""
    cmd = ["codeql", "pack", "install"]
    try:
        result = subprocess.run(
            cmd,
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=300  # 设置超时时间为5分钟
        )
        # 检查输出中是否包含成功标志
        success_pattern = re.compile(r"Already installed|Installed fresh codeql")
        if success_pattern.search(result.stdout) or success_pattern.search(result.stderr):
            return True, result.stdout + result.stderr
        else:
            return False, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return False, "Command timed out"
    except Exception as e:
        return False, str(e)


def batch_process_qlpack(root_dir):
    """批量处理指定目录下的所有项目"""
    root_path = Path(root_dir)
    if not root_path.exists() or not root_path.is_dir():
        print(f"Error: {root_dir} is not a valid directory")
        return

    success_projects = []
    failed_projects = []

    # 遍历根目录下的所有子目录
    for project_dir in root_path.iterdir():
        if project_dir.is_dir():
            print(f"Processing {project_dir.name}...")

            # 创建 qlpack.yml 文件
            print(f"Creating qlpack.yml in {project_dir.name}...")
            success_create, error_create = create_qlpack_file(project_dir)

            if not success_create:
                failed_projects.append((project_dir.name, error_create))
                print(f"{project_dir.name}: Failed to create qlpack.yml")
                continue

            # 运行 codeql pack install 命令
            print(f"Running codeql pack install in {project_dir.name}...")
            success_install, error_install = run_codeql_pack_install(project_dir)

            if success_install:
                success_projects.append(project_dir.name)
                print(f"{project_dir.name}: Success")
            else:
                failed_projects.append((project_dir.name, error_install))
                print(f"{project_dir.name}: Failed to install pack")

    # 输出总结
    print("\n=== Execution Summary ===")
    print(f"Total projects processed: {len(success_projects) + len(failed_projects)}")
    print(f"Successful projects ({len(success_projects)}):")
    for proj in success_projects:
        print(f"  - {proj}")

    print(f"\nFailed projects ({len(failed_projects)}):")
    for proj, error in failed_projects:
        print(f"  - {proj}: {error.strip()[:100]}...")  # 截断错误信息以保持输出简洁


if __name__ == "__main__":
    # 请将此路径替换为实际的根目录路径
    root_directory = r""
    batch_process_qlpack(root_directory)