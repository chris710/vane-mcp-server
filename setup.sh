#!/bin/bash
set -e

echo "========================================="
echo "  Vane MCP Server — Installation"
echo "========================================="
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3.11+"
    exit 1
fi

PY_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "✅ Python $PY_VERSION"

# Install UV if not present
if ! command -v uv &> /dev/null; then
    echo "📦 Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
fi

echo ""
echo "📦 Installing dependencies..."

# Install the package
uv pip install -e . 2>/dev/null || pip install -e .

echo ""
echo "========================================="
echo "✅ Installation complete!"
echo ""
echo "Starting the MCP server:"
echo "  uv run vane-mcp              # stdio mode"
echo "  uv run vane-mcp --sse        # SSE mode"
echo ""
echo "Before running, make sure that:"
echo "  1. Vane is running on localhost:3000"
echo "  2. SearxNG is running on localhost:8080"
echo "  3. Environment variables are configured (see README)"
echo ""
echo "Connecting to Claude Desktop:"
echo "  Add config/claude_desktop.json to ~/Library/Application Support/Claude/claude_desktop_config.json"
echo "========================================="
