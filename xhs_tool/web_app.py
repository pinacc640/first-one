#!/usr/bin/env python3
"""
web_app.py - 小红书笔记批量制作工具 Web UI

使用方法：
    1. 将3张产品截图放入 input/ 目录
    2. 运行：streamlit run web_app.py
"""

import base64
import io
import json
import os
import sys
import time
from pathlib import Path

import streamlit as st
from google import genai
from google.genai import types
from PIL import Image

# 添加当前目录到路径，以便导入 config 和 prompts
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import (
    GEMINI_API_KEY,
    TEXT_MODEL,
    IMAGE_MODEL,
    NUM_NOTES,
)
from prompts import (
    COPYWRITING_SYSTEM_PROMPT,
    COPYWRITING_USER_PROMPT,
    COVER_IMAGE_PROMPT,
)


# ============ 页面配置 ============
st.set_page_config(
    page_title="小红书笔记批量生成工具",
    page_icon="📕",
    layout="wide",
)


# ============ 样式 ============
st.markdown("""
<style>
    .stButton > button {
        width: 100%;
        background: linear-gradient(90deg, #FF2442 0%, #FF6B6B 100%);
        color: white;
        font-size: 18px;
        font-weight: bold;
        padding: 15px;
        border: none;
        border-radius: 10px;
    }
    .stButton > button:hover {
        background: linear-gradient(90deg, #E61E32 0%, #FF5252 100%);
    }
    .note-card {
        background: #fff;
        border-radius: 16px;
        padding: 24px;
        margin: 16px 0;
        box-shadow: 0 4px 20px rgba(0,0,0,0.08);
    }
    .note-title {
        font-size: 20px;
        font-weight: bold;
        color: #333;
        margin-bottom: 16px;
    }
    .note-body {
        font-size: 15px;
        color: #555;
        line-height: 1.8;
        white-space: pre-wrap;
    }
    .note-tags {
        margin-top: 16px;
        padding-top: 16px;
        border-top: 1px solid #eee;
    }
    .tag {
        display: inline-block;
        background: #FFF0F0;
        color: #FF2442;
        padding: 4px 12px;
        border-radius: 20px;
        margin: 4px;
        font-size: 13px;
    }
    .cover-placeholder {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        border-radius: 12px;
        display: flex;
        align-items: center;
        justify-content: center;
        height: 400px;
        color: #999;
    }
</style>
""", unsafe_allow_html=True)


# ============ 辅助函数 ============
def get_client():
    """创建 Gemini API 客户端"""
    if not GEMINI_API_KEY:
        st.error("❌ 请在 config.py 中配置 GEMINI_API_KEY，或设置环境变量")
        return None
    return genai.Client(api_key=GEMINI_API_KEY)


def uploaded_file_to_part(uploaded_file):
    """将 Streamlit 上传的文件转换为 API 可用的 Part 对象"""
    mime_map = {
        "image/png": "image/png",
        "image/jpeg": "image/jpeg",
        "image/jpg": "image/jpeg",
        "image/webp": "image/webp",
        "image/gif": "image/gif",
    }
    mime_type = mime_map.get(uploaded_file.type, "image/jpeg")
    return types.Part.from_bytes(data=uploaded_file.read(), mime_type=mime_type)


def generate_copywriting(client, product_title, uploaded_files):
    """使用 Gemini 生成小红书文案"""
    user_prompt = COPYWRITING_USER_PROMPT.format(
        num_notes=NUM_NOTES,
        product_title=product_title,
    )

    contents = [user_prompt]
    for uploaded_file in uploaded_files:
        uploaded_file.seek(0)  # 确保从文件开头读取
        contents.append(uploaded_file_to_part(uploaded_file))

    response = client.models.generate_content(
        model=TEXT_MODEL,
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=COPYWRITING_SYSTEM_PROMPT,
            temperature=0.8,
        ),
    )

    raw_text = response.text.strip()

    # 尝试提取 JSON 块
    if "```json" in raw_text:
        raw_text = raw_text.split("```json")[1].split("```")[0].strip()
    elif "```" in raw_text:
        raw_text = raw_text.split("```")[1].split("```")[0].strip()

    notes = json.loads(raw_text)
    return notes


def generate_cover_image(client, product_title, note_title):
    """使用 Gemini 生成封面图"""
    prompt = COVER_IMAGE_PROMPT.format(
        product_title=product_title,
        note_title=note_title,
    )

    try:
        response = client.models.generate_content(
            model=IMAGE_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE", "TEXT"],
            ),
        )

        for part in response.candidates[0].content.parts:
            if part.inline_data and part.inline_data.mime_type.startswith("image/"):
                return part.inline_data.data, part.inline_data.mime_type

        return None, None
    except Exception as e:
        st.warning(f"封面图生成失败: {e}")
        return None, None


