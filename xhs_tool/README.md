# 小红书笔记批量制作工具

一个务实的小红书内容批量生成工具。上传 3 张产品截图 + 产品标题，自动输出 3 张封面图 + 3 份完整文案（标题、正文、10个标签）。

## 工作原理

```
输入：3张产品截图 + 产品标题
        ↓
  [Gemini 2.5 Flash] → 分析截图，生成3篇不同角度的文案
  [图像服务链]        → 根据文案标题，生成3张封面图
        ↓
输出：3张可下载封面图 + 3份可复制文案（标题/正文/标签）
```

- **文案生成**：使用 Gemini 2.5 Flash（多模态），能看懂产品截图并写出接地气的种草文案
- **封面图生成**：多 provider 自动回退链（详见下方"封面图方案选择"）

## 封面图方案选择

Gemini 和 GPT-Image 官方 API 的免费 tier 配额均为 0，高质量图需付费。工具实现了**按优先级自动回退**：

| 优先级 | 服务 | 质量 | 花费 | 配置方式 |
|------|------|------|------|---------|
| 1 | Gemini 2.5 Flash Image | ★★★★★ | ~$0.04/张 | 需在 AI Studio 升级到 Tier 1（绑卡） |
| 2 | OpenAI gpt-image-1 | ★★★★★ | ~$0.04/张 | `export OPENAI_API_KEY=sk-...` |
| 3 | SiliconFlow FLUX.1-dev | ★★★★☆ | **免费（送额度）** | `export SILICONFLOW_API_KEY=sk-...` |
| 4 | Pollinations gptimage-large | ★★★★ | **完全免费** | 无需任何配置 |

**推荐方案**：注册 [硅基流动 SiliconFlow](https://cloud.siliconflow.cn/account/ak)，新账号送 ¥14 额度（约 700 张 FLUX.1 图），质量接近 Gemini，完全免费。

## 快速开始

### 1. 安装依赖

```bash
cd xhs_tool
pip install -r requirements.txt
```

### 2. 获取 API Key

前往 [Google AI Studio](https://aistudio.google.com/apikey) 免费获取 API Key。

设置环境变量：

```bash
export GEMINI_API_KEY="你的API密钥"
```

或者直接编辑 `config.py` 文件填入。

### 3. 放入产品截图

将 3 张产品截图放入 `input/` 目录：

```
xhs_tool/
└── input/
    ├── screenshot_1.png
    ├── screenshot_2.jpg
    └── screenshot_3.png
```

支持格式：PNG、JPG、JPEG、WebP、GIF

### 4. 运行

```bash
python main.py --title "产品名称"
```

## 命令行参数

| 参数 | 简写 | 说明 | 默认值 |
|------|------|------|--------|
| `--title` | `-t` | 产品标题（必填） | - |
| `--input-dir` | `-i` | 截图输入目录 | `./input` |
| `--output-dir` | `-o` | 输出目录 | `./output` |
| `--num` | `-n` | 生成笔记数量 | 3 |
| `--skip-cover` | - | 跳过封面图生成 | False |

### 示例

```bash
# 基本用法
python main.py -t "Sony WH-1000XM5 降噪耳机"

# 只生成文案，不生成封面图
python main.py -t "戴森吹风机" --skip-cover

# 指定输入输出目录
python main.py -t "iPad Pro" -i ./my_screenshots -o ./results

# 生成5篇笔记
python main.py -t "小米手环8" -n 5
```

## 输出结构

每次运行会在 `output/` 下创建一个带时间戳的子目录：

```
output/
└── 20250511_143022_Sony WH-1000XM/
    ├── note_1.txt          # 第1篇文案
    ├── note_2.txt          # 第2篇文案
    ├── note_3.txt          # 第3篇文案
    ├── cover_1.png         # 第1张封面图
    ├── cover_2.png         # 第2张封面图
    ├── cover_3.png         # 第3张封面图
    └── summary.json        # 汇总数据（JSON格式，便于程序读取）
```

### 文案文件示例

```
📌 标题：这副耳机让我通勤路上终于安静了
========================================

最近换了新耳机，用了两周来说说真实感受...
（正文内容）

========================================
🏷️ 标签：
#降噪耳机 #通勤好物 #索尼耳机 #WH1000XM5 ...
```

## 配置说明

编辑 `config.py` 可调整：

- `GEMINI_API_KEY` - API 密钥
- `TEXT_MODEL` - 文案模型（默认 gemini-2.5-flash）
- `IMAGE_MODEL` - 图像模型（默认 gemini-2.0-flash-exp）
- `NUM_NOTES` - 默认生成数量
- `IMAGE_WIDTH` / `IMAGE_HEIGHT` - 封面图尺寸

## 文案风格

工具生成的文案风格定位为：
- 务实、不夸张
- 像朋友推荐一样自然
- 有具体使用细节和真实感受
- 适当口语化但不过度

如需调整风格，编辑 `prompts.py` 中的提示词模板即可。

## 注意事项

1. **API 用量**：每次运行会调用约 4 次 API（1次文案 + 3次图像），注意 Google AI Studio 的免费配额
2. **图像生成**：Gemini 原生图像生成目前是实验性功能，偶尔可能失败，工具会自动尝试 Imagen 备用方案
3. **网络要求**：需要能访问 Google API 的网络环境
4. **内容审核**：生成内容仅供参考，发布前请自行检查是否符合平台规范
