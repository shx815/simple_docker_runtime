#!/usr/bin/env python3
"""
精简的Python命令测试
专注于核心功能验证，避免重复和耗时测试
"""

import subprocess
import time

def run_python_command(command):
    """运行Python命令并返回结果"""
    try:
        result = subprocess.run(
            ["python", "-c", command],
            capture_output=True,
            text=True,
            timeout=5  # 减少超时时间
        )
        return result.returncode == 0, result.stdout.strip(), result.stderr.strip()
    except Exception as e:
        return False, "", str(e)

def test_basic_commands():
    """测试基础命令 - 核心系统命令"""
    print("=== 测试基础命令 ===")
    
    commands = [
        {
            "name": "pwd",
            "command": "import requests; print(requests.post('http://localhost:8000/execute_action', json={'action': {'action': 'run', 'args': {'command': 'pwd'}}}).json()['content'])",
            "expected_patterns": ["/workspace", "/tmp", "/app"]
        },
        {
            "name": "whoami",
            "command": "import requests; print(requests.post('http://localhost:8000/execute_action', json={'action': {'action': 'run', 'args': {'command': 'whoami'}}}).json()['content'])",
            "expected_output": "appuser"
        }
    ]
    
    for cmd in commands:
        print(f"\n--- {cmd['name']} ---")
        success, output, error = run_python_command(cmd['command'])
        if success:
            print(f"结果: '{output}'")
            
            if "expected_patterns" in cmd:
                matched = any(pattern in output for pattern in cmd["expected_patterns"])
                if matched:
                    print(f"✓ 验证通过: 结果匹配预期模式")
                else:
                    print(f"✗ 验证失败: 期望匹配 {cmd['expected_patterns']}, 实际结果: '{output}'")
            else:
                if cmd["expected_output"] == output:
                    print(f"✓ 验证通过: 结果完全匹配")
                else:
                    print(f"✗ 验证失败: 期望 '{cmd['expected_output']}', 实际结果: '{output}'")
        else:
            print(f"错误: {error}")

def test_python_code():
    """测试Python代码执行 - 核心Jupyter功能"""
    print("\n=== 测试Python代码执行 ===")
    
    commands = [
        {
            "name": "print(123)",
            "command": "import requests; print(requests.post('http://localhost:8000/execute_action', json={'action': {'action': 'run_ipython', 'args': {'code': 'print(123)'}}}).json()['content'])",
            "expected_output": "123"
        },
        {
            "name": "import os",
            "command": "import requests; print(requests.post('http://localhost:8000/execute_action', json={'action': {'action': 'run_ipython', 'args': {'code': 'import os; print(os.getcwd())'}}}).json()['content'])",
            "expected_patterns": ["/workspace", "/tmp", "/app"]
        }
    ]
    
    for cmd in commands:
        print(f"\n--- {cmd['name']} ---")
        success, output, error = run_python_command(cmd['command'])
        if success:
            print(f"结果: '{output}'")
            
            if "expected_patterns" in cmd:
                matched = any(pattern in output for pattern in cmd["expected_patterns"])
                if matched:
                    print(f"✓ 验证通过: 结果匹配预期模式")
                else:
                    print(f"✗ 验证失败: 期望匹配 {cmd['expected_patterns']}, 实际结果: '{output}'")
            else:
                if cmd["expected_output"] == output:
                    print(f"✓ 验证通过: 结果完全匹配")
                else:
                    print(f"✗ 验证失败: 期望 '{cmd['expected_output']}', 实际结果: '{output}'")
        else:
            print(f"错误: {error}")

def test_api_endpoints():
    """测试核心API端点"""
    print("\n=== 测试API端点 ===")
    
    commands = [
        {
            "name": "health check",
            "command": "import requests; print(requests.get('http://localhost:8000/alive').json())",
            "expected_patterns": ["alive", "bash_session_active", "True"]
        }
    ]
    
    for cmd in commands:
        print(f"\n--- {cmd['name']} ---")
        success, output, error = run_python_command(cmd['command'])
        if success:
            print(f"结果: '{output}'")
            
            all_patterns_found = all(pattern in output for pattern in cmd["expected_patterns"])
            if all_patterns_found:
                print(f"✓ 验证通过: 结果包含所有预期模式")
            else:
                missing_patterns = [p for p in cmd["expected_patterns"] if p not in output]
                print(f"✗ 验证失败: 缺少模式 {missing_patterns}")
        else:
            print(f"错误: {error}")

def main():
    """主函数"""
    print("开始精简的Python命令测试")
    print("=" * 50)
    
    # 检查服务器状态
    print("检查服务器状态...")
    success, output, error = run_python_command(
        "import requests; print(requests.get('http://localhost:8000/alive').json())"
    )
    
    if not success:
        print("服务器未运行，请先启动服务器")
        return
    
    print("服务器运行正常，开始测试...")
    
    # 运行核心测试
    test_basic_commands()
    test_python_code()
    test_api_endpoints()
    
    print("\n" + "=" * 50)
    print("测试完成")

if __name__ == "__main__":
    main() 