"""
config.py - 小红书笔记批量制作工具配置
"""

import os

# ============================================================
# 文案生成（Gemini，免费配额够用）
# 获取地址：https://aistudio.google.com/apikey
# ============================================================
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
TEXT_MODEL = "gemini-2.5-flash"


# ============================================================
# 封面图生成 —— 按优先级自动回退
# ------------------------------------------------------------
# 现状（2026/05）：Gemini 和 GPT-Image 都没有公开免费 tier，
# 想要高质量图必须付费或用第三方聚合平台。工具会按下面的
# 优先级依次尝试，哪个配好了 key 就用哪个，都没有就用
# Pollinations 免费兜底。
# ============================================================

# --- 优先级 1：Gemini 官方（质量最好，需要开通计费）---
# 开通方式：https://aistudio.google.com/apikey -> 升级到 Tier 1（绑卡）
# 定价：~$0.039 / 张
GEMINI_IMAGE_MODEL = "gemini-2.5-flash-image"
USE_GEMINI_IMAGE = os.environ.get("USE_GEMINI_IMAGE", "auto")  # auto/yes/no


# --- 优先级 2：OpenAI gpt-image-1 / gpt-image-2（质量顶级，需付费）---
# 获取地址：https://platform.openai.com/api-keys
# 定价：~$0.04 / 张
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_IMAGE_MODEL = "gpt-image-1"  # 或 "gpt-image-2"（如已开放）


# --- 优先级 3：SiliconFlow 硅基流动（国内推荐，注册送免费额度）---
# 获取地址：https://cloud.siliconflow.cn/account/ak
# 免费：新账号送 ¥14 额度，约可生成 700+ 张 FLUX.1 图
# 质量：FLUX.1-dev 接近 Gemini 水平
SILICONFLOW_API_KEY = os.environ.get("SILICONFLOW_API_KEY", "")
SILICONFLOW_MODEL = "black-forest-labs/FLUX.1-dev"


# --- 优先级 4：Pollinations（完全免费兜底，无需 key）---
# gptimage-large 质量不错，flux 一般
POLLINATIONS_MODEL = "gptimage-large"


# ============================================================
# 输出配置
# ============================================================

NUM_NOTES = 3

# 封面图尺寸（小红书推荐 3:4 竖版）
IMAGE_WIDTH = 1080
IMAGE_HEIGHT = 1440

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
INPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "input")
