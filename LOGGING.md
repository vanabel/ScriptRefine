# 日志功能说明

## 📝 日志配置

系统支持详细的调试日志，可以记录每个分片的处理过程。

### 配置选项

在 `config.yaml` 中的 `logging` 部分：

```yaml
logging:
  enabled: true  # 是否启用详细日志
  level: "DEBUG"  # 日志级别: DEBUG, INFO, WARNING, ERROR
  output_to_console: true  # 输出到控制台
  output_to_file: true  # 输出到文件
  log_dir: "./logs"  # 日志目录
  log_chunks: true  # 记录分片信息（原始分片、提示词、输出结果）
  log_file_template: "process_{timestamp}.log"  # 日志文件名模板
```

## 📋 记录的信息

### 文本重写过程

对于每个分片，会记录：

1. **分片基本信息**
   - 分片编号（第 X/共 Y 个）
   - 分片长度（字符数）
   - 讲话人信息
   - 在原文中的位置

2. **原始分片内容**
   - 完整的原始分片文本（不截断）

3. **系统提示词**
   - 完整的系统提示词

4. **用户提示词**
   - 完整的用户提示词（包含原始文本和上下文信息）

5. **LLM 输出结果**
   - 完整的 LLM 生成结果（不截断）

6. **处理状态**
   - 处理开始/完成时间
   - 错误信息（如果有）

### 会议纪要生成过程

会记录：

1. **输入信息**
   - 输入文本长度
   - 提示词内容

2. **输出结果**
   - 完整的会议纪要内容

## 📂 日志文件

- 日志文件保存在 `logs/` 目录下
- 文件名格式：`process_YYYYMMDD_HHMMSS.log`
- 每次处理会生成新的日志文件

## 🔍 使用示例

### 启用日志

在 `config.yaml` 中设置：

```yaml
logging:
  enabled: true
  level: "DEBUG"
  output_to_console: true
  output_to_file: true
  log_chunks: true
```

### 查看日志

#### 控制台输出

日志会实时输出到控制台，包括：
- 分片处理进度
- 每个分片的详细信息
- 提示词和输出结果

#### 日志文件

日志文件包含完整的处理过程，可以用于：
- 调试问题
- 分析处理效果
- 优化提示词
- 检查内容是否完整

### 禁用日志

如果不需要详细日志，可以设置：

```yaml
logging:
  enabled: false
```

或者只禁用分片详细记录：

```yaml
logging:
  enabled: true
  log_chunks: false  # 不记录每个分片的详细信息
```

## 💡 日志级别

- **DEBUG**: 最详细，包括所有调试信息
- **INFO**: 一般信息，包括处理进度和结果
- **WARNING**: 警告信息
- **ERROR**: 错误信息

## 📊 日志格式

```
2024-01-01 12:00:00 - ScriptRefine.Rewriter - INFO - 📦 文本已分割为 3 个分片
2024-01-01 12:00:01 - ScriptRefine.Rewriter - INFO - 🔄 处理分片 1/3
2024-01-01 12:00:01 - ScriptRefine.Rewriter - INFO - 📝 原始分片内容 (500 字符):
...
```

## 🎯 使用场景

1. **调试问题**：查看每个分片的处理过程，找出问题所在
2. **优化提示词**：查看实际使用的提示词，优化效果
3. **检查完整性**：验证所有内容都被正确处理
4. **性能分析**：分析处理时间和效果
5. **质量评估**：对比原始分片和输出结果，评估处理质量

