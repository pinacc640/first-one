#!/usr/bin/env python3
"""
main.py - 小红书笔记批量制作工具

使用方法：
    1. 将3张产品截图放入 input/ 目录
    2. 设置环境变量 GEMINI_API_KEY 或在 config.py 中填入
    3. 运行：python main.py --title "产品名称"

输出：
    - output/ 目录下生成3张封面图 + 3份文案文件
"""

import argparse
import base64
import json
import os
import sys
import time
from pathlib import Path

from google import genai
from google.genai import types

from config import (
    GEMINI_API_KEY,
    TEXT_MODEL,
    IMAGE_MODEL,
    NUM_NOTES,
    OUTPUT_DIR,
    INPUT_DIR,
)
from prompts import (
    COPYWRITING_SYSTEM_PROMPT,
    COPYWRITING_USER_PROMPT,
    COVER_IMAGE_PROMPT,
)


def get_client():
    """创建 Gemini API 客户端"""
    if not GEMINI_API_KEY:
        print("❌ 错误：请设置 GEMINI_API_KEY 环境变量或在 config.py 中配置")
        print("   获取地址：https://aistudio.google.com/apikey")
        sys.exit(1)
    return genai.Client(api_key=GEMINI_API_KEY)


def load_images(input_dir):
    """加载 input 目录中的图片文件"""
    supported_ext = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
    images = []

    input_path = Path(input_dir)
    if not input_path.exists():
        print(f"❌ 错误：输入目录不存在 -> {input_dir}")
        sys.exit(1)

    for f in sorted(input_path.iterdir()):
        if f.suffix.lower() in supported_ext:
            images.append(f)

    if not images:
        print(f"❌ 错误：输入目录中没有找到图片文件 -> {input_dir}")
        print(f"   支持格式：{', '.join(supported_ext)}")
        sys.exit(1)

    print(f"📷 找到 {len(images)} 张产品截图：")
    for img in images:
        print(f"   - {img.name}")

    return images


def image_to_part(image_path):
    """将图片文件转换为 API 可用的 Part 对象"""
    mime_map = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".gif": "image/gif",
    }
    ext = image_path.suffix.lower()
    mime_type = mime_map.get(ext, "image/jpeg")

    with open(image_path, "rb") as f:
        data = f.read()

    return types.Part.from_bytes(data=data, mime_type=mime_type)


def generate_copywriting(client, product_title, images):
    """使用 Gemini 生成小红书文案"""
    print("\n✍️  正在生成文案...")

    # 构建多模态 prompt：文字 + 图片
    user_prompt = COPYWRITING_USER_PROMPT.format(
        num_notes=NUM_NOTES,
        product_title=product_title,
    )

    contents = [user_prompt]
    for img_path in images:
        contents.append(image_to_part(img_path))

    response = client.models.generate_content(
        model=TEXT_MODEL,
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=COPYWRITING_SYSTEM_PROMPT,
            temperature=0.8,
        ),
    )

    # 解析 JSON 响应
    raw_text = response.text.strip()

    # 尝试提取 JSON 块
    if "```json" in raw_text:
        raw_text = raw_text.split("```json")[1].split("```")[0].strip()
    elif "```" in raw_text:
        raw_text = raw_text.split("```")[1].split("```")[0].strip()

    try:
        notes = json.loads(raw_text)
    except json.JSONDecodeError as e:
        print(f"⚠️  JSON 解析失败，尝试修复...")
        print(f"   原始响应：{raw_text[:200]}...")
        # 尝试宽松解析
        notes = []
        print(f"❌ 无法解析文案响应：{e}")
        sys.exit(1)

    print(f"✅ 成功生成 {len(notes)} 篇文案")
    return notes


def generate_cover_image(client, product_title, note_title, index):
    """使用 Gemini 生成封面图"""
    print(f"\n🎨 正在生成封面图 #{index + 1}...")

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

        # 从响应中提取图片数据
        for part in response.candidates[0].content.parts:
            if part.inline_data and part.inline_data.mime_type.startswith("image/"):
                print(f"✅ 封面图 #{index + 1} 生成成功")
                return part.inline_data.data, part.inline_data.mime_type

        print(f"⚠️  封面图 #{index + 1} 未返回图片数据，尝试备用方案...")
        return None, None

    except Exception as e:
        print(f"⚠️  封面图 #{index + 1} 生成失败: {e}")
        return None, None


