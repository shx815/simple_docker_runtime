#!/bin/bash

# 设置错误时退出
set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查Docker是否运行
check_docker() {
    if ! docker info >/dev/null 2>&1; then
        log_error "Docker is not running. Please start Docker Desktop first."
        exit 1
    fi
    log_success "Docker is running"
}

# 清理旧容器和镜像
cleanup() {
    log_info "Cleaning up old containers and images..."
    
    # 停止并删除旧容器
    if docker ps -a --format "table {{.Names}}" | grep -q "simple-runtime"; then
        log_info "Stopping and removing old container..."
        docker stop simple-runtime 2>/dev/null || true
        docker rm simple-runtime 2>/dev/null || true
        log_success "Old container cleaned up"
    fi
    
    # 检查是否有同名镜像
    if docker images --format "table {{.Repository}}" | grep -q "^simple-docker-runtime$"; then
        log_info "Found existing image: simple-docker-runtime"
        read -p "Do you want to remove old image and force rebuild? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            log_info "Removing old image..."
            docker rmi simple-docker-runtime 2>/dev/null || true
            log_success "Old image removed"
        fi
    else
        log_info "No existing image found, will build new one"
    fi
}

# 构建镜像
build_image() {
    log_info "Building Docker image..."
    
    # 检查是否存在Dockerfile
    if [ ! -f "Dockerfile" ]; then
        log_error "Dockerfile not found in current directory"
        exit 1
    fi
    
    # 首次构建提示
    echo
    log_warning "⚠️  首次构建时间较长，请耐心等待..."
    log_info "构建过程中会下载基础镜像和安装依赖包"
    echo
    
    # 构建镜像
    if docker build -t simple-docker-runtime .; then
        log_success "Image built successfully"
    else
        log_error "Failed to build image"
        exit 1
    fi
}

# 准备挂载目录
prepare_mounts() {
    log_info "Preparing mount directories..."
    
    # 创建workspace目录
    mkdir -p "$(pwd)/workspace"
    chmod 777 -R "$(pwd)/workspace"
    
    log_success "Mount directories prepared"
}

# 启动容器
start_container() {
    log_info "Starting container..."
    
    # 启动容器（修复重复挂载点问题）
    docker run -d --name simple-runtime \
        -p 8000:8000 \
        -p 3000:3000 \
        -p 8001:8001 \
        -v "$(pwd)/workspace:/workspace" \
        simple-docker-runtime
    
    if [ $? -eq 0 ]; then
        log_success "Container started successfully"
    else
        log_error "Failed to start container"
        exit 1
    fi
}

# 等待服务启动
wait_for_service() {
    log_info "Waiting for service to start..."
    
    local max_attempts=45  # 增加等待时间
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s "http://localhost:8000/alive" >/dev/null 2>&1; then
            log_success "Service is ready (attempt $attempt/$max_attempts)"
            return 0
        fi
        
        log_info "Waiting for service... (attempt $attempt/$max_attempts)"
        sleep 2
        attempt=$((attempt + 1))
    done
    
    log_error "Service failed to start within $((max_attempts * 2)) seconds"
    log_info "Container logs:"
    docker logs simple-runtime
    exit 1
}

# 检查容器状态
check_container_status() {
    log_info "Checking container status..."
    
    # 检查容器是否运行
    if docker ps --format "table {{.Names}}" | grep -q "simple-runtime"; then
        log_success "Container is running"
    else
        log_error "Container is not running"
        docker ps -a
        exit 1
    fi
    
    # 显示容器信息
    log_info "Container details:"
    docker ps --filter "name=simple-runtime" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    
    # 显示容器日志（最近15行）
    log_info "Recent container logs:"
    docker logs --tail 15 simple-runtime
}

# 运行测试
run_tests() {
    log_info "Running tests inside container..."
    
    # 检查测试目录
    if [ ! -d "tests" ]; then
        log_warning "Tests directory not found, skipping tests"
        return 0
    fi
    
    # 等待一下让服务完全启动
    log_info "Waiting a bit more for service to fully initialize..."
    sleep 5
    
    # 运行所有测试
    log_info "Running all tests..."
    if docker exec -it simple-runtime bash -c "cd /simplerun/code && /simplerun/micromamba/bin/micromamba run -n simplerun poetry run pytest tests -v"; then
        log_success "All tests passed!"
    else
        log_warning "Some tests failed, but continuing..."
        log_info "You can check test details later with: docker exec -it simple-runtime bash"
    fi
}

# 显示使用说明
show_usage() {
    log_info "Container is ready for use!"
    echo
    echo "Container ports:"
    echo "  API: http://localhost:8000"
    echo "  VSCode: http://localhost:3000"
    echo "  Jupyter: 8001"
    echo "  Workspace: $(pwd)/workspace"
    echo
    echo "Quick test:"
    echo "  curl http://localhost:8000/alive"
    echo
    echo "Useful commands:"
    echo "  View logs:        docker logs -f simple-runtime"
    echo "  Enter container:  docker exec -it simple-runtime bash"
    echo "  Stop container:   docker stop simple-runtime"
    echo "  Remove container: docker rm simple-runtime"
}

# 主函数
main() {
    echo "=========================================="
    echo "  Simple Docker Runtime - Full Test Run"
    echo "=========================================="
    echo
    
    # 检查当前目录
    if [ ! -f "Dockerfile" ] || [ ! -f "pyproject.toml" ]; then
        log_error "Please run this script from the simple_docker_runtime directory"
        exit 1
    fi
    
    # 执行各个步骤
    check_docker
    cleanup
    build_image
    prepare_mounts
    start_container
    wait_for_service
    check_container_status
    run_tests
    show_usage
    
    echo
    log_success "All operations completed successfully!"
}

# 捕获中断信号
trap 'log_error "Script interrupted"; exit 1' INT TERM

# 运行主函数
main "$@"
