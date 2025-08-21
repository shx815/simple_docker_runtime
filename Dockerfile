FROM python:3.12-slim

# Shared environment variables 
ENV POETRY_VIRTUALENVS_PATH=/simplerun/poetry \
    MAMBA_ROOT_PREFIX=/simplerun/micromamba \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    EDITOR=code \
    VISUAL=code \
    GIT_EDITOR="code --wait" \
    OPENVSCODE_SERVER_ROOT=/simplerun/.openvscode-server \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    WORK_DIR=/simplerun/workspace \
    HOST=0.0.0.0 \
    PORT=8000 \
    USERNAME=appuser \
    VSCODE_PORT=3000 \
    JUPYTER_PORT=8001

# Install base system dependencies 
RUN set -eux; \
    apt-get update -o Acquire::Retries=5 && \
    apt-get install -y --no-install-recommends --fix-missing \
      wget curl ca-certificates sudo apt-utils git tmux build-essential && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Install uv (required by MCP) 
RUN curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR="/simplerun/bin" sh
# Add /simplerun/bin to PATH
ENV PATH="/simplerun/bin:${PATH}"

# Remove UID 1000 named pn or ubuntu, so the 'simplerun' user can be created from ubuntu hosts
RUN (if getent passwd 1000 | grep -q pn; then userdel pn; fi) && \
    (if getent passwd 1000 | grep -q ubuntu; then userdel ubuntu; fi)

# Create necessary directories 
RUN mkdir -p /simplerun && \
    mkdir -p /simplerun/logs && \
    mkdir -p /simplerun/poetry

# Install micromamba
RUN mkdir -p /simplerun/micromamba/bin && \
    /bin/bash -c "PREFIX_LOCATION=/simplerun/micromamba BIN_FOLDER=/simplerun/micromamba/bin INIT_YES=no CONDA_FORGE_YES=yes $(curl -L https://micro.mamba.pm/install.sh)" && \
    /simplerun/micromamba/bin/micromamba config remove channels defaults && \
    /simplerun/micromamba/bin/micromamba config list

# Create the simplerun virtual environment and install poetry and python
RUN /simplerun/micromamba/bin/micromamba create -n simplerun -y && \
    /simplerun/micromamba/bin/micromamba install -n simplerun -c conda-forge poetry python=3.12 -y

# Configure micromamba and poetry
RUN /simplerun/micromamba/bin/micromamba config set changeps1 False && \
    /simplerun/micromamba/bin/micromamba run -n simplerun poetry config virtualenvs.path /simplerun/poetry

# 创建工作目录 
RUN mkdir -p /simplerun/code && \
    mkdir -p /simplerun/workspace

# 复制Poetry配置文件 (提前复制以利用Docker缓存)
COPY pyproject.toml /simplerun/code/

# 设置工作目录
WORKDIR /simplerun/code

# 为测试与本地运行提供稳定的模块搜索路径
ENV PYTHONPATH=/simplerun/code:/simplerun/code/simplerun

# 使用Poetry安装依赖 (分阶段策略)
RUN /simplerun/micromamba/bin/micromamba run -n simplerun poetry install --only main --no-interaction --no-root

# 安装开发依赖 (包含pytest等测试工具)
RUN /simplerun/micromamba/bin/micromamba run -n simplerun poetry install --only dev --no-interaction --no-root

# 复制应用代码 (在安装依赖之后复制，避免缓存失效)
RUN mkdir -p /simplerun/code/simplerun && \
    touch /simplerun/code/simplerun/__init__.py
COPY simplerun/ /simplerun/code/simplerun/
COPY tests/ /simplerun/code/tests/

# 清理缓存 (缓存清理策略)
RUN /simplerun/micromamba/bin/micromamba run -n simplerun poetry cache clear --all . -n && \
    apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* && \
    /simplerun/micromamba/bin/micromamba clean --all

# 测试Poetry安装是否成功
RUN /simplerun/micromamba/bin/micromamba run -n simplerun poetry --version

