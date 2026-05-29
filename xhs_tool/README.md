# 小红书封面卡片生成工具

上传产品截图，自动生成杂志风格的小红书封面卡片 + 详情页 + 文案。

## 快速开始

```bash
cd xhs_tool
pip install -r requirements.txt
```

## 配置

编辑 `config.py` 或设环境变量：

| 变量 | 用途 | 获取地址 |
|------|------|---------|
| `GEMINI_API_KEY` | 文案生成（免费够用） | https://aistudio.google.com/apikey |
| `OPENAI_API_KEY` | 封面图（付费） | https://platform.openai.com/api-keys |
| `SILICONFLOW_API_KEY` | 封面图（国内推荐） | https://cloud.siliconflow.cn/account/ak |

封面图生成按优先级自动回退：Gemini → OpenAI → SiliconFlow → Pollinations（免费兜底，无需 key）。

## 运行

```bash
streamlit run web_app.py
```

1. 输入产品标题
2. 上传 3+ 张截图
3. 点击生成 → 得到 3 篇文案 + 封面卡片

## 封面卡片

使用 **guizang 瑞士国际主义风格** 的 5 种排版布局，自动轮换：

- **A** Swiss Grid — 深色大字报，设备框截图
- **B** Full-bleed Hero — 全屏大图 + 浮层标题
- **C** Serif Center — 衬线居中，大量留白
- **D** Dark Cinematic — 深色电影感
- **E** Product Grid — 网格多截图

字体通过 Google Fonts CDN 加载（Inter + Noto Sans SC + Noto Serif SC + JetBrains Mono）。
截图自动叠加 IKB 蓝滤镜 + 灰度处理，与背景融合。

## 手动测试

```bash
python test_layouts.py     # 生成 5 种排版测试图
```

输出在 `output/` 目录。
