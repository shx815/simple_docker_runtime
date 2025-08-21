# Simple Docker Runtime

基于 OpenHands 的 runtime 代码创建的 Docker 容器，提供 FastAPI 接口来执行 Bash 命令与插件功能。

## 主要功能

### **核心功能**

#### **1. Bash 命令执行系统**
- 执行 bash 命令
- 支持交互式操作

#### **2. Python 代码执行引擎**
- Jupyter 服务器集成（自动初始化）
- 交互式编程环境
- 支持文本和PNG图片输出

#### **3. 文件操作管理系统**
- 文件读取、写入、编辑
- 文件内容查看（支持 PDF、PNG、JPG、JPEG、GIF）

#### **4. 系统监控与诊断**
- 服务器状态监控
- 资源使用统计（CPU、内存、磁盘、I/O）
- 系统健康检查

#### **5. 插件管理系统**
- **Jupyter 插件**：自动初始化，提供 Python 执行环境
- **AgentSkills 插件**：立即可用，提供文件操作、搜索、PDF/DOCX/LaTeX/PPTX解析等技能
- **VSCode 插件**：手动初始化，提供完整的VSCode开发环境（基于OpenVSCode服务器）
---

## 用户使用指南

### 1. 环境部署

#### 方式一：一键部署脚本（推荐）
```bash
# 进入项目目录
cd simple_docker_runtime

# 给脚本执行权限
chmod +x deploy_and_start.sh

# 运行部署脚本
./deploy_and_start.sh
```

#### 方式二：手动部署
```bash
# 进入项目目录
cd simple_docker_runtime

# 构建 Docker 镜像
docker build -t simple-docker-runtime .

# 启动容器
docker run -d --name simple-runtime \
  -p 8000:8000 -p 3000:3000 -p 8001:8001 \
  -v "$(pwd)/workspace:/workspace" \
  simple-docker-runtime

# 端口说明：
# -p 8000:8000          # 主API服务端口，提供所有API接口
# -p 3000:3000          # VSCode服务器端口，用于Web版VSCode访问
# -p 8001:8001          # Jupyter端口，用于Python代码执行

# 查看启动日志
docker logs -f simple-runtime
```

### 2. API 接口使用

#### 基础服务 API

**健康检查**
```bash
# 检查服务是否存活
curl http://localhost:8000/alive

# 获取服务器详细信息
curl http://localhost:8000/server_info

# 访问根路径
curl http://localhost:8000/
```

**系统监控**
```bash
# 获取系统资源统计
curl http://localhost:8000/system/stats

# 重置 bash session
curl -X POST "http://localhost:8000/reset"
```

#### execute_action 统一接口

**标准命令格式**

所有操作都通过 `/execute_action` 端点执行，使用统一的JSON格式。以下是完整的命令结构说明：

```json
{
  "action": {
    "action": "action_type",           // 动作类型：run(命令执行)、run_ipython(Python代码)、read(文件读取)、write(文件写入)、edit(文件编辑)
    "args": {                          // 动作参数，根据动作类型不同而不同
      "command": "ls -la",            // 命令执行：要执行的bash命令
      "code": "print('Hello')",       // Python执行：要执行的Python代码
      "path": "/path/to/file",        // 文件操作：文件路径
      "content": "file content",      // 文件写入/编辑：文件内容
      "thought": "执行原因说明",       // 可选：执行此动作的思考过程
      "start": 1,                     // 文件编辑：起始行号(1-indexed)
      "end": -1,                      // 文件编辑：结束行号(-1表示文件末尾)
      "command": "str_replace",       // 文件编辑：编辑命令(str_replace, insert等)
      "old_str": "old text",          // 文件编辑：要替换的旧字符串
      "new_str": "new text"           // 文件编辑：新的字符串
    }
  }
}
```

**1. Bash 命令执行**
```bash
# 列出当前目录下的内容
curl -X POST "http://localhost:8000/execute_action" \
  -H "Content-Type: application/json" \
  -d '{
    "action": {
      "action": "run",
      "args": {
        "command": "ls -la",
        "thought": "列出当前目录内容"
      }
    }
  }'

# 显示当前工作目录路径
curl -X POST "http://localhost:8000/execute_action" \
  -H "Content-Type: application/json" \
  -d '{
    "action": {
      "action": "run",
      "args": {
        "command": "pwd",
        "thought": "显示当前工作目录"
      }
    }
  }'

# 切换到指定目录
curl -X POST "http://localhost:8000/execute_action" \
  -H "Content-Type: application/json" \
  -d '{
    "action": {
      "action": "run",
      "args": {
        "command": "cd /workspace",
        "thought": "切换到工作目录"
      }
    }
  }'

# 显示当前登录的用户名
curl -X POST "http://localhost:8000/execute_action" \
  -H "Content-Type: application/json" \
  -d '{
    "action": {
      "action": "run",
      "args": {
        "command": "whoami",
        "thought": "显示当前用户名"
      }
    }
  }'

# 查找指定类型的文件
curl -X POST "http://localhost:8000/execute_action" \
  -H "Content-Type: application/json" \
  -d '{
    "action": {
      "action": "run",
      "args": {
        "command": "find . -name \"*.py\" | head -5",
        "thought": "查找Python文件"
      }
    }
  }'
```

**2. Python 代码执行**
```bash
# 执行简单Python代码
curl -X POST "http://localhost:8000/execute_action" \
  -H "Content-Type: application/json" \
  -d '{
    "action": {
      "action": "run_ipython",
      "args": {
        "code": "print(\"Hello, World!\")"
      }
    }
  }'

# 查看系统信息
curl -X POST "http://localhost:8000/execute_action" \
  -H "Content-Type: application/json" \
  -d '{
    "action": {
      "action": "run_ipython",
      "args": {
        "code": "import os\nprint(f\"Current directory: {os.getcwd()}\")\nprint(f\"Files: {os.listdir(\".\")}\")"
      }
    }
  }'

# 数据处理示例
curl -X POST "http://localhost:8000/execute_action" \
  -H "Content-Type: application/json" \
  -d '{
    "action": {
      "action": "run_ipython",
      "args": {
        "code": "numbers = [1, 2, 3, 4, 5]\nsquared = [x**2 for x in numbers]\nprint(f\"Numbers: {numbers}\")\nprint(f\"Squared: {squared}\")\nprint(f\"Sum: {sum(squared)}\")"
      }
    }
  }'

# 网络请求示例
curl -X POST "http://localhost:8000/execute_action" \
  -H "Content-Type: application/json" \
  -d '{
    "action": {
      "action": "run_ipython",
      "args": {
        "code": "import requests\ntry:\n    response = requests.get(\"https://httpbin.org/get\")\n    print(f\"Status: {response.status_code}\")\n    print(f\"Response: {response.json()}\")\nexcept Exception as e:\n    print(f\"Error: {e}\")"
      }
    }
  }'

# 生成图表示例
curl -X POST "http://localhost:8000/execute_action" \
  -H "Content-Type: application/json" \
  -d '{
    "action": {
      "action": "run_ipython",
      "args": {
        "code": "import matplotlib.pyplot as plt\nimport numpy as np\nx = np.linspace(0, 10, 100)\ny = np.sin(x)\nplt.plot(x, y)\nplt.title(\"Sine Wave\")\nplt.show()"
      }
    }
  }'
```

**3. 文件操作（read/write/edit）**
```bash
# 写入文件（write）
curl -X POST "http://localhost:8000/execute_action" \
  -H "Content-Type: application/json" \
  -d '{
    "action": {
      "action": "write",
      "args": {
        "path": "/workspace/test.txt",
        "content": "这是一个测试文件",
        "thought": "创建测试文件"
      }
    }
  }'

# 编辑文件（edit）
curl -X POST "http://localhost:8000/execute_action" \
  -H "Content-Type: application/json" \
  -d '{
    "action": {
      "action": "edit",
      "args": {
        "path": "/workspace/test.txt",
        "command": "str_replace",
        "old_str": "测试",
        "new_str": "示例",
        "thought": "修改文件内容"
      }
    }
  }'

# 读取文件（read）
curl -X POST "http://localhost:8000/execute_action" \
  -H "Content-Type: application/json" \
  -d '{
    "action": {
      "action": "read",
      "args": {
        "path": "/workspace/test.txt",
        "thought": "查看文件内容"
      }
    }
  }'

# 删除文件
curl -X POST "http://localhost:8000/execute_action" \
  -H "Content-Type: application/json" \
  -d '{
    "action": {
      "action": "run",
      "args": {
        "command": "rm /workspace/test.txt",
        "thought": "清理测试文件"
      }
    }
  }'
```


