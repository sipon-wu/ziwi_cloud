FROM python:3.13-slim AS builder

WORKDIR /app
# 国内构建默认走阿里云 PyPI 镜像（官方源在 CVM 上实测 12 kB/s，会卡死构建）
ARG PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/
COPY requirements.txt .
RUN pip install --no-cache-dir -i ${PIP_INDEX_URL} -r requirements.txt

COPY . .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
