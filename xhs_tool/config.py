"""
config.py - 小红书封面卡片生成工具配置

API key 配置方式（任选其一）：
  1) 推荐：复制 config_local.py.example 为 config_local.py 并填入你的 key
     （config_local.py 已在 .gitignore 中，不会被提交到仓库）
  2) 环境变量：GEMINI_API_KEY、GEMINI_API_KEY_2
"""

import os

# ============================================================
# Gemini API key（双邮箱免费配额轮换）
# 获取地址：https://aistudio.google.com/apikey
# ============================================================

# 优先从 config_local.py 读取（本地、不入 git）
try:
    from config_local import GEMINI_API_KEYS  # type: ignore
except ImportError:
    # 回退到环境变量
    _env_keys = [
        os.environ.get("GEMINI_API_KEY"),
        os.environ.get("GEMINI_API_KEY_2"),
    ]
    GEMINI_API_KEYS = [k for k in _env_keys if k]

# 文案生成用的 Gemini 模型
TEXT_MODEL = "gemini-2.5-flash"


# ============================================================
# 封面图生成 —— 多 provider 自动回退（旧版兼容字段）
# ------------------------------------------------------------
# 当前版本主要使用 Playwright 本地渲染 HTML 模板生成封面卡片，
# 不再依赖付费图像 API。下面的字段保留是为了兼容老的 web_app.py
# 调用路径，未来会清理。
# ============================================================

# --- Gemini 官方图像模型（需绑卡升级到 Tier 1）---
GEMINI_IMAGE_MODEL = "gemini-2.5-flash-image"
USE_GEMINI_IMAGE = os.environ.get("USE_GEMINI_IMAGE", "auto")  # auto/yes/no

# --- OpenAI gpt-image-1 / gpt-image-2（需付费）---
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_IMAGE_MODEL = "gpt-image-1"

# --- SiliconFlow 硅基流动（国内推荐）---
SILICONFLOW_API_KEY = os.environ.get("SILICONFLOW_API_KEY", "")
SILICONFLOW_MODELS = [
    "Kwai-Kolors/Kolors",
    "black-forest-labs/FLUX.1-schnell",
    "stabilityai/stable-diffusion-3-5-large",
    "black-forest-labs/FLUX.1-dev",
    "stabilityai/stable-diffusion-xl-base-1.0",
]

# --- Pollinations（完全免费兜底，无需 key）---
POLLINATIONS_MODEL = "gptimage-large"


# ============================================================
# 输出配置
# ============================================================

NUM_NOTES = 3

# 封面卡片尺寸（小红书推荐 3:4 竖版）
IMAGE_WIDTH = 1080
IMAGE_HEIGHT = 1440

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
INPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "input")
