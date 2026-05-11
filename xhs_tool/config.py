"""
config.py - 小红书笔记批量制作工具配置
"""

import os

# ============================================================
# Google AI API 配置
# 从环境变量读取，或在此处直接填入你的 API Key
# 获取地址：https://aistudio.google.com/apikey
# ============================================================
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

# 文案生成模型（支持多模态输入）
TEXT_MODEL = "gemini-2.5-flash"

# 封面图生成模型（支持原生图像输出）
# gemini-2.5-flash-image = Nano Banana，免费 tier 500张/天，AI Studio key 直接可用
# 注意：gemini-3.1-flash-image-preview 免费配额为 0（需付费）
#       imagen-3.0-generate-002 只支持 Vertex AI，AI Studio key 不可用
IMAGE_MODEL = "gemini-2.5-flash-image"

# ============================================================
# 输出配置
# ============================================================

# 每次运行生成几组笔记（默认3组）
NUM_NOTES = 3

# 封面图尺寸（小红书推荐 3:4 竖版）
IMAGE_WIDTH = 1080
IMAGE_HEIGHT = 1440

# 输出目录
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
INPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "input")