#### 文件查看端点

**view-file 特殊端点**

除了execute_action统一接口外，还提供专门的文件查看端点：
```bash
# 查看图片文件（PNG、JPG、GIF）
curl "http://localhost:8000/view-file?path=/path/to/your/image.png"

# 查看PDF文件
curl "http://localhost:8000/view-file?path=/path/to/your/document.pdf"

# 注意：/view-file 只支持图片和PDF文件，不支持文本文件
# 文本文件请使用上面的 execute_action——read 文件操作
```



#### 插件管理 API

**插件状态**
```bash
# 获取所有插件状态
curl http://localhost:8000/plugins
```

**VSCode 插件**
```bash
# 初始化 VSCode 插件
curl -X POST "http://localhost:8000/plugins/vscode/initialize" \
  -H "Content-Type: application/json" \
  -d '{"username": "simplerun"}'

# 获取 VSCode 连接URL
curl http://localhost:8000/vscode-url

# 获取 VSCode 连接令牌
curl http://localhost:8000/vscode/connection_token
```

**注意**：
- Jupyter 插件：服务启动时自动初始化，无需手动操作
- AgentSkills 插件：函数集合，立即可用，无需初始化

---

## 开发者使用指南

### 环境配置

**容器内环境说明：**
- 使用 **Poetry** 管理依赖，**micromamba** 管理Python环境
- 容器内Python命令需要：`/simplerun/micromamba/bin/micromamba run -n simplerun poetry run python -c "your_code_here"`

**容器内目录结构：**
```
/simplerun/
├── code/                    # 应用代码
├── workspace/              # 工作目录
├── poetry/                 # Poetry环境
├── micromamba/             # Python环境
└── .openvscode-server/     # VSCode服务器
```

### 项目架构

本项目按照 OpenHands 标准组织类定义，结构清晰：

#### 基础类层次结构

```
Event (基础事件类)
├── Action (动作基类)
│   ├── CmdRunAction (命令执行)
│   ├── IPythonRunCellAction (Python代码执行)
│   ├── FileReadAction (文件读取)
│   ├── FileWriteAction (文件写入)
│   └── FileEditAction (文件编辑)
└── Observation (观察基类)
    ├── CmdOutputObservation (命令输出)
    ├── IPythonRunCellObservation (Python执行输出)
    ├── FileReadObservation (文件读取结果)
    ├── FileWriteObservation (文件写入结果)
    └── FileEditObservation (文件编辑结果)
```

### 功能实现细节

#### **1. Bash 命令执行系统**

**命令执行与解析**
- 支持执行单个 bash 命令，包括管道、重定向、条件语句等
- 通过 bashlex 库进行智能语法解析
- 支持命令链（&&、;）、here document 等复杂语法结构
- 不支持同时执行多条命令

**会话环境管理**
- 基于 tmux 的持久化 shell 环境
- 支持多会话管理，每个会话有唯一标识
- 支持命令历史记录（限制为10,000条）
- 支持切换工作目录并通过 PS1 提示符自动检测工作目录变化

**执行控制与监控**
- 通过 tmux 会话实时获取命令的标准输出和错误输出
- 支持阻塞和非阻塞模式
- 提供两种超时机制（无变化超时默认30秒和硬超时可配置）
- 非阻塞模式下自动触发超时防止命令长时间阻塞

**交互与状态管理**
- 支持与运行中的进程交互，可发送输入数据或特殊控制键（如 Ctrl+C、Ctrl+Z、Ctrl+D 等）
- 实时跟踪命令执行状态（运行中、完成、超时等）
- 自动清理命令输出并处理输出截断

**错误处理与容错**
- 完善的错误处理机制，包括命令解析错误、执行错误、超时错误等异常情况
- 提供详细的错误信息和状态反馈

#### **2. Python 代码执行引擎**

