"""Test all 5 cover layouts."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from card_generator import render_cover_html, html_to_png

os.makedirs("output", exist_ok=True)
image_paths = [os.path.join("input", f"test_screenshot_{i+1}.png") for i in range(2)]

layouts = ["A", "B", "C", "D", "E"]
for i, layout in enumerate(layouts):
    html = render_cover_html(
        note_title="笔记标题最多十二字示例",
        product_title="产品名称示例",
        image_paths=image_paths,
        tags=["标签1", "标签2", "标签3", "标签4", "标签5", "标签6"],
        subtitle="副标题｜说明文字｜关键词概括",
        vol=i + 1,
        cover_layout=layout,
    )
    path = f"output/test_layout_{layout}.png"
    html_to_png(html, path)
    size = os.path.getsize(path) // 1024
    print(f"Layout {layout}: OK ({size}KB)")
