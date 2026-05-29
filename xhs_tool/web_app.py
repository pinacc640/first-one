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
import tempfile
import time
from pathlib import Path

import streamlit as st
from google import genai
from google.genai import types
from PIL import Image

# 添加当前目录到路径，以便导入 config 和 prompts
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import (
    GEMINI_API_KEYS,
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
)
from card_generator import generate_cover, generate_magazine_cover, generate_detail_pages
from stock_photos import fetch_stock_image


# ============ 页面配置 ============
st.set_page_config(
    page_title="小红书笔记 · Guizang 杂志封面",
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
# ============ API Key 轮换 ============
_key_index = 0

def get_client():
    """创建 Gemini API 客户端（多 key 轮换）"""
    global _key_index
    if not GEMINI_API_KEYS or not GEMINI_API_KEYS[0]:
        st.error("❌ 请在 config.py 中配置 GEMINI_API_KEYS，或设置环境变量 GEMINI_API_KEY")
        return None
    key = GEMINI_API_KEYS[_key_index % len(GEMINI_API_KEYS)]
    _key_index += 1
    return genai.Client(api_key=key)


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
    """使用 Gemini 生成小红书文案（含自动重试）"""
    user_prompt = COPYWRITING_USER_PROMPT.format(
        num_notes=NUM_NOTES,
        product_title=product_title,
    )

    contents = [user_prompt]
    for uploaded_file in uploaded_files:
        uploaded_file.seek(0)  # 确保从文件开头读取
        contents.append(uploaded_file_to_part(uploaded_file))

    import time
    max_retries = 5
    last_error = None
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=TEXT_MODEL,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=COPYWRITING_SYSTEM_PROMPT,
                    temperature=0.8,
                ),
            )
            raw_text = response.text.strip()
            break
        except Exception as e:
            last_error = e
            err_str = str(e)
            if "503" in err_str or "UNAVAILABLE" in err_str or "429" in err_str:
                wait = 2 ** attempt * 2
                print(f"API 繁忙，第 {attempt+1} 次重试，等待 {wait} 秒...")
                time.sleep(wait)
                continue
            raise  # 非限流错误直接抛

    else:
        raise Exception(f"API 服务不可用，已重试 {max_retries} 次: {last_error}")

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
    st.title("📕 小红书笔记生成 · Guizang 杂志封面")
    st.markdown("上传产品截图，自动生成种草文案 + **杂志级封面卡片**")

    # 侧边栏配置
    with st.sidebar:
        st.header("⚙️ 配置")
        st.markdown("---")
        num_notes = st.slider("生成数量", 1, 5, 3)
        skip_cover = st.checkbox("跳过封面图生成", value=False)

        st.markdown("---")
        st.markdown("**🎨 输出内容（每篇笔记）**")
        st.markdown("- 🟦 **1 张 Swiss 杂志封面**")
        st.markdown("  - 2~4 张截图网格排版，各配不同背景纹理")
        st.markdown("  - 可选 Pexels 图库背景图")
        st.markdown("- 📄 **5 张详情页图片**（布局轮换）")
        st.markdown("- 大字标题 + 满版构图")

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
        status_text.text("🎨 正在生成杂志风封面图...")

        # Step 2: 保存截图到临时目录
        tmp_dir = Path(tempfile.mkdtemp())
        saved_images = []
        for uf in uploaded_files:
            uf.seek(0)
            ext = Path(uf.name).suffix or ".png"
            dest = tmp_dir / f"screenshot_{len(saved_images)}{ext}"
            dest.write_bytes(uf.read())
            saved_images.append(str(dest))

        # Step 3: 用 card_generator 生成图片
        # 每篇笔记: 1 张杂志封面 + 3 张详情页
        all_results = []  # [(note_idx, type, img_data, mime, label), ...]

        if skip_cover:
            pass  # no images
        else:
            output_dir = Path(__file__).parent / "output"
            output_dir.mkdir(exist_ok=True)

            total = len(notes) * 6  # 1 cover + 5 detail per note
            done = 0

            for i, note in enumerate(notes):
                note_dir = output_dir / f"note_{i+1}"
                note_dir.mkdir(exist_ok=True)

                # --- 1. 杂志封面（多截图 + 可选 stock photo 背景）---
                subtitle = note.get("body", "")[:30].strip()
                if len(subtitle) == 30:
                    subtitle = subtitle.rstrip("，。；") + "..."

                status_text.text(f"🎨 正在生成笔记 {i+1} 的杂志封面...")

                # 取 stock photo 作为封面背景（异步兜底，失败不影响主流程）
                stock_b64 = None
                try:
                    stock_b64 = fetch_stock_image(product_title, timeout=10)
                except Exception:
                    pass

                cover_path = str(note_dir / "cover.png")
                # 给 3 篇笔记分配视觉差异最大的 3 种 layout：
                #   A = 深色 Swiss Grid + 设备框        （高密度文字 + 截图网格）
                #   E = Product Grid 多截图网格         （4 张截图拼版，最丰富）
                #   B = 全屏大图 + 浮层标题             （单图大胆视觉冲击）
                # 避开 C（衬线大留白）和 D（深色电影感，视觉与 A 接近）以最大化差异。
                cover_layouts = ["A", "E", "B"]
                cover_result = generate_magazine_cover(
                    note_title=note["title"],
                    product_title=product_title,
                    image_paths=saved_images,  # 传全部截图，模板自动布局
                    output_path=cover_path,
                    tags=note.get("tags", [])[:6],
                    subtitle=subtitle,
                    vol=i + 1,
                    stock_b64=stock_b64,
                    cover_layout=cover_layouts[i % len(cover_layouts)],
                )

                if cover_result:
                    img_bytes = Path(cover_path).read_bytes()
                    all_results.append((i, "cover", img_bytes, "image/png", "Guizang Swiss Cover"))
                else:
                    all_results.append((i, "cover", None, None, None))

                done += 1
                progress = 50 + done * 50 // total
                progress_bar.progress(progress)

                # --- 2. 五张详情页 ---
                status_text.text(f"📄 正在生成笔记 {i+1} 的详情页（5张）...")

                detail_results = generate_detail_pages(
                    note_title=note["title"],
                    product_title=product_title,
                    image_paths=saved_images,
                    output_dir=str(note_dir),
                    tags=note.get("tags", [])[:6],
                    prefix="detail",
                    count=5,
                )

                for detail_path, layout in detail_results:
                    if detail_path:
                        img_bytes = Path(detail_path).read_bytes()
                        all_results.append((i, "detail", img_bytes, "image/png", f"Detail {layout}"))
                    else:
                        all_results.append((i, "detail", None, None, None))
                    done += 1
                    progress = 50 + done * 50 // total
                    progress_bar.progress(progress)

        # 清理临时目录
        import shutil
        shutil.rmtree(tmp_dir, ignore_errors=True)

        status_text.text("🎉 生成完成!")
        progress_bar.progress(100)

        # ============ 展示结果 ============
        st.markdown("---")
        st.subheader(f"📋 生成结果：{product_title}")

        for i, note in enumerate(notes):
            st.markdown(f"### 第 {i+1} 篇")
            note_results = [r for r in all_results if r[0] == i]

            # 封面图 + 文案在同一行
            c1, c2 = st.columns([1, 1.2])

            cover_data = next((r for r in note_results if r[1] == "cover"), None)
            with c1:
                if cover_data and cover_data[2]:
                    cover_bytes = cover_data[2] if isinstance(cover_data[2], bytes) else base64.b64decode(cover_data[2])
                    img = Image.open(io.BytesIO(cover_bytes))
                    st.image(img, caption=f"杂志封面 {i+1} · {cover_data[4]}", use_container_width=True)
                    st.download_button(
                        label=f"⬇️ 下载封面 {i+1}",
                        data=cover_bytes,
                        file_name=f"cover_{i+1}.png",
                        mime="image/png",
                        use_container_width=True,
                    )
                else:
                    st.info(f"杂志封面 {i+1} 生成失败")

            with c2:
                st.markdown("**📌 标题**（可直接复制）")
                st.text_area(
                    label=f"title_{i}",
                    value=note["title"],
                    height=68,
                    key=f"title_{i}",
                    label_visibility="collapsed",
                )
                st.markdown("**📝 正文**（可直接复制）")
                st.text_area(
                    label=f"body_{i}",
                    value=note["body"],
                    height=180,
                    key=f"body_{i}",
                    label_visibility="collapsed",
                )
                tags_str = " ".join(note["tags"])
                st.markdown("**🏷️ 标签**（可直接复制）")
                st.text_area(
                    label=f"tags_{i}",
                    value=tags_str,
                    height=60,
                    key=f"tags_{i}",
                    label_visibility="collapsed",
                )

            # 5 张详情页预览
            detail_results = [r for r in note_results if r[1] == "detail"]
            if detail_results and any(r[2] for r in detail_results):
                st.markdown("**📄 详情页图片（5张）**")
                cols = st.columns(min(5, len(detail_results)))
                for j, (col, dr) in enumerate(zip(cols, detail_results)):
                    with col:
                        if dr[2]:
                            det_bytes = dr[2] if isinstance(dr[2], bytes) else base64.b64decode(dr[2])
                            det_img = Image.open(io.BytesIO(det_bytes))
                            st.image(det_img, caption=f"详情 {j+1} · {dr[4]}", use_container_width=True)
                            st.download_button(
                                label=f"⬇️ 下载 {j+1}",
                                data=det_bytes,
                                file_name=f"detail_{i+1}_{j+1}.png",
                                mime="image/png",
                                use_container_width=True,
                            )
                        else:
                            st.info(f"详情 {j+1} 失败")

            st.markdown("---")


if __name__ == "__main__":
    main()