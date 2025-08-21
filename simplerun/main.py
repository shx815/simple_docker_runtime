#!/usr/bin/env python3
"""
Simple Docker Runtime - FastAPI Server
使用完全移植的原始bash.py
"""

import os
import sys
import asyncio
import getpass
import subprocess
import traceback
import glob
import re
import time
from contextlib import asynccontextmanager
from typing import Optional, Dict

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from simplerun.models import ServerInfo
from simplerun.bash import BashSession
from simplerun.events.action import CmdRunAction, FileReadAction, FileWriteAction, FileEditAction, IPythonRunCellAction
from simplerun.events.observation import CmdOutputObservation, FileReadObservation, FileWriteObservation, FileEditObservation, IPythonRunCellObservation
from simplerun.utils.system_stats import get_system_stats
from simplerun.utils.file.file_viewer import generate_file_viewer_html

from simplerun.plugins import ALL_PLUGINS, JupyterPlugin, VSCodePlugin
from simplerun.events.serialization import event_from_dict, event_to_dict
from pydantic import BaseModel

# 全局变量
bash_session: Optional[BashSession] = None
# 已初始化的插件实例注册表
PLUGIN_INSTANCES: Dict[str, object] = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global bash_session

    # 启动时初始化bash session
    work_dir = os.environ.get('WORK_DIR', '/workspace')
    username = os.environ.get('USERNAME', getpass.getuser())

    # 确保工作目录存在
    os.makedirs(work_dir, exist_ok=True)

    bash_session = BashSession(work_dir=work_dir, username=username)
    try:
        bash_session.initialize()
        print(f"Bash session initialized in {work_dir} as user {username}")
    except Exception as e:
        print(f"Failed to initialize bash session: {e}")
        bash_session = None

    # 自动初始化核心插件
    if bash_session:
        try:
            jupyter_plugin = JupyterPlugin()
            await jupyter_plugin.initialize(username)
            PLUGIN_INSTANCES["jupyter"] = jupyter_plugin
            print(f"Jupyter plugin auto-initialized for user {username}")
        except Exception as e:
            print(f"Failed to auto-initialize Jupyter plugin: {e}")
        
        # AgentSkills插件无需初始化，函数立即可用
        print("AgentSkills plugin functions are always available (no initialization needed)")

    yield

    # 关闭时清理
    if bash_session:
        bash_session.close()

