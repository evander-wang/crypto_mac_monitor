#!/usr/bin/env python3
"""
测试运行脚本
"""

import sys
import subprocess
import os
from pathlib import Path


def run_tests():
    """运行所有测试"""
    project_root = Path(__file__).parent
    os.chdir(project_root)

    print("🧪 开始运行 notifications_v2 模块的单元测试...")
    print("=" * 60)

    # 运行单元测试
    test_commands = [
        # 运行所有 notifications_v2 单元测试
        ["python", "-m", "pytest", "tests/unit/notifications_v2/", "-v", "--tb=short"],
        # 运行测试覆盖率报告
        [
            "python",
            "-m",
            "pytest",
            "tests/unit/notifications_v2/",
            "--cov=notifications_v2",
            "--cov-report=term-missing",
        ],
    ]

    for i, cmd in enumerate(test_commands, 1):
        print(f"\n📋 运行测试命令 {i}/{len(test_commands)}: {' '.join(cmd)}")
        print("-" * 40)

        try:
            result = subprocess.run(cmd, capture_output=False, text=True)
            if result.returncode != 0:
                print(f"❌ 测试命令失败，退出码: {result.returncode}")
                return False
            else:
                print(f"✅ 测试命令成功完成")
        except FileNotFoundError:
            print(f"❌ 命令未找到: {cmd[0]}")
            print("请确保已安装 pytest 和 pytest-cov:")
            print("pip install pytest pytest-cov")
            return False
        except Exception as e:
            print(f"❌ 运行测试时出错: {e}")
            return False

    print("\n" + "=" * 60)
    print("🎉 所有测试完成！")
    return True


def check_dependencies():
    """检查测试依赖"""
    required_packages = ["pytest", "pytest-cov"]
    missing_packages = []

    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
        except ImportError:
            missing_packages.append(package)

    if missing_packages:
        print("❌ 缺少以下测试依赖:")
        for package in missing_packages:
            print(f"  - {package}")
        print("\n请运行以下命令安装:")
        print(f"pip install {' '.join(missing_packages)}")
        return False

    return True


if __name__ == "__main__":
    print("🔍 检查测试依赖...")
    if not check_dependencies():
        sys.exit(1)

    print("✅ 测试依赖检查通过")

    success = run_tests()
    sys.exit(0 if success else 1)
