FROM python:3.12-slim

#Install uv
COPY --from=ghcr.io/astral-sh/uv /uv /uvx /bin/

#設定容器內的工作目錄（程式碼要放哪裡）
WORKDIR /app

COPY pyproject.toml uv.lock ./

# 3. 凍結鎖定檔並安裝依賴（排除專案本身的程式碼）
RUN uv sync --frozen --no-install-project --no-dev

COPY . .

CMD ["uv", "run", "uvicorn", "src.main", "--host", "0.0.0.0", "--port", "8000"]