# 关键修复：设置 Poetry 虚拟环境的 PATH
RUN /simplerun/micromamba/bin/micromamba run -n simplerun poetry env info --path > /tmp/poetry_env_path.txt && \
    echo "export PATH=\"$(cat /tmp/poetry_env_path.txt)/bin:\$PATH\"" >> /etc/environment && \
    rm /tmp/poetry_env_path.txt

# Set environment variables and permissions (环境变量设置)
RUN /simplerun/micromamba/bin/micromamba run -n simplerun poetry run python -c "import sys; print('OH_INTERPRETER_PATH=' + sys.executable)" >> /etc/environment && \
    chmod -R g+rws /simplerun/poetry

# ================================================================
# Setup VSCode Server 
# ================================================================
# Reference:
# 1. https://github.com/gitpod-io/openvscode-server
# 2. https://github.com/gitpod-io/openvscode-releases

# Setup VSCode Server
ARG RELEASE_TAG="openvscode-server-v1.98.2"
ARG RELEASE_ORG="gitpod-io"

RUN if [ -z "${RELEASE_TAG}" ]; then \
        echo "The RELEASE_TAG build arg must be set." >&2 && \
        exit 1; \
    fi && \
    arch=$(uname -m) && \
    if [ "${arch}" = "x86_64" ]; then \
        arch="x64"; \
    elif [ "${arch}" = "aarch64" ]; then \
        arch="arm64"; \
    elif [ "${arch}" = "armv7l" ]; then \
        arch="armhf"; \
    fi && \
    wget https://github.com/${RELEASE_ORG}/openvscode-server/releases/download/${RELEASE_TAG}/${RELEASE_TAG}-linux-${arch}.tar.gz && \
    tar -xzf ${RELEASE_TAG}-linux-${arch}.tar.gz && \
    if [ -d "${OPENVSCODE_SERVER_ROOT}" ]; then rm -rf "${OPENVSCODE_SERVER_ROOT}"; fi && \
    mv ${RELEASE_TAG}-linux-${arch} ${OPENVSCODE_SERVER_ROOT} && \
    cp ${OPENVSCODE_SERVER_ROOT}/bin/remote-cli/openvscode-server ${OPENVSCODE_SERVER_ROOT}/bin/remote-cli/code && \
    rm -f ${RELEASE_TAG}-linux-${arch}.tar.gz

# 创建用户 (暂时保持原有的用户创建方式)
RUN useradd -m -s /bin/bash appuser \
    && chown -R appuser:appuser /simplerun

# 完全替换 .bashrc 文件，避免任何 PS1 冲突
RUN rm -f /home/appuser/.bashrc \
    && echo '# Minimal .bashrc for App' > /home/appuser/.bashrc \
    && echo 'export PATH=/simplerun/bin:/usr/local/bin:/usr/bin:/bin' >> /home/appuser/.bashrc \
    && echo 'export PATH="/simplerun/poetry/simple-docker-runtime-*/bin:$PATH"' >> /home/appuser/.bashrc \
    && echo 'unset PROMPT_COMMAND' >> /home/appuser/.bashrc \
    && chown appuser:appuser /home/appuser/.bashrc

# 创建 tmux 目录并设置权限
RUN mkdir -p /tmp/tmux-1000 \
    && chown -R appuser:appuser /tmp/tmux-1000 \
    && chmod 700 /tmp/tmux-1000

# 设置文件权限
RUN chmod -R g+rws,o+rw /simplerun/workspace && \
    chmod -R g+rws,o+rw /simplerun/code

# 切换到用户
USER appuser

# 暴露端口
EXPOSE 8000 3000 8001

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/alive || exit 1

# 直接使用 Poetry 虚拟环境的 Python
CMD ["/bin/bash", "-c", "source /etc/environment && /simplerun/micromamba/bin/micromamba run -n simplerun poetry run python -m simplerun.main"]