def generate_cover_with_imagen(client, product_title, note_title):
    """备用方案：使用 Imagen 模型生成封面图"""
    prompt = (
        f"Product photo for social media post. "
        f"Product: {product_title}. "
        f"Style: clean, minimal, lifestyle photography, warm tones, "
        f"vertical composition 3:4 ratio. "
        f"Title text overlay: {note_title}"
    )

    try:
        response = client.models.generate_images(
            model="imagen-3.0-generate-002",
            prompt=prompt,
            config=types.GenerateImagesConfig(
                number_of_images=1,
                aspect_ratio="3:4",
            ),
        )

        if response.generated_images:
            img = response.generated_images[0]
            return img.image.image_bytes, "image/png"
    except Exception as e:
        st.warning(f"Imagen 备用方案失败: {e}")

    return None, None


# ============ 主界面 ============
def main():
    # 标题
    st.title("📕 小红书笔记批量生成工具")
    st.markdown("上传产品截图，自动生成精美的种草文案和封面图")

    # 侧边栏配置
    with st.sidebar:
        st.header("⚙️ 配置")
        st.markdown("---")
        num_notes = st.slider("生成数量", 1, 5, 3)
        skip_cover = st.checkbox("跳过封面图生成", value=False)

        st.markdown("---")
        st.markdown("**使用说明：**")
        st.markdown("1. 上传产品截图（至少1张）")
        st.markdown("2. 填写产品标题")
        st.markdown("3. 点击开始生成按钮")

    # 主输入区域
    st.subheader("📤 上传产品截图")
    uploaded_files = st.file_uploader(
        "支持 PNG、JPG、JPEG、WebP、GIF",
        type=["png", "jpg", "jpeg", "webp", "gif"],
        accept_multiple_files=True,
        label_visibility="collapsed"
    )

    # 预览上传的图片
    if uploaded_files:
        st.success(f"✅ 已选择 {len(uploaded_files)} 张图片")
        cols = st.columns(min(len(uploaded_files), 3))
        for i, f in enumerate(uploaded_files[:3]):
            with cols[i % 3]:
                st.image(f, caption=f.name, use_container_width=True)
        if len(uploaded_files) > 3:
            st.info(f"还有 {len(uploaded_files) - 3} 张图片...")

    st.subheader("📦 产品标题")
    col1, col2 = st.columns([3, 1])
    with col1:
        product_title = st.text_input(
            "输入产品名称",
            placeholder="例如：Sony WH-1000XM5 降噪耳机",
            label_visibility="collapsed"
        )
    with col2:
        generate_btn = st.button("🚀 开始生成")

    # 生成逻辑
    if generate_btn:
        if not product_title:
            st.error("请输入产品标题")
            return

        if not uploaded_files:
            st.error("请先上传产品截图")
            return

        # 创建客户端
        client = get_client()
        if not client:
            return

        # 进度显示
        progress_bar = st.progress(0)
        status_text = st.empty()

        # Step 1: 生成文案
        status_text.text("✍️ 正在生成文案...")
        progress_bar.progress(20)

        try:
            notes = generate_copywriting(client, product_title, uploaded_files)
            notes = notes[:num_notes]
        except Exception as e:
            st.error(f"文案生成失败: {e}")
            return

        progress_bar.progress(50)
        status_text.text("🎨 正在生成封面图...")

        # Step 2: 生成封面图
        cover_images = []

        if skip_cover:
            cover_images = [(None, None)] * len(notes)
        else:
            for i, note in enumerate(notes):
                # 先尝试 Gemini
                img_data, mime_type = generate_cover_image(
                    client, product_title, note["title"]
                )
                # 如果失败，尝试 Imagen
                if img_data is None:
                    img_data, mime_type = generate_cover_with_imagen(
                        client, product_title, note["title"]
                    )

                cover_images.append((img_data, mime_type))
                progress = 50 + (i + 1) * 50 // len(notes)
                progress_bar.progress(progress)

                if i < len(notes) - 1:
                    time.sleep(1)

        status_text.text("🎉 生成完成!")
        progress_bar.progress(100)

        # ============ 展示结果 ============
        st.markdown("---")
        st.subheader(f"📋 生成结果：{product_title}")

        for i, (note, (img_data, mime_type)) in enumerate(zip(notes, cover_images)):
            # 封面图在左，文案在右
            c1, c2 = st.columns([1, 1.2])

            with c1:
                if img_data:
                    img = Image.open(io.BytesIO(img_data))
                    st.image(img, caption=f"封面图 {i+1}", use_container_width=True)
                else:
                    st.markdown(f"""
                    <div class="cover-placeholder">
                        <span>封面图 {i+1}<br>(生成失败)</span>
                    </div>
                    """, unsafe_allow_html=True)

            with c2:
                st.markdown(f"""
                <div class="note-card">
                    <div class="note-title">📌 {note['title']}</div>
                    <div class="note-body">{note['body']}</div>
                    <div class="note-tags">
                        {" ".join([f'<span class="tag">{tag}</span>' for tag in note['tags']])}
                    </div>
                </div>
                """, unsafe_allow_html=True)

            st.markdown("---")


if __name__ == "__main__":
    main()