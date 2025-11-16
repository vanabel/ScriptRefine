# 使用指南

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置

#### 方式一：使用环境变量（推荐）

创建 `.env` 文件：

```bash
# OpenAI
OPENAI_API_KEY=sk-xxx

# DeepSeek
DEEPSEEK_API_KEY=sk-xxx

# 阿里通义
DASHSCOPE_API_KEY=sk-xxx

# 智谱 GLM
ZHIPUAI_API_KEY=xxx

# Anthropic Claude
ANTHROPIC_API_KEY=sk-xxx
```

#### 方式二：在配置文件中设置

编辑 `config.yaml` 或创建 `config_local.yaml`：

```yaml
llm:
  type: "online"
  online:
    provider: "openai"  # 或 deepseek, qianwen, zhipu, anthropic
    model: "gpt-4-turbo-preview"
    api_key: "sk-xxx"  # 或从环境变量读取
```

### 3. 使用命令行

#### 生成完整版

```bash
python main.py -i example_input.txt -m full
```

#### 生成会议纪要

```bash
python main.py -i example_input.txt -m summary
```

#### 同时生成完整版和会议纪要

```bash
python main.py -i example_input.txt -m both
```

#### 使用自定义配置

```bash
python main.py -i example_input.txt -c config_local.yaml -m full
```

### 4. 使用 Python API

```python
from script_refine import ScriptRefiner

# 初始化
refiner = ScriptRefiner(config_path="config_local.yaml")

# 处理文件
results = refiner.process(
    input_path="example_input.txt",
    output_mode="both",  # full, summary, both
    show_progress=True
)

# 或直接处理文本
text = "你的文本内容..."
results = refiner.process_text(text, output_mode="full")
print(results["full"])
```

## 配置说明

### LLM 配置

#### 在线模型

支持以下提供商：
- `openai`: OpenAI GPT 系列
- `deepseek`: DeepSeek
- `qianwen`: 阿里通义千问
- `zhipu`: 智谱 GLM
- `anthropic`: Anthropic Claude

#### 本地模型

支持以下模型：
- `qwen2.5`: Qwen2.5 系列
- `llama`: Llama 系列
- `chatglm`: ChatGLM 系列

配置示例：

```yaml
llm:
  type: "local"
  local:
    provider: "qwen2.5"
    model_path: "/path/to/model"  # 可选，默认使用 HuggingFace 模型
    device: "auto"  # auto, cuda, cpu
```

### 文本处理配置

```yaml
text_processing:
  cleaning:
    remove_filler_words: true  # 去除语气词
    merge_broken_sentences: true  # 合并断句
    remove_duplicates: true  # 去除重复
    fix_encoding: true  # 修复乱码
  
  chunking:
    max_tokens: 3000  # 每个分片的 token 限制
    overlap: 200  # 分片重叠 token 数
    preserve_speakers: true  # 保持讲话人结构
  
  speaker_detection:
    enabled: true
    patterns:
      - "【.*?】"  # 匹配【讲话人】格式
      - ".*?:"  # 匹配 讲话人: 格式
```

### 输出配置

```yaml
output:
  formats: ["markdown", "docx"]  # 支持格式
  output_dir: "./output"
  
  full_version:
    filename_template: "完整版_{timestamp}.md"
  
  summary_version:
    filename_template: "会议纪要_{timestamp}.md"
    structure:
      - "会议背景"
      - "主要议题"
      - "双方主要观点"
      - "达成共识与行动计划"
      - "后续工作安排"
```

## 自定义提示词

可以在 `prompts/` 目录下自定义提示词模板：

- `rewrite.txt`: 文本重写提示词（支持 `{text}`, `{speaker_info}`, `{context_info}` 占位符）
- `summary.txt`: 会议纪要提示词（支持 `{text}`, `{structure}` 占位符）
- `cleaning.txt`: 文本清洗提示词（支持 `{text}` 占位符）

## 常见问题

### Q: 如何处理很长的文本？

A: 系统会自动将文本切片处理，每个切片不超过配置的 `max_tokens` 限制。切片之间会有重叠，以保持上下文连贯性。

### Q: 如何保持讲话人结构？

A: 系统会自动识别讲话人标记（如 `【主持人】`、`讲话人:` 等），并在重写时保持这些结构。

### Q: 本地模型运行慢怎么办？

A: 可以：
1. 使用 GPU 加速（设置 `device: "cuda"`）
2. 减小 `max_tokens` 限制
3. 使用更小的模型
4. 考虑使用在线 API

### Q: 如何提高输出质量？

A: 可以：
1. 使用更强大的模型（如 GPT-4）
2. 自定义提示词模板
3. 调整 `temperature` 参数（较低的值更稳定）
4. 增加 `max_tokens` 限制

## 输出示例

### 完整版输出

```
【主持人】

大家好，今天我们召开关于教学改革的讨论会，我想听取大家的意见。

【党委书记 唐宇】

好的，我来说几句。首先，我们这次来到开州中学，主要有三方面目的：第一，了解学校的教学情况；第二，听取教师们的意见；第三，讨论下一步的改革方向。我认为教学质量很重要，需要进一步提升。

【教师代表 郭俊华】

我同意唐书记的观点。在实际教学中，我们发现了一些问题，比如学生参与度不够高，课堂氛围比较沉闷。我认为需要改进教学方法，让学生更主动地参与进来。

...
```

### 会议纪要输出

```
一、会议背景

本次会议旨在讨论教学改革相关问题，与会人员包括党委书记唐宇、教师代表郭俊华等。

二、主要议题

1. 教学情况了解
2. 教师意见听取
3. 改革方向讨论

三、主要观点

1. 唐书记提出三方面目的：了解教学情况、听取意见、讨论改革方向
2. 郭老师反映学生参与度不高、课堂氛围沉闷的问题
3. 需要改进教学方法，提升教学质量

...
```

