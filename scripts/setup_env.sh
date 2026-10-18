#!/usr/bin/env bash
# 创建 conda 环境 pyy 并安装依赖
set -euo pipefail
cd "$(dirname "$0")/.."

if ! command -v conda >/dev/null 2>&1; then
  echo "[错误] 没找到 conda，请先安装 Miniconda 并初始化 shell"
  exit 1
fi

if conda env list | awk '{print $1}' | grep -qx "pyy"; then
  echo "[1/2] 环境 pyy 已存在，跳过创建"
else
  echo "[1/2] 创建环境 pyy ..."
  conda create -n pyy python=3.11 -y
fi

echo "[2/2] 安装依赖 ..."
conda run -n pyy python -m pip install -r requirements.txt
echo
echo "完成。启动：conda run -n pyy python run.py"
