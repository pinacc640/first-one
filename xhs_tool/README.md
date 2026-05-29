# 小红书封面卡片生成工具

上传 3 张以上产品截图 + 标题，自动生成 **3 篇接地气文案** + **5 种瑞士国际主义风格的杂志感封面卡片**。

文案由 Gemini 多模态 AI 读图生成；封面卡片由 Playwright 在本地渲染 HTML 模板，不调用任何付费图像 API。

---

## 核心特点

- **双 Gemini API key 轮换** — 两个 Google 账户的免费配额轮换调用，单号被限速时自动切到另一个
- **5 种瑞士排版** — Swiss Grid / Full-bleed Hero / Serif Center / Dark Cinematic / Product Grid，每次生成自动轮换
- **本地渲染封面** — Playwright + Chromium 渲染 HTML → PNG，不依赖任何付费图像 API
- **接地气文案** — Prompt 调优过，避免"绝绝子"式油腻表达
- **Web + CLI 两种模式** — Streamlit 可视化界面 + 命令行
- **完全开源** — MIT 协议，本地运行，数据不出本机

---

## 快速开始

### 1. 克隆 + 安装依赖

```bash
git clone https://github.com/pinacc640/first-one.git
cd first-one/xhs_tool
pip install -r requirements.txt
playwright install chromium
```

> 第一次会下载 Chromium 内核（约 150 MB），慢一点正常。

### 2. 申请两个 Gemini API key

为了把免费额度翻倍，建议用**两个不同的 Google 账户**各申请一个 key：

- 账户 A：登录 <https://aistudio.google.com/apikey> → 创建 API key
- 账户 B：换浏览器或隐身窗口登录第二个 Google 账户，重复上一步

### 3. 配置 key

复制模板文件，然后填入你的 key：

```bash
cp config_local.py.example config_local.py
```

打开 `config_local.py`，把两个占位字符串换成你的两个 Gemini API key：

```python
GEMINI_API_KEYS = [
    "你的第一个 key",
    "你的第二个 key",
]
```

> `config_local.py` 已经在 `.gitignore` 中，**不会被推到 GitHub**。永远不要把 key 写在 `config.py` 里。

如果你不想用文件，也可以走环境变量：

```bash
export GEMINI_API_KEY="key1"
export GEMINI_API_KEY_2="key2"
```

### 4. 启动

```bash
streamlit run web_app.py
```

浏览器打开 <http://localhost:8501>：

1. 输入产品标题
2. 上传 3 张以上产品截图
3. 点「生成」→ 得到 3 篇文案 + 5 张封面卡片

---

## 5 种封面卡片排版

每次生成会按顺序输出 5 种布局，避免审美疲劳：

| ID | 风格 | 说明 |
|----|------|------|
| **A** | Swiss Grid | 深色大字报，设备框包裹截图 |
| **B** | Full-bleed Hero | 全屏大图 + 浮层标题 |
| **C** | Serif Center | 衬线居中，大量留白 |
| **D** | Dark Cinematic | 深色电影感 |
| **E** | Product Grid | 网格多截图 |

字体走 Google Fonts CDN（Inter + Noto Sans SC + Noto Serif SC + JetBrains Mono），离线环境会回退到系统字体。

截图自动叠加 IKB 蓝滤镜 + 灰度处理，与背景融合，杂志感更强。

### 测试 5 种排版

不想跑完整流程，先看 5 种排版长啥样：

```bash
python test_layouts.py
```

输出在 `output/test_layout_A.png` … `test_layout_E.png`。

---

## 输出结构

每次运行会在 `output/` 下创建带时间戳的子目录：

```
output/20260529_143022_产品名/
├── note_1.txt        第 1 篇文案（标题 + 正文 + 标签）
├── note_2.txt        第 2 篇文案
├── note_3.txt        第 3 篇文案
├── cover_A.png       A 排版封面
├── cover_B.png       B 排版封面
├── cover_C.png       C 排版封面
├── cover_D.png       D 排版封面
├── cover_E.png       E 排版封面
└── summary.json      汇总数据
```

---

## 文案风格

提示词调优过的方向：

- 务实不夸张，不堆砌"绝绝子"这种词
- 像朋友推荐一样自然
- 带具体使用细节
- 适当口语化，但不油腻

---

## 依赖环境

- Python 3.10+
- google-genai
- streamlit
- jinja2
- playwright（含 Chromium）
- Pillow

完整版本号见 [`requirements.txt`](./requirements.txt)。

---

## 注意事项

- 需要能访问 Google API（Gemini）
- 双 key 轮换不是无限免费，密集调用还是会撞总额度
- Playwright 第一次启动需要下载 Chromium（约 150 MB）
- 生成内容仅供参考，发布前请审核
- 字体走 Google Fonts CDN，离线环境会回退到系统字体

---

## 项目结构

```
xhs_tool/
├── web_app.py          Streamlit Web UI（推荐入口）
├── card_generator.py   封面卡片渲染（Jinja2 + Playwright）
├── stock_photos.py     备用素材图获取
├── prompts.py          Gemini 文案生成提示词
├── config.py           配置（API keys、模型名、尺寸）
├── test_layouts.py     5 种排版测试脚本
├── templates/          HTML 模板（5 种排版）
├── input/              产品截图输入目录
├── output/             生成结果输出目录
└── requirements.txt
```

---

## License

MIT