def generate_cover_with_imagen(client, product_title, note_title, index):
    """备用方案：使用 Imagen 模型生成封面图"""
    print(f"🎨 [备用] 使用 Imagen 生成封面图 #{index + 1}...")

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
            print(f"✅ 封面图 #{index + 1} 生成成功 (Imagen)")
            return img.image.image_bytes, "image/png"

    except Exception as e:
        print(f"⚠️  Imagen 备用方案也失败: {e}")

    return None, None


def save_outputs(notes, cover_images, product_title):
    """保存所有输出到 output 目录"""
    # 创建本次运行的输出子目录
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    run_dir = Path(OUTPUT_DIR) / f"{timestamp}_{product_title[:20]}"
    run_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n💾 保存输出到: {run_dir}")

    # 保存文案
    for i, note in enumerate(notes):
        # 保存为单独的文本文件
        txt_path = run_dir / f"note_{i + 1}.txt"
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(f"📌 标题：{note['title']}\n")
            f.write(f"{'=' * 40}\n\n")
            f.write(f"{note['body']}\n\n")
            f.write(f"{'=' * 40}\n")
            f.write(f"🏷️ 标签：\n")
            f.write(" ".join(note["tags"]))
            f.write("\n")
        print(f"   📄 note_{i + 1}.txt")

    # 保存封面图
    for i, (img_data, mime_type) in enumerate(cover_images):
        if img_data:
            ext = ".png" if "png" in (mime_type or "") else ".jpg"
            img_path = run_dir / f"cover_{i + 1}{ext}"
            with open(img_path, "wb") as f:
                if isinstance(img_data, bytes):
                    f.write(img_data)
                else:
                    f.write(base64.b64decode(img_data))
            print(f"   🖼️  cover_{i + 1}{ext}")

    # 保存汇总 JSON
    summary_path = run_dir / "summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "product_title": product_title,
                "generated_at": timestamp,
                "notes": notes,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )
    print(f"   📋 summary.json")

    return run_dir


def main():
    parser = argparse.ArgumentParser(
        description="小红书笔记批量制作工具 - 输入产品截图和标题，输出封面图+文案"
    )
    parser.add_argument(
        "--title",
        "-t",
        required=True,
        help="产品标题/名称",
    )
    parser.add_argument(
        "--input-dir",
        "-i",
        default=INPUT_DIR,
        help=f"产品截图目录（默认: {INPUT_DIR}）",
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        default=OUTPUT_DIR,
        help=f"输出目录（默认: {OUTPUT_DIR}）",
    )
    parser.add_argument(
        "--skip-cover",
        action="store_true",
        help="跳过封面图生成（只生成文案）",
    )
    parser.add_argument(
        "--num",
        "-n",
        type=int,
        default=NUM_NOTES,
        help=f"生成笔记数量（默认: {NUM_NOTES}）",
    )

    args = parser.parse_args()

    # 覆盖全局配置
    global OUTPUT_DIR
    OUTPUT_DIR = args.output_dir

    print("=" * 50)
    print("📝 小红书笔记批量制作工具")
    print("=" * 50)
    print(f"\n📦 产品：{args.title}")

    # Step 1: 加载图片
    images = load_images(args.input_dir)

    # Step 2: 创建 API 客户端
    client = get_client()

    # Step 3: 生成文案
    notes = generate_copywriting(client, args.title, images)

    # Step 4: 生成封面图
    cover_images = []
    if not args.skip_cover:
        for i, note in enumerate(notes[:args.num]):
            # 先尝试 Gemini 原生图像生成
            img_data, mime_type = generate_cover_image(
                client, args.title, note["title"], i
            )
            # 如果失败，尝试 Imagen
            if img_data is None:
                img_data, mime_type = generate_cover_with_imagen(
                    client, args.title, note["title"], i
                )
            cover_images.append((img_data, mime_type))

            # 避免请求过快
            if i < len(notes) - 1:
                time.sleep(2)
    else:
        print("\n⏭️  跳过封面图生成")
        cover_images = [(None, None)] * len(notes)

    # Step 5: 保存输出
    run_dir = save_outputs(notes[:args.num], cover_images, args.title)

    print(f"\n{'=' * 50}")
    print(f"🎉 完成！共生成 {len(notes[:args.num])} 篇笔记")
    print(f"📂 输出目录：{run_dir}")
    print(f"{'=' * 50}")


if __name__ == "__main__":
    main()
