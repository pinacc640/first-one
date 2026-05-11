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
    NUM_NOTES,
    GEMINI_IMAGE_MODEL,
    USE_GEMINI_IMAGE,
    OPENAI_API_KEY,
    OPENAI_IMAGE_MODEL,
    SILICONFLOW_API_KEY,
    SILICONFLOW_MODELS,
    POLLINATIONS_MODEL,
    IMAGE_WIDTH,
    IMAGE_HEIGHT,
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
    """
    按优先级尝试生成封面图，返回 (img_bytes, mime, provider_label)。
    """
    prompt_text = build_cover_prompt(product_title, note_title)

    # 优先级 1：Gemini 官方
    if USE_GEMINI_IMAGE in ("auto", "yes") and GEMINI_API_KEY:
        img, mime, err = _try_gemini_image(client, prompt_text)
        if img:
            return img, mime, "Gemini 2.5 Flash Image"
        if err and "quota" not in err.lower() and "exhausted" not in err.lower():
            st.caption(f"Gemini 不可用: {err[:120]}")

    # 优先级 2：OpenAI
    if OPENAI_API_KEY:
        img, mime, err = _try_openai_image(prompt_text)
        if img:
            return img, mime, f"OpenAI {OPENAI_IMAGE_MODEL}"
        if err:
            st.caption(f"OpenAI 不可用: {err[:120]}")

    # 优先级 3：SiliconFlow 依次尝试多个模型
    if SILICONFLOW_API_KEY:
        for model_id in SILICONFLOW_MODELS:
            img, mime, err = _try_siliconflow_image(prompt_text, model_id)
            if img:
                return img, mime, f"SiliconFlow {model_id.split('/')[-1]}"
            if err:
                # 若是 Model disabled / 付费拒绝，继续下一个；其他错直接退出
                low = err.lower()
                if "disabled" in low or "forbid" in low or "403" in low or "402" in low:
                    st.caption(f"SiliconFlow [{model_id}] 不可用，尝试下一个...")
                    continue
                st.caption(f"SiliconFlow [{model_id}] 异常: {err[:120]}")
                break

    # 优先级 4：Pollinations 免费兜底
    img, mime, err = _try_pollinations_image(prompt_text)
    if img:
        return img, mime, f"Pollinations {POLLINATIONS_MODEL}"
    st.warning(f"所有图像服务均失败。最后错误: {err}")
    return None, None, None


def build_cover_prompt(product_title, note_title):
    """构建封面图提示词（英文效果更好）"""
    return (
        f"Premium Xiaohongshu (Little Red Book) social media cover photo. "
        f"Product: {product_title}. Theme: {note_title}. "
        f"Style: clean minimal lifestyle product photography, warm natural lighting, "
        f"soft pastel background, high-end aesthetic, shallow depth of field, "
        f"Instagram-quality, vertical 3:4 composition, editorial look, no text overlay."
    )


def _try_gemini_image(client, prompt_text):
    """调用 Gemini 原生图像生成"""
    try:
        response = client.models.generate_content(
            model=GEMINI_IMAGE_MODEL,
            contents=prompt_text,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE", "TEXT"],
                image_config=types.ImageConfig(aspect_ratio="3:4"),
            ),
        )
        candidate = response.candidates[0]
        if candidate.finish_reason not in (
            types.FinishReason.STOP,
            types.FinishReason.MAX_TOKENS,
        ):
            return None, None, f"被模型拒绝: {candidate.finish_reason.name}"
        for part in candidate.content.parts:
            if part.inline_data and part.inline_data.mime_type.startswith("image/"):
                return part.inline_data.data, part.inline_data.mime_type, None
        return None, None, "响应中无图片数据"
    except Exception as e:
        return None, None, str(e)


