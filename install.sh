#!/bin/bash
# Ink CLI 安装脚本

set -e

INK_HOME="$HOME/ink"
INSTALL_DIR="${INSTALL_DIR:-$HOME/.local/bin}"

echo "🌊 Liquid Blog 安装脚本"
echo "======================="

# 检查依赖
echo "📦 检查依赖..."

if ! command -v python3 &> /dev/null; then
    echo "❌ 需要 Python 3，请先安装"
    exit 1
fi

if ! command -v pip3 &> /dev/null; then
    echo "❌ 需要 pip3，请先安装"
    exit 1
fi

# 安装 Python 依赖
echo "📦 安装 Python 依赖..."
pip3 install --user pyyaml markdown 2>/dev/null || pip3 install pyyaml markdown

# 创建目录结构
echo "📁 创建目录结构..."
mkdir -p "$INK_HOME"
mkdir -p "$INK_HOME/.ink/skills"
mkdir -p "$INK_HOME/.ink/workflows"
mkdir -p "$INK_HOME/.ink/sessions"
mkdir -p "$INK_HOME/_index"
mkdir -p "$INK_HOME/_templates/default"

# 复制文件
echo "📄 复制核心文件..."

# 复制 CLI 脚本（假设在相同目录）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -f "$SCRIPT_DIR/ink" ]; then
    cp "$SCRIPT_DIR/ink" "$INK_HOME/ink"
    chmod +x "$INK_HOME/ink"
fi

# 复制 Skills
if [ -d "$SCRIPT_DIR/.ink/skills" ]; then
    cp "$SCRIPT_DIR/.ink/skills/"*.md "$INK_HOME/.ink/skills/"
fi

# 复制 Workflows
if [ -d "$SCRIPT_DIR/.ink/workflows" ]; then
    cp "$SCRIPT_DIR/.ink/workflows/"*.md "$INK_HOME/.ink/workflows/"
fi

# 复制模板
if [ -d "$SCRIPT_DIR/_templates" ]; then
    cp -r "$SCRIPT_DIR/_templates/"* "$INK_HOME/_templates/"
fi

# 创建默认配置
if [ ! -f "$INK_HOME/.ink/config.yaml" ]; then
    cat > "$INK_HOME/.ink/config.yaml" << 'EOF'
site:
  title: "My Liquid Blog"
  description: "A blog powered by Skills + Markdown"
  author: "Anonymous"

channels:
  blog:
    type: static
    output: "./_site"

search:
  engine: "hybrid"
  top_k: 10
EOF
fi

# 创建软链接
if [ -d "$INSTALL_DIR" ]; then
    echo "🔗 创建命令链接..."
    ln -sf "$INK_HOME/ink" "$INSTALL_DIR/ink"
    echo "   ink 命令已链接到 $INSTALL_DIR/ink"
else
    echo "⚠️  $INSTALL_DIR 不存在，请手动将 $INK_HOME/ink 添加到 PATH"
fi

# 添加到 PATH（如果需要）
if ! command -v ink &> /dev/null; then
    SHELL_RC=""
    if [[ "$SHELL" == *"bash"* ]]; then
        SHELL_RC="$HOME/.bashrc"
    elif [[ "$SHELL" == *"zsh"* ]]; then
        SHELL_RC="$HOME/.zshrc"
    fi
    
    if [ -n "$SHELL_RC" ] && [ -f "$SHELL_RC" ]; then
        echo "" >> "$SHELL_RC"
        echo "# Ink CLI" >> "$SHELL_RC"
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$SHELL_RC"
        echo "✅ 已更新 $SHELL_RC，请运行 'source $SHELL_RC' 或重新打开终端"
    fi
fi

echo ""
echo "✅ 安装完成！"
echo ""
echo "快速开始:"
echo "  ink init        # 初始化环境"
echo "  ink new 'Hello' # 创建第一篇文章"
echo "  ink list        # 查看所有文章"
echo "  ink --help      # 查看帮助"
echo ""
echo "配置文件: $INK_HOME/.ink/config.yaml"