# 创建FastAPI应用
app = FastAPI(
    title="Simple Docker Runtime",
    description="基于OpenHands的完整bash.py实现的Docker运行时",
    version="1.0.0",
    lifespan=lifespan
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理器"""
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc),
            "type": type(exc).__name__
        }
    )

@app.get("/")
async def root():
    """根路径"""
    return {"message": "Simple Docker Runtime API", "version": "1.0.0"}

@app.get("/alive")
async def alive_check():
    """健康检查端点"""
    return {"status": "alive", "bash_session_active": bash_session is not None and bash_session._initialized}

@app.get("/server_info", response_model=ServerInfo)
async def get_server_info():
    """获取服务器信息"""
    work_dir = os.environ.get('WORK_DIR', '/workspace')
    username = os.environ.get('USERNAME', getpass.getuser())

    cwd = work_dir
    if bash_session and bash_session._initialized:
        try:
            cwd = bash_session.cwd
        except Exception:
            pass

    # 获取系统统计信息
    try:
        resources = get_system_stats()
    except Exception as e:
        resources = {"error": f"Failed to get system stats: {str(e)}"}

    return ServerInfo(
        status="running",
        version="1.0.0",
        cwd=cwd,
        username=username,
        resources=resources
    )

@app.get("/system/stats")
async def get_system_stats_api():
    """获取系统统计信息
    
    基于你已有的get_system_stats函数，提供专业的系统统计API
    """
    try:
        stats = get_system_stats()
        return {
            "status": "success",
            "system_stats": stats,
            "timestamp": time.time()
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get system stats: {str(e)}"
        )





@app.post("/reset")
async def reset_session():
    """重置bash session"""
    global bash_session

    if bash_session:
        bash_session.close()

    work_dir = os.environ.get('WORK_DIR', '/workspace')
    username = os.environ.get('USERNAME', getpass.getuser())

    try:
        bash_session = BashSession(work_dir=work_dir, username=username)
        bash_session.initialize()
        return {"message": "Bash session reset successfully"}
    except Exception as e:
        bash_session = None
        raise HTTPException(
            status_code=500,
            detail=f"Failed to reset bash session: {str(e)}"
        )

@app.post("/test/run")
async def run_tests(test_pattern: str = "*", verbose: bool = False):
    """运行测试的API端点
    
    基于OpenHands的测试运行模式，使用查询参数
    """
    try:
        # 检查测试目录是否存在 - 使用完整路径
        test_dir = "/simplerun/code/tests"
        if not os.path.exists(test_dir):
            return JSONResponse(
                status_code=404,
                content={
                    "error": "Tests directory not found",
                    "detail": f"Test directory {test_dir} does not exist"
                }
            )
        
        # 使用你的实际测试方式：micromamba + poetry
        micromamba_path = "/simplerun/micromamba/bin/micromamba"
        poetry_path = "/simplerun/micromamba/envs/simplerun/bin/poetry"
        
        # 如果路径不存在，尝试其他路径
        if not os.path.exists(micromamba_path):
            micromamba_path = "/usr/local/bin/micromamba"
        if not os.path.exists(poetry_path):
            poetry_path = "/usr/local/bin/poetry"
        
        # 构建测试命令：micromamba run -n simplerun poetry run pytest
        cmd = [
            micromamba_path, "run", "-n", "simplerun",
            poetry_path, "run", "pytest",
            test_dir,
            "-v" if verbose else "-q",
            "--tb=short"
        ]
        
        # 如果指定了测试模式，添加-k参数
        if test_pattern and test_pattern != "*":
            cmd.extend(["-k", test_pattern])
        
        # 设置Poetry环境变量
        env = {
            **os.environ,
            "PYTHONPATH": "/simplerun/code:/simplerun/code/simplerun",
            "PATH": "/simplerun/micromamba/envs/simplerun/bin:/usr/local/bin:/usr/bin:/bin",
            "PYTHONUNBUFFERED": "1",
            "POETRY_VENV_IN_PROJECT": "1"
        }
        
        # 运行测试
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd="/simplerun/code",
            env=env,
            timeout=300  # 5分钟超时
        )
        
        return {
            "status": "completed",
            "return_code": result.returncode,
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "command": " ".join(cmd),
            "micromamba_path": micromamba_path,
            "poetry_path": poetry_path,
            "test_dir": test_dir
        }
        
    except subprocess.TimeoutExpired:
        return JSONResponse(
            status_code=408,
            content={
                "error": "Test execution timed out after 5 minutes",
                "detail": "Tests are taking too long to complete"
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "error": f"Failed to run tests: {str(e)}",
                "traceback": traceback.format_exc()
            }
        )


@app.get("/test/list")
async def list_tests():
    """列出可用的测试"""
    try:
        test_dir = "/simplerun/code/tests"
        if not os.path.exists(test_dir):
            return JSONResponse(
                status_code=404,
                content={
                    "error": "Tests directory not found",
                    "detail": f"Test directory {test_dir} does not exist"
                }
            )
        
        # 查找所有测试文件
        test_files = []
        for pattern in ["test_*.py", "*_test.py"]:
            test_files.extend(glob.glob(os.path.join(test_dir, pattern)))
        
        # 获取测试文件信息
        test_info = []
        for test_file in sorted(test_files):
            try:
                with open(test_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 简单解析测试函数
                test_functions = re.findall(r'def\s+(test_\w+)', content)
                
                test_info.append({
                    "file": os.path.basename(test_file),
                    "path": test_file,
                    "test_functions": test_functions,
                    "test_count": len(test_functions)
                })
            except Exception as e:
                test_info.append({
                    "file": os.path.basename(test_file),
                    "path": test_file,
                    "error": str(e)
                })
        
        return {
            "test_directory": test_dir,
            "total_files": len(test_files),
            "total_tests": sum(t.get("test_count", 0) for t in test_info),
            "tests": test_info
        }
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "error": f"Failed to list tests: {str(e)}",
                "traceback": traceback.format_exc()
            }
        )


@app.post("/test/run-single")
async def run_single_test(test_file: str, test_function: str = None):
    """运行单个测试文件或测试函数
    
    基于OpenHands的测试运行模式，使用查询参数
    """
    try:
        test_dir = "/simplerun/code/tests"
        test_path = os.path.join(test_dir, test_file)
        
        if not os.path.exists(test_path):
            return JSONResponse(
                status_code=404,
                content={
                    "error": "Test file not found",
                    "detail": f"Test file {test_path} does not exist"
                }
            )
        
        # 使用你的实际测试方式：micromamba + poetry
        micromamba_path = "/simplerun/micromamba/bin/micromamba"
        poetry_path = "/simplerun/micromamba/envs/simplerun/bin/poetry"
        
        # 如果路径不存在，尝试其他路径
        if not os.path.exists(micromamba_path):
            micromamba_path = "/usr/local/bin/micromamba"
        if not os.path.exists(poetry_path):
            poetry_path = "/usr/local/bin/poetry"
        
        # 构建测试命令：micromamba run -n simplerun poetry run pytest
        cmd = [
            micromamba_path, "run", "-n", "simplerun",
            poetry_path, "run", "pytest",
            test_path,
            "-v",
            "--tb=short"
        ]
        
        # 如果指定了测试函数，添加-k参数
        if test_function:
            cmd.extend(["-k", test_function])
        
        # 设置Poetry环境变量
        env = {
            **os.environ,
            "PYTHONPATH": "/simplerun/code:/simplerun/code/simplerun",
            "PATH": "/simplerun/micromamba/envs/simplerun/bin:/usr/local/bin:/usr/bin:/bin",
            "PYTHONUNBUFFERED": "1",
            "POETRY_VENV_IN_PROJECT": "1"
        }
        
        # 运行测试
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd="/simplerun/code",
            env=env,
            timeout=300  # 5分钟超时
        )
        
        return {
            "status": "completed",
            "return_code": result.returncode,
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "command": " ".join(cmd),
            "test_file": test_file,
            "test_function": test_function,
            "micromamba_path": micromamba_path,
            "poetry_path": poetry_path,
            "test_path": test_path
        }
        
    except subprocess.TimeoutExpired:
        return JSONResponse(
            status_code=408,
            content={
                "error": "Test execution timed out after 5 minutes",
                "detail": "Tests are taking too long to complete"
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "error": f"Failed to run single test: {str(e)}",
                "detail": traceback.format_exc()
            }
        )

# 移除独立的文件操作API端点，统一通过 /execute_action 处理
# 参考 OpenHands 的架构设计

@app.get("/view-file")
async def view_file(path: str):
    """查看文件内容"""
    try:
        if not os.path.isabs(path):
            raise HTTPException(status_code=400, detail="Path must be absolute")
        
        if not os.path.exists(path):
            raise HTTPException(status_code=404, detail="File not found")
        
        if os.path.isdir(path):
            raise HTTPException(status_code=400, detail="Path is a directory")
        
        html_content = generate_file_viewer_html(path)
        return HTMLResponse(content=html_content)
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error viewing file: {str(e)}")


@app.get("/vscode/connection_token")
async def get_vscode_connection_token():
    """获取VSCode连接令牌
    
    基于OpenHands的VSCode插件API，提供连接令牌
    """
    plugin = PLUGIN_INSTANCES.get("vscode")
    if plugin is None or not isinstance(plugin, VSCodePlugin):
        raise HTTPException(
            status_code=400, 
            detail="VSCode plugin is not initialized. Call /plugins/vscode/initialize first."
        )
    
    try:
        # 直接访问插件的属性，就像OpenHands做的那样
        token = plugin.vscode_connection_token
        if not token:
            raise HTTPException(
                status_code=400,
                detail="VSCode plugin not properly initialized or token not available"
            )
        return {
            "status": "success",
            "connection_token": token,
            "note": "Use this token to connect VSCode to the runtime"
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get VSCode connection token: {str(e)}"
        )

@app.get("/vscode-url")
async def get_vscode_url():
    """获取VSCode连接URL
    
    基于OpenHands的VSCode插件API，提供连接URL
    """
    plugin = PLUGIN_INSTANCES.get("vscode")
    if plugin is None or not isinstance(plugin, VSCodePlugin):
        raise HTTPException(
            status_code=400, 
            detail="VSCode plugin is not initialized. Call /plugins/vscode/initialize first."
        )
    
    try:
        # 直接构建URL，就像OpenHands做的那样
        token = plugin.vscode_connection_token
        port = plugin.vscode_port
        if not token or not port:
            raise HTTPException(
                status_code=400,
                detail="VSCode plugin not properly initialized or token/port not available"
            )
        
        # 构建VSCode URL，使用localhost（容器内访问）
        vscode_url = f"http://localhost:{port}/?tkn={token}&folder=/workspace"
        
        return {
            "status": "success",
            "vscode_url": vscode_url,
            "note": "Use this URL to open VSCode in browser or connect desktop VSCode"
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get VSCode URL: {str(e)}"
        )

@app.get("/plugins")
async def get_plugins():
    """获取可用插件列表和状态"""
    plugin_status = {}
    
    for name, plugin_class in ALL_PLUGINS.items():
        if name == "jupyter":
            # Jupyter自动初始化
            status = "auto_initialized" if name in PLUGIN_INSTANCES else "auto_initializing"
            note = "Auto-initializes on startup"
        elif name == "agent_skills":
            # AgentSkills无需初始化
            status = "always_available"
            note = "Function collection, no initialization needed"
        else:
            # 其他插件需要手动初始化
            status = "initialized" if name in PLUGIN_INSTANCES else "not_initialized"
            note = "Requires manual initialization"
        
        plugin_status[name] = {
            "name": plugin_class.name,
            "type": plugin_class.__name__,
            "status": status,
            "note": note
        }
    
    return {
        "available_plugins": list(ALL_PLUGINS.keys()),
        "plugin_count": len(ALL_PLUGINS),
        "plugins": plugin_status,
        "summary": {
            "auto_initialized": len([p for p in plugin_status.values() if p["status"] == "auto_initialized"]),
            "always_available": len([p for p in plugin_status.values() if p["status"] == "always_available"]),
            "manual_required": len([p for p in plugin_status.values() if p["status"] in ["initialized", "not_initialized"]])
        }
    }


@app.post("/plugins/{plugin_name}/initialize")
async def initialize_plugin(plugin_name: str, username: str = "simplerun"):
    """初始化指定插件
    
    注意：
    - Jupyter插件会在服务启动时自动初始化，无需手动初始化
    - AgentSkills插件是函数集合，无需初始化，可直接使用
    - 只有VSCode等需要运行时状态的插件需要手动初始化
    """
    if plugin_name not in ALL_PLUGINS:
        raise HTTPException(status_code=404, detail=f"Plugin '{plugin_name}' not found")
    
    # 检查插件类型
    if plugin_name == "jupyter":
        raise HTTPException(
            status_code=400, 
            detail="Jupyter plugin auto-initializes on startup, no manual initialization needed"
        )
    
    if plugin_name == "agent_skills":
        raise HTTPException(
            status_code=400, 
            detail="AgentSkills plugin is a function collection, no initialization needed. Functions can be called directly in Python code."
        )
    
    try:
        plugin_class = ALL_PLUGINS[plugin_name]
        plugin_instance = plugin_class()
        await plugin_instance.initialize(username)
        # 保存实例，供后续调用
        PLUGIN_INSTANCES[plugin_name] = plugin_instance
        return {
            "status": "success",
            "plugin": plugin_name,
            "message": f"Plugin '{plugin_name}' initialized successfully",
            "note": "This plugin requires manual initialization"
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to initialize plugin '{plugin_name}': {str(e)}"
        )


class ActionRequest(BaseModel):
    action: dict




@app.post("/execute_action")
async def execute_action(action_request: ActionRequest):
    """执行 OpenHands Action - 支持所有 Action 类型"""
    if not bash_session:
        raise HTTPException(
            status_code=503,
            detail="Bash session not available. Please check server status."
        )

    if not bash_session._initialized:
        raise HTTPException(
            status_code=503,
            detail="Bash session not initialized. Please check server status."
        )

    try:
        # 从字典创建 Action 对象 - 直接传递 action_request.action
        action = event_from_dict(action_request.action)
        
        # 根据 Action 类型执行相应的操作
        if isinstance(action, CmdRunAction):
            # 执行 bash 命令
            observation = bash_session.execute(action)
            return event_to_dict(observation)
            
        elif isinstance(action, IPythonRunCellAction):
            # 执行 Python 代码 - Jupyter自动可用
            plugin = PLUGIN_INSTANCES.get("jupyter")
            if plugin is None or not isinstance(plugin, JupyterPlugin):
                # 如果Jupyter未初始化，自动初始化
                try:
                    print("Auto-initializing Jupyter plugin...")
                    jupyter_plugin = JupyterPlugin()
                    await jupyter_plugin.initialize("simplerun")
                    PLUGIN_INSTANCES["jupyter"] = jupyter_plugin
                    plugin = jupyter_plugin
                    print("Jupyter plugin auto-initialized successfully")
                except Exception as e:
                    print(f"Failed to auto-initialize Jupyter plugin: {e}")
                    raise HTTPException(status_code=500, detail=f"Failed to auto-initialize Jupyter: {str(e)}")
            
            try:
                observation = await plugin.run(action)
                return event_to_dict(observation)
            except Exception as e:
                print(f"Error executing Python code: {e}")
                # 返回错误观察结果
                error_obs = IPythonRunCellObservation(
                    content=f"Error executing Python code: {str(e)}",
                    code=action.code,
                    image_urls=None,
                )
                return event_to_dict(error_obs)
            
        elif isinstance(action, FileReadAction):
            # 读取文件
            observation = await read_file_action(action)
            return event_to_dict(observation)
            
        elif isinstance(action, FileWriteAction):
            # 写入文件
            observation = await write_file_action(action)
            return event_to_dict(observation)
            
        elif isinstance(action, FileEditAction):
            # 编辑文件
            observation = await edit_file_action(action)
            return event_to_dict(observation)
            
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported action type: {type(action).__name__}")
            
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "error": str(e),
                "traceback": traceback.format_exc()
            }
        )

async def read_file_action(action: FileReadAction) -> FileReadObservation:
    """读取文件内容"""
    if not bash_session:
        raise HTTPException(status_code=503, detail="Bash session not available")
    
    working_dir = bash_session.cwd
    filepath = action.path if os.path.isabs(action.path) else os.path.join(working_dir, action.path)
    
    try:
        if not os.path.exists(filepath):
            return FileReadObservation(
                content=f"File not found: {filepath}. Your current working directory is {working_dir}.",
                path=filepath
            )
        
        if os.path.isdir(filepath):
            return FileReadObservation(
                content=f"Path is a directory: {filepath}. You can only read files",
                path=filepath
            )
        
        # 读取文件内容
        with open(filepath, 'r', encoding='utf-8') as file:
            content = file.read()
            
        return FileReadObservation(
            content=content,
            path=filepath
        )
        
    except Exception as e:
        return FileReadObservation(
            content=f"Error reading file {filepath}: {str(e)}",
            path=filepath
        )

async def write_file_action(action: FileWriteAction) -> FileWriteObservation:
    """写入文件内容"""
    if not bash_session:
        raise HTTPException(status_code=503, detail="Bash session not available")
    
    working_dir = bash_session.cwd
    filepath = action.path if os.path.isabs(action.path) else os.path.join(working_dir, action.path)
    
    try:
        # 确保目录存在
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        # 写入文件
        with open(filepath, 'w', encoding='utf-8') as file:
            file.write(action.content)
            
        return FileWriteObservation(
            content="File written successfully",
            path=filepath
        )
        
    except Exception as e:
        return FileWriteObservation(
            content=f"Error writing file {filepath}: {str(e)}",
            path=filepath
        )

async def edit_file_action(action: FileEditAction) -> FileEditObservation:
    """编辑文件内容"""
    if not bash_session:
        raise HTTPException(status_code=503, detail="Bash session not available")
    
    working_dir = bash_session.cwd
    filepath = action.path if os.path.isabs(action.path) else os.path.join(working_dir, action.path)
    
    try:
        if not os.path.exists(filepath):
            return FileEditObservation(
                content=f"File not found: {filepath}",
                path=filepath
            )
        
        # 读取原文件内容
        with open(filepath, 'r', encoding='utf-8') as file:
            old_content = file.read()
        
        # 执行编辑操作
        if action.command == "str_replace" and action.old_str and action.new_str:
            new_content = old_content.replace(action.old_str, action.new_str)
        else:
            new_content = old_content
        
        # 写入新内容
        with open(filepath, 'w', encoding='utf-8') as file:
            file.write(new_content)
            
        return FileEditObservation(
            content="File edited successfully",
            path=filepath,
            old_content=action.old_str,
            new_content=action.new_str
        )
        
    except Exception as e:
        return FileEditObservation(
            content=f"Error editing file {filepath}: {str(e)}",
            path=filepath
        )

def main():
    """主函数"""
    # 从环境变量获取配置
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', '8000'))

    print(f"Starting Simple Docker Runtime on {host}:{port}")
    print(f"Work directory: {os.environ.get('WORK_DIR', '/workspace')}")
    print(f"Username: {os.environ.get('USERNAME', getpass.getuser())}")

    # 运行服务器
    uvicorn.run(
        "simplerun.main:app",
        host=host,
        port=port,
        reload=False,
        log_level="info"
    )

if __name__ == "__main__":
    main()