def _try_openai_image(prompt_text):
    """调用 OpenAI gpt-image 生成"""
    import urllib.request
    import urllib.error

    body = json.dumps({
        "model": OPENAI_IMAGE_MODEL,
        "prompt": prompt_text,
        "size": "1024x1536",  # 3:2 近似 3:4
        "n": 1,
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.openai.com/v1/images/generations",
        data=body,
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        img_item = data["data"][0]
        if "b64_json" in img_item:
            return base64.b64decode(img_item["b64_json"]), "image/png", None
        if "url" in img_item:
            with urllib.request.urlopen(img_item["url"], timeout=30) as r2:
                return r2.read(), "image/png", None
        return None, None, "响应格式异常"
    except urllib.error.HTTPError as e:
        return None, None, f"HTTP {e.code}: {e.read().decode('utf-8', errors='ignore')[:200]}"
    except Exception as e:
        return None, None, str(e)


def _try_siliconflow_image(prompt_text, model_id):
    """调用 SiliconFlow 指定模型生成图像"""
    import urllib.request
    import urllib.error

    body = json.dumps({
        "model": model_id,
        "prompt": prompt_text,
        "image_size": f"{IMAGE_WIDTH}x{IMAGE_HEIGHT}",
        "num_inference_steps": 20,
        "guidance_scale": 7.5,
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.siliconflow.cn/v1/images/generations",
        data=body,
        headers={
            "Authorization": f"Bearer {SILICONFLOW_API_KEY}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        img_url = data["images"][0]["url"]
        with urllib.request.urlopen(img_url, timeout=30) as r2:
            return r2.read(), "image/png", None
    except urllib.error.HTTPError as e:
        return None, None, f"HTTP {e.code}: {e.read().decode('utf-8', errors='ignore')[:200]}"
    except Exception as e:
        return None, None, str(e)


def _try_pollinations_image(prompt_text):
    """Pollinations 免费兜底（无需 key）"""
    import urllib.parse
    import urllib.request

    encoded = urllib.parse.quote(prompt_text)
    url = (
        f"https://image.pollinations.ai/prompt/{encoded}"
        f"?model={POLLINATIONS_MODEL}&width={IMAGE_WIDTH}&height={IMAGE_HEIGHT}"
        f"&enhance=true&nologo=true"
    )
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=120) as resp:
            img_bytes = resp.read()
        if len(img_bytes) < 1000:
            return None, None, "返回数据过小"
        return img_bytes, "image/jpeg", None
    except Exception as e:
        return None, None, str(e)


def generate_cover_with_imagen(client, product_title, note_title):
    """占位，已不使用（逻辑并入 generate_cover_image 的回退链）"""
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
        st.markdown("**🎨 封面图服务状态**")
        if GEMINI_API_KEY and USE_GEMINI_IMAGE in ("auto", "yes"):
            st.markdown("- ✅ Gemini（优先，需付费）")
        else:
            st.markdown("- ⚪ Gemini（未启用）")
        if OPENAI_API_KEY:
            st.markdown("- ✅ OpenAI gpt-image")
        else:
            st.markdown("- ⚪ OpenAI（未配置 key）")
        if SILICONFLOW_API_KEY:
            st.markdown("- ✅ SiliconFlow（推荐，送免费额度）")
        else:
            st.markdown("- ⚪ SiliconFlow（未配置 key）")
        st.markdown("- ✅ Pollinations（免费兜底）")
        with st.expander("💡 如何获取更好效果"):
            st.markdown(
                "**推荐配置 SiliconFlow**（免费质量接近 Gemini）:\n"
                "1. 注册 [siliconflow.cn](https://cloud.siliconflow.cn/account/ak)\n"
                "2. 新账号送 ¥14 额度\n"
                "3. `export SILICONFLOW_API_KEY=sk-...`"
            )

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
            cover_images = [(None, None, None)] * len(notes)
        else:
            for i, note in enumerate(notes):
                img_data, mime_type, provider = generate_cover_image(
                    client, product_title, note["title"]
                )
                cover_images.append((img_data, mime_type, provider))
                progress = 50 + (i + 1) * 50 // len(notes)
                progress_bar.progress(progress)

                if i < len(notes) - 1:
                    time.sleep(1)

        status_text.text("🎉 生成完成!")
        progress_bar.progress(100)

        # ============ 展示结果 ============
        st.markdown("---")
        st.subheader(f"📋 生成结果：{product_title}")

        for i, (note, (img_data, mime_type, provider)) in enumerate(zip(notes, cover_images)):
            st.markdown(f"### 第 {i+1} 篇")
            # 封面图在左，文案在右
            c1, c2 = st.columns([1, 1.2])

            with c1:
                if img_data:
                    img_bytes = img_data if isinstance(img_data, bytes) else base64.b64decode(img_data)
                    img = Image.open(io.BytesIO(img_bytes))
                    caption = f"封面图 {i+1}"
                    if provider:
                        caption += f" · {provider}"
                    st.image(img, caption=caption, use_container_width=True)
                    # 下载按钮
                    ext = "png" if "png" in (mime_type or "") else "jpg"
                    st.download_button(
                        label=f"⬇️ 下载封面图 {i+1}",
                        data=img_bytes,
                        file_name=f"cover_{i+1}.{ext}",
                        mime=mime_type or "image/png",
                        use_container_width=True,
                    )
                else:
                    st.info(f"封面图 {i+1} 生成失败")

            with c2:
                # 标题 —— 可复制
                st.markdown("**📌 标题**（可直接复制）")
                st.text_area(
                    label=f"title_{i}",
                    value=note["title"],
                    height=68,
                    key=f"title_{i}",
                    label_visibility="collapsed",
                )

                # 正文 —— 可复制
                st.markdown("**📝 正文**（可直接复制）")
                st.text_area(
                    label=f"body_{i}",
                    value=note["body"],
                    height=220,
                    key=f"body_{i}",
                    label_visibility="collapsed",
                )

                # 标签 —— 可复制，空格分隔方便粘贴
                tags_str = " ".join(note["tags"])
                st.markdown("**🏷️ 标签**（可直接复制）")
                st.text_area(
                    label=f"tags_{i}",
                    value=tags_str,
                    height=100,
                    key=f"tags_{i}",
                    label_visibility="collapsed",
                )

            st.markdown("---")


if __name__ == "__main__":
    main()