**Jupyter 服务器集成**
- 通过 Jupyter 服务器执行 Python 代码，支持交互式编程
- 自动启动并使用固定端口（8001）

**智能内核管理**
- 自动初始化、内核生命周期管理、心跳检测、连接重连
- 支持 LocalRuntime 和 Docker 容器运行模式

**代码执行与输出**
- 通过 IPythonRunCellAction 执行代码，支持超时设置
- 多种输出类型处理（文本、图片PNG、ANSI转义序列清理）

**环境集成与错误处理**
- 与 Poetry 虚拟环境和 micromamba 环境集成
- 完善的异常捕获和错误信息展示，支持 Linux 系统完整运行

#### **3. 文件操作管理系统**

**文件读取**
- 通过FileReadAction执行，支持相对路径和绝对路径
- 自动基于当前工作目录解析，支持UTF-8编码

**文件写入**
- 通过FileWriteAction执行，支持创建和覆盖文件内容
- 自动创建必要的目录结构

**文件编辑**
- 通过FileEditAction执行，支持字符串替换编辑操作（str_replace命令）

**文件查看**
- 提供/view-file端点，支持查看文件内容
- 生成HTML格式的文件查看器

**统一接口**
- 核心文件操作（读取、写入、编辑）通过/execute_action端点统一处理
- 遵循OpenHands的Action架构

**错误处理**
- 完善的异常处理，包括文件不存在、路径是目录、权限错误、编码错误等情况的处理
- 通过返回相应的Observation对象或HTTP异常提供详细错误信息

#### **4. 系统监控与诊断**

**服务器信息**
- 通过 /server_info 端点提供服务器状态、工作目录、用户名和资源信息

**系统资源监控**
- 通过 /system/stats 端点监控进程 CPU、内存（RSS、VMS、使用百分比）、磁盘使用情况和 I/O 统计

**端口管理**
- 提供端口可用性检查和可用端口查找功能，支持端口范围搜索

#### **5. VSCode 插件**

**OpenVSCode 服务器**
- 集成 OpenVSCode 服务器，提供基于浏览器的代码编辑环境
- 支持端口配置（默认3000）和自动端口检测

**连接管理**
- 生成唯一连接令牌，提供 /vscode-url 和 /vscode/connection_token 端点获取连接信息

**工作区配置**
- 自动创建 .vscode/settings.json 配置文件
- Windows 容器内自动禁用，Linux 容器正常支持

### 开发指南

#### 添加新的 Action 类型

1. 在相应的模块文件中定义新的 Action 类
2. 继承自 `Action` 基类
3. 设置 `action` 属性为唯一的字符串标识
4. 在 `serialization.py` 的 `actions` 元组中添加新类
5. 更新 `__init__.py` 的导出

#### 添加新的 Observation 类型

1. 在相应的模块文件中定义新的 Observation 类
2. 继承自 `Observation` 基类
3. 设置 `observation` 属性为唯一的字符串标识
4. 在 `serialization.py` 的 `observations` 元组中添加新类
5. 更新 `__init__.py` 的导出

### 测试运行

#### 在容器内运行
```bash
# 进入容器
docker exec -it simple-runtime bash

# 切换到代码目录
cd /simplerun/code

# 运行所有测试
/simplerun/micromamba/bin/micromamba run -n simplerun poetry run pytest tests -v

# 或者运行特定测试文件
/simplerun/micromamba/bin/micromamba run -n simplerun poetry run pytest tests/test_bash_session.py -v

# 或者运行特定测试函数
/simplerun/micromamba/bin/micromamba run -n simplerun poetry run pytest tests/test_bash_session.py::test_bash_session_creation -v
```

### 开发流程
1. **修改代码**
2. **停止旧容器**: `docker stop simple-runtime && docker rm simple-runtime`
3. **构建镜像**: `docker build -t simple-docker-runtime .`
4. **启动新容器**: `docker run -d --name simple-runtime -p 8000:8000 -p 3000:3000 -p 8001:8001 -v "$(pwd)/workspace:/workspace" simple-docker-runtime`
5. **验证修改**: 测试新功能是否正常工作

### 开发提示
- 大部分操作与用户指南相同
- 主要区别在于依赖安装和测试运行方式
- 代码修改后需要重新构建镜像才能生效