"""
card_generator.py - 使用 guizang 风格模板生成小红书封面卡片

依赖: jinja2, playwright, Pillow
"""
import base64
import os
import tempfile
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

# 模板目录
_TEMPLATE_DIR = Path(__file__).parent / "templates"
_ENV = Environment(
    loader=FileSystemLoader(str(_TEMPLATE_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
)

# 封面图尺寸
CARD_WIDTH = 1080
CARD_HEIGHT = 1440


def image_to_b64(image_path: str) -> str:
    """将图片文件转为 base64 字符串 (PNG 格式)。

    兼容各种 PIL mode（RGBA / P / L / CMYK / 1 等），统一输出 RGB PNG。
    """
    from PIL import Image

    img = Image.open(image_path)

    # 第一步：统一转成 RGB（兼容所有原始 mode）
    if img.mode != "RGB":
        # RGBA / P+透明 → 用浅色底合成；其它 mode 直接 convert
        if img.mode == "RGBA":
            bg = Image.new("RGB", img.size, (250, 250, 248))
            bg.paste(img, mask=img.split()[-1])  # 用 alpha 通道当蒙版
            img = bg
        elif img.mode == "P" and "transparency" in img.info:
            img = img.convert("RGBA")
            bg = Image.new("RGB", img.size, (250, 250, 248))
            bg.paste(img, mask=img.split()[-1])
            img = bg
        else:
            img = img.convert("RGB")

    # 第二步：缩放（保持比例，宽度上限 CARD_WIDTH）
    w, h = img.size
    if w > CARD_WIDTH:
        ratio = CARD_WIDTH / w
        new_w = CARD_WIDTH
        new_h = int(h * ratio)
        img = img.resize((new_w, new_h), Image.LANCZOS)

    import io
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=False)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def render_card_html(
    note_title: str,
    product_title: str,
    image_path: str,
    tags: list | None = None,
    layout: str = "split",
) -> str:
    """
    渲染一张详情页卡片的 HTML（使用 card-cover.html 模板）。

    Args:
        note_title: 笔记标题
        product_title: 产品名称
        image_path: 截图文件路径
        tags: 标签列表
        layout: "split"（截图在上/文字在下）或 "hero"（全屏截图+文字浮层）

    Returns:
        HTML 字符串
    """
    template = _ENV.get_template("card-cover.html")

    image_b64 = image_to_b64(image_path)

    html = template.render(
        title=f"{product_title} - {note_title}",
        note_title=note_title,
        product_title=product_title,
        image_b64=image_b64,
        tags=tags or [],
        layout=layout,
    )
    return html


def render_cover_html(
    note_title: str,
    product_title: str,
    image_paths: list[str],
    tags: list | None = None,
    subtitle: str | None = None,
    vol: int = 1,
    stock_b64: str | None = None,
    cover_layout: str = "A",
) -> str:
    """
    渲染一张 Swiss 杂志风格封面卡片的 HTML（多截图 + stock photo 背景）。

    Args:
        note_title: 笔记标题
        product_title: 产品名称
        image_paths: 截图文件路径列表（最多4张）
        tags: 标签列表
        subtitle: 副标题（可选）
        vol: 卷号
        stock_b64: 可选库存照片 base64，作为背景
        cover_layout: 排版布局 "A"（经典 Swiss）或 "B"（全屏截图+底部面板）

    Returns:
        HTML 字符串
    """
    template = _ENV.get_template("cover-swiss.html")

    # 封面最多展示 2 张截图（保持简洁），每个配不同 bg tone
    BG_TONES = ["grid", "dot", "paper", "ink"]
    max_imgs = min(len(image_paths), 2)
    images = []
    for i in range(max_imgs):
        try:
            b64 = image_to_b64(image_paths[i])
        except Exception:
            b64 = None
        images.append({"b64": b64, "bg": BG_TONES[i % len(BG_TONES)]})

    from datetime import date
    today = date.today()

    html = template.render(
        title=f"{product_title} - {note_title}",
        note_title=note_title,
        product_title=product_title,
        subtitle=subtitle or "",
        images=images,
        image_count=max_imgs,
        stock_b64=stock_b64 or "",
        tags=tags or [],
        vol=f"{vol:02d}",
        date=today.strftime("%Y.%m"),
        cover_layout=cover_layout,
    )
    return html


def html_to_png(html: str, output_path: str) -> str:
    """
    使用系统 Edge (Chromium) 将 HTML 渲染为 PNG。

    优先使用系统已安装的 Edge（避免 CDN 下载 Chromium），
    若不可用则回退到 Playwright 内置 Chromium。

    Args:
        html: HTML 字符串
        output_path: 输出 PNG 文件路径

    Returns:
        输出文件路径
    """
    from playwright.sync_api import sync_playwright

    # 写入临时 HTML 文件
    tmp_html = Path(tempfile.mkdtemp()) / "card.html"
    tmp_html.write_text(html, encoding="utf-8")

    with sync_playwright() as p:
        # 优先用系统 Edge (避免被墙的 CDN 下载)
        try:
            browser = p.chromium.launch(
                channel="msedge",
                headless=True,
                args=["--disable-gpu", "--no-sandbox"],
            )
        except Exception:
            # 回退到 Playwright 内置 chromium（如果有的话）
            browser = p.chromium.launch(
                headless=True,
                args=["--disable-gpu", "--no-sandbox"],
            )
        page = browser.new_page(
            viewport={"width": CARD_WIDTH, "height": CARD_HEIGHT},
            device_scale_factor=2,
        )
        page.goto(f"file://{tmp_html.resolve()}", wait_until="domcontentloaded", timeout=30000)
        # 等字体 + 图片加载
        page.wait_for_timeout(3000)
        page.screenshot(path=output_path, full_page=False)
        browser.close()

    # 清理临时文件
    tmp_html.unlink(missing_ok=True)

    return output_path


def generate_cover(
    note_title: str,
    product_title: str,
    image_path: str,
    output_path: str,
    tags: list | None = None,
    layout: str = "split",
) -> str | None:
    """
    生成一张详情页卡片（使用 card-cover.html 模板）。

    Args:
        note_title: 笔记标题
        product_title: 产品名称
        image_path: 截图文件路径
        output_path: 输出 PNG 文件路径
        tags: 标签列表
        layout: 布局模式 ("split" / "hero")

    Returns:
        输出文件路径，或失败时返回 None
    """
    try:
        html = render_card_html(
            note_title=note_title,
            product_title=product_title,
            image_path=image_path,
            tags=tags,
            layout=layout,
        )
        return html_to_png(html, output_path)
    except Exception as e:
        print(f"[ERROR] 详情页卡片生成失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def generate_magazine_cover(
    note_title: str,
    product_title: str,
    image_paths: list[str],
    output_path: str,
    tags: list | None = None,
    subtitle: str | None = None,
    vol: int = 1,
    stock_b64: str | None = None,
    cover_layout: str = "A",
) -> str | None:
    """
    生成一张 Swiss 杂志风格的封面卡片（多截图 + 可选 stock photo 背景）。

    Args:
        note_title: 笔记标题
        product_title: 产品名称
        image_paths: 截图文件路径列表（最多4张）
        output_path: 输出 PNG 文件路径
        tags: 标签列表
        subtitle: 副标题（可选）
        vol: 卷号
        stock_b64: 可选库存照片 base64
        cover_layout: 排版布局 "A"（经典 Swiss）或 "B"（全屏截图+底部面板）

    Returns:
        输出文件路径，或失败时返回 None
    """
    try:
        html = render_cover_html(
            note_title=note_title,
            product_title=product_title,
            image_paths=image_paths,
            tags=tags,
            subtitle=subtitle,
            vol=vol,
            stock_b64=stock_b64,
            cover_layout=cover_layout,
        )
        return html_to_png(html, output_path)
    except Exception as e:
        print(f"[ERROR] 杂志封面生成失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def generate_detail_pages(
    note_title: str,
    product_title: str,
    image_paths: list[str],
    output_dir: str,
    tags: list | None = None,
    prefix: str = "detail",
    count: int = 5,
) -> list[tuple[str | None, str]]:
    """
    为一篇笔记生成多张详情页卡片（每张使用不同截图，轮换布局）。

    Args:
        note_title: 笔记标题
        product_title: 产品名称
        image_paths: 截图文件路径列表（会循环使用）
        output_dir: 输出目录
        tags: 标签列表
        prefix: 输出文件名前缀
        count: 生成张数（默认 5）

    Returns:
        [(输出路径或 None, layout名称), ...] 列表
    """
    LAYOUTS = ["split", "hero", "split", "hero", "split"]
    results = []

    for i in range(count):
        img_idx = i % len(image_paths)
        layout = LAYOUTS[i % len(LAYOUTS)]
        out_path = Path(output_dir) / f"{prefix}_{i+1}.png"

        result = generate_cover(
            note_title=note_title,
            product_title=product_title,
            image_path=image_paths[img_idx],
            output_path=str(out_path),
            tags=tags,
            layout=layout,
        )
        results.append((result, layout))

    return results
