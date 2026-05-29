"""
stock_photos.py - 免费可商用图库集成

优先级:
  1. Pexels (免费，200 req/h，需 API key)
  2. picsum.photos (免费，无需 key，纯随机风景照)

用法:
  img_b64 = fetch_stock_image("教辅 书籍 课堂")
  # 返回 base64 JPEG，失败时返回 None
"""

import base64
import json
import os
import urllib.parse
import urllib.request

# Pexels API — 免费获取: https://www.pexels.com/api/
PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY", "")


def fetch_stock_image(query: str, timeout: int = 15) -> str | None:
    """按关键词搜索库存照片，返回 base64 JPEG。"""
    # 优先级 1: Pexels
    if PEXELS_API_KEY:
        try:
            return _pexels_search(query, timeout)
        except Exception as e:
            print(f"[stock] Pexels 失败: {e[:60]}")

    # 优先级 2: picsum.photos (纯随机，无关关键词)
    try:
        return _picsum_random(timeout)
    except Exception as e:
        print(f"[stock] picsum 失败: {e[:60]}")

    return None


def _pexels_search(query: str, timeout: int) -> str | None:
    encoded = urllib.parse.quote(query)
    url = f"https://api.pexels.com/v1/search?query={encoded}&per_page=1&orientation=portrait"
    req = urllib.request.Request(url, headers={"Authorization": PEXELS_API_KEY})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    photos = data.get("photos", [])
    if not photos:
        return None

    # 取中等尺寸
    src = photos[0]["src"].get("large", photos[0]["src"]["original"])

    with urllib.request.urlopen(src, timeout=timeout) as img_resp:
        return base64.b64encode(img_resp.read()).decode("utf-8")


def _picsum_random(timeout: int) -> str | None:
    url = "https://picsum.photos/1080/1440"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return base64.b64encode(resp.read()).decode("utf-8")
