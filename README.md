# 📝 语稿智能整理系统

> 自动将混乱的语音识别文本，转换为高质量、结构化、可存档的正式文稿

## ✨ 核心功能

- ✅ **文本清洗**：移除 ASR 冗余符号、合并断裂句子、清理重复词和口头禅
- ✅ **逐句纠错与语义重写**：语义补全、语病修正、专业术语纠正、去口语化
- ✅ **保持讲话人段落结构**：自动识别讲话人，保持完整结构
- ✅ **双模式输出**：完整逐句重写版 + 会议纪要版
- ✅ **长文本自动切片**：支持几万字文本，自动分块处理
- ✅ **多模型支持**：本地 LLM（Qwen2.5、Llama、ChatGLM）和在线 API（OpenAI、DeepSeek、通义、智谱）

## 🚀 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置

1. 复制配置文件：
```bash
cp config.yaml config_local.yaml
```

2. 编辑 `config_local.yaml`，设置你的 LLM API 密钥或本地模型路径

3. 创建 `.env` 文件（可选，用于存储敏感信息）：
```
OPENAI_API_KEY=your_key_here
DEEPSEEK_API_KEY=your_key_here
```

### 使用

#### 🌐 Web 界面（推荐）

启动 Web 服务器：

```bash
python app.py
```

然后在浏览器中访问 `http://localhost:8080`（默认端口，可通过环境变量 PORT 修改）

功能特点：
- 📝 文本输入或文件上传
- ✨ 实时处理并显示结果
- 📄 支持下载 Word、PDF、Markdown 格式
- 🎨 现代化 UI 界面

#### 命令行模式

```bash
python main.py --input input.txt --output output/ --mode full
```

#### Python API

```python
from script_refine import ScriptRefiner

refiner = ScriptRefiner(config_path="config_local.yaml")
result = refiner.process("input.txt", output_mode="full")
```

## 📁 项目结构

```
ScriptRefine/
├── app.py                 # Web 应用入口
├── main.py                # CLI 入口
├── config.yaml            # 默认配置
├── requirements.txt       # 依赖包
├── templates/             # Web 模板
│   └── index.html        # 前端页面
├── static/                # 静态资源
│   ├── style.css         # 样式文件
│   └── script.js         # 前端脚本
├── script_refine/         # 核心模块
│   ├── __init__.py
│   ├── llm/              # LLM 接口层
│   │   ├── base.py       # 基础接口
│   │   ├── local.py      # 本地模型
│   │   └── online.py     # 在线 API
│   ├── text_processor/   # 文本处理
│   │   ├── cleaner.py    # 文本清洗
│   │   ├── chunker.py   # 文本切片
│   │   └── speaker.py   # 讲话人识别
│   ├── rewriter.py       # 重写核心逻辑
│   ├── summarizer.py     # 会议纪要生成
│   └── output.py         # 文档输出
├── prompts/              # 提示词模板
│   ├── rewrite.txt
│   ├── summary.txt
│   └── cleaning.txt
└── output/               # 输出目录
```

## 🔧 配置说明

详见 `config.yaml` 文件注释。

## 📝 许可证

MIT License

