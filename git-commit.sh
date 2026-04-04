#!/bin/bash
# Git 提交脚本

cd ~/ink

echo "📝 配置 Git..."
git config user.email "cheng@example.com"
git config user.name "程老师"

echo "📦 添加所有文件..."
git add .

echo "💾 提交变更..."
git commit -m "feat: 导入11篇知识库文章并生成静态网站

- 添加 AgentHub 多Agent协作平台文章
- 添加 Claude Code 15个隐藏能力文章
- 添加 agency-agents 学习笔记
- 添加 OpenClaw 优化指南
- 添加 Vibe Coding 指南
- 添加 Seedance 2.0 视频提示词
- 添加中国AI生态深度观察
- 添加 OpenCLI 浏览器自动化
- 添加镜头运动速查表
- 添加粒子日记本产品案例
- 生成静态网站 _site/index.html
- 更新博客索引 INDEX.md

总字数: ~43,000字"

echo "🚀 推送至远程仓库..."
git push origin main

echo "✅ 完成！"
