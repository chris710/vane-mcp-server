#!/bin/bash
set -e

echo "========================================="
echo "  Vane MCP Server — установка"
echo "========================================="
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 не найден. Установи Python 3.11+"
    exit 1
fi

PY_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "✅ Python $PY_VERSION"

# Install UV if not present
if ! command -v uv &> /dev/null; then
    echo "📦 Устанавливаю uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
fi

echo ""
echo "📦 Устанавливаю зависимости..."

# Install the package
uv pip install -e . 2>/dev/null || pip install -e .

echo ""
echo "========================================="
echo "✅ Установка завершена!"
echo ""
echo "Запуск MCP сервера:"
echo "  uv run vane-mcp              # stdio режим"
echo "  uv run vane-mcp --sse        # SSE режим"
echo ""
echo "Перед запуском убедись что:"
echo "  1. Vane запущен на localhost:3000"
echo "  2. SearxNG запущен на localhost:8080"
echo "  3. Переменные окружения настроены (см. README)"
echo ""
echo "Подключение к Claude Desktop:"
echo "  Добавь config/claude_desktop.json в ~/Library/Application Support/Claude/claude_desktop_config.json"
echo "========================================="
