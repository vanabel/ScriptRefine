"""文本重写模块"""

import os
import logging
from datetime import datetime
from typing import List, Dict, Optional
from tqdm import tqdm
from .llm import BaseLLM
from .text_processor import TextChunker


class TextRewriter:
    """文本重写器"""
    
    def __init__(self, llm: BaseLLM, config: Dict):
        self.llm = llm
        self.config = config
        self.chunker = TextChunker(
            config.get("chunking", {}),
            llm=llm
        )
        self.rewrite_prompt = self._load_prompt(config.get("prompts", {}).get("rewrite_prompt", ""))
        
        # 初始化日志
        self.logger = self._init_logger(config.get("logging", {}))
    
    def rewrite(self, text: str, show_progress: bool = True) -> str:
        """
        重写文本
        
        Args:
            text: 原始文本
            show_progress: 是否显示进度条
            
        Returns:
            重写后的文本
        """
        # 切片
        chunks = self.chunker.chunk(text)
        
        if not chunks:
            return ""
        
        # 记录分片信息
        if self.logger:
            self.logger.info(f"📦 文本已分割为 {len(chunks)} 个分片")
            for i, chunk in enumerate(chunks):
                self.logger.debug(f"分片 {i+1}/{len(chunks)}: 长度={len(chunk['text'])} 字符, "
                                f"讲话人={chunk.get('speaker', '无')}, "
                                f"位置={chunk.get('start_idx', 0)}-{chunk.get('end_idx', 0)}")
        
        # 逐块重写
        rewritten_chunks = []
        iterator = tqdm(chunks, desc="重写文本") if show_progress else chunks
        
        for i, chunk in enumerate(iterator):
            rewritten = self._rewrite_chunk(chunk, i, len(chunks))
            if rewritten:
                rewritten_chunks.append(rewritten)
        
        # 合并结果
        result = self._merge_chunks(rewritten_chunks)
        
        if self.logger:
            self.logger.info(f"✅ 重写完成，共处理 {len(rewritten_chunks)} 个分片，最终结果长度: {len(result)} 字符")
        
        return result
    
    def _rewrite_chunk(self, chunk: Dict, chunk_idx: int, total_chunks: int) -> str:
        """重写单个切片"""
        text = chunk["text"]
        speaker = chunk.get("speaker")
        
        # 构建提示词
        prompt = self._build_prompt(text, speaker, chunk_idx, total_chunks)
        system_prompt = self._get_system_prompt()
        
        # 记录分片信息
        if self.logger:
            self.logger.info(f"\n{'='*80}")
            self.logger.info(f"🔄 处理分片 {chunk_idx + 1}/{total_chunks}")
            self.logger.info(f"{'='*80}")
            self.logger.info(f"📝 原始分片内容 ({len(text)} 字符):")
            self.logger.info(f"{'-'*80}")
            # 记录完整内容（不截断）
            self.logger.info(text)
            self.logger.info(f"{'-'*80}")
            self.logger.info(f"👤 讲话人: {speaker if speaker else '无'}")
            self.logger.info(f"📋 系统提示词:")
            self.logger.info(f"{'-'*80}")
            self.logger.info(system_prompt)
            self.logger.info(f"{'-'*80}")
            self.logger.info(f"💬 用户提示词 ({len(prompt)} 字符):")
            self.logger.info(f"{'-'*80}")
            # 记录完整提示词（不截断）
            self.logger.info(prompt)
            self.logger.info(f"{'-'*80}")
        
        # 调用 LLM
        try:
            if self.logger:
                self.logger.info("⏳ 正在调用 LLM 生成...")
            
            rewritten = self.llm.generate(
                prompt,
                system_prompt=system_prompt,
                temperature=self.config.get("temperature", 0.3),
                max_tokens=self.config.get("max_tokens", 4000),
            )
            
            # 移除 LLM 推理标记
            rewritten = self._remove_reasoning_markers(rewritten)
            
            # 保留讲话人标记
            if speaker:
                speaker_marker = f"【{speaker}】\n\n" if not rewritten.startswith("【") else ""
                if speaker_marker and not rewritten.startswith(speaker_marker):
                    rewritten = speaker_marker + rewritten
            
            result = rewritten.strip()
            
            # 记录输出结果
            log_chunks = self.config.get("logging", {}).get("log_chunks", True)
            if self.logger and log_chunks:
                self.logger.info(f"✅ LLM 生成完成 ({len(result)} 字符)")
                self.logger.info(f"📤 输出结果:")
                self.logger.info(f"{'-'*80}")
                # 记录完整输出结果（不截断）
                self.logger.info(result)
                self.logger.info(f"{'-'*80}")
                self.logger.info(f"{'='*80}\n")
            
            return result
        
        except Exception as e:
            error_msg = f"重写切片 {chunk_idx + 1}/{total_chunks} 时出错: {str(e)}"
            if self.logger:
                self.logger.error(error_msg)
                self.logger.exception("详细错误信息:")
            else:
                print(error_msg)
            # 出错时返回原文
            return text
    
    def _build_prompt(self, text: str, speaker: Optional[str], chunk_idx: int, total_chunks: int) -> str:
        """构建重写提示词"""
        context_info = ""
        if total_chunks > 1:
            context_info = f"\n\n注意：这是第 {chunk_idx + 1} 部分，共 {total_chunks} 部分。请保持与前后文的连贯性。"
        
        speaker_info = ""
        if speaker:
            speaker_info = f"\n\n讲话人：{speaker}"
        
        if self.rewrite_prompt:
            prompt = self.rewrite_prompt.format(
                text=text,
                speaker_info=speaker_info,
                context_info=context_info
            )
        else:
            prompt = f"""请将以下语音识别文本进行专业整理和重写，要求：

1. **逐句纠错**：修正错别字、语法错误、识别错误
2. **语义补全**：补全不完整的句子，确保语义完整
3. **专业术语纠正**：纠正专业术语、人名、地名、机构名
4. **去口语化**：将口语化表达转换为正式书面语
5. **逻辑优化**：优化句子结构，使表达更清晰流畅
6. **保持原意**：不改变原讲话人的核心内容和观点
7. **保持结构**：保留段落结构和讲话人信息（如果有）{speaker_info}
8. **完整输出**：**必须完整输出所有内容，不要遗漏任何句子或段落，不要截断内容**

原始文本：
{text}{context_info}

**重要提示**：
- 这是文本的一部分，请完整处理并输出所有内容
- 如果这是多部分文本的一部分，请保持与前后文的连贯性
- 必须输出完整的整理结果，不要因为长度限制而截断

请输出整理后的文本（直接输出文本，不要添加额外说明）："""
        
        return prompt
    
    def _get_system_prompt(self) -> str:
        """获取系统提示词"""
        return """你是一位专业的文本整理专家，擅长将语音识别文本转换为高质量、正式、结构清晰的书面文稿。
你的任务是：
- 准确理解原文内容
- 修正所有错误和不规范之处
- 保持原意不变
- 输出正式、流畅的书面语
- **必须完整输出所有内容，不要遗漏任何部分，不要截断内容**"""
    
    def _merge_chunks(self, chunks: List[str]) -> str:
        """合并重写后的切片，智能去重重叠部分"""
        if not chunks:
            return ""
        
        if len(chunks) == 1:
            return chunks[0]
        
        merged = []
        prev_speaker = None
        prev_content = ""  # 用于检测重叠
        
        for i, chunk in enumerate(chunks):
            chunk = chunk.strip()
            if not chunk:
                continue
            
            lines = chunk.split('\n')
            first_line = lines[0] if lines else ""
            
            # 检查是否是讲话人标记
            if first_line.startswith('【') and first_line.endswith('】'):
                current_speaker = first_line
                content = '\n'.join(lines[1:]).strip()
                
                if current_speaker == prev_speaker:
                    # 相同讲话人，需要去重
                    if content:
                        # 检查是否有重叠
                        deduped_content = self._deduplicate_overlap(prev_content, content)
                        if deduped_content:
                            merged.append(deduped_content)
                            prev_content = content
                else:
                    # 新讲话人
                    if prev_speaker:
                        # 结束上一个讲话人的内容
                        merged.append("")
                    merged.append(chunk)
                    prev_speaker = current_speaker
                    prev_content = content
            else:
                # 没有讲话人标记的内容
                if prev_speaker:
                    # 如果之前有讲话人，这是该讲话人的内容
                    deduped_content = self._deduplicate_overlap(prev_content, chunk)
                    if deduped_content:
                        merged.append(deduped_content)
                        prev_content = chunk
                else:
                    # 没有讲话人的普通内容
                    deduped_content = self._deduplicate_overlap(prev_content, chunk)
                    if deduped_content:
                        merged.append(deduped_content)
                        prev_content = chunk
                    prev_speaker = None
        
        return '\n\n'.join(merged)
    
    def _deduplicate_overlap(self, prev_text: str, current_text: str) -> str:
        """去重重叠内容"""
        if not prev_text or not current_text:
            return current_text
        
        # 检查当前文本开头是否与上一个文本结尾重叠
        # 尝试找到重叠点（从后往前匹配）
        overlap_threshold = 50  # 最小重叠字符数
        
        # 从上一个文本的末尾和当前文本的开头寻找重叠
        prev_suffix = prev_text[-200:] if len(prev_text) > 200 else prev_text
        current_prefix = current_text[:200] if len(current_text) > 200 else current_text
        
        # 寻找最长公共后缀-前缀
        max_overlap = 0
        for i in range(min(len(prev_suffix), len(current_prefix)), overlap_threshold - 1, -1):
            if prev_suffix[-i:] == current_prefix[:i]:
                max_overlap = i
                break
        
        if max_overlap >= overlap_threshold:
            # 有重叠，去除重叠部分
            return current_text[max_overlap:].strip()
        
        return current_text
    
    def _init_logger(self, logging_config: Dict) -> Optional[logging.Logger]:
        """初始化日志记录器"""
        if not logging_config.get("enabled", False):
            return None
        
        logger = logging.getLogger("ScriptRefine.Rewriter")
        logger.setLevel(getattr(logging, logging_config.get("level", "DEBUG"), logging.DEBUG))
        
        # 清除已有的处理器
        logger.handlers.clear()
        
        # 日志格式
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # 控制台输出
        if logging_config.get("output_to_console", True):
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)
        
        # 文件输出
        if logging_config.get("output_to_file", True):
            log_dir = logging_config.get("log_dir", "./logs")
            os.makedirs(log_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file_template = logging_config.get("log_file_template", "process_{timestamp}.log")
            log_filename = log_file_template.format(timestamp=timestamp)
            log_filepath = os.path.join(log_dir, log_filename)
            
            file_handler = logging.FileHandler(log_filepath, encoding='utf-8')
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
            
            logger.info(f"📝 日志文件: {log_filepath}")
        
        return logger
    
    def _remove_reasoning_markers(self, text: str) -> str:
        """移除 LLM 推理过程标记"""
        import re
        # 移除各种推理标记（支持多行）
        patterns = [
            r'<think>.*?</think>',  # <think>...</think>
            r'<think>.*?</think>',  # <think>...</think>
            r'<reasoning>.*?</reasoning>',  # <reasoning>...</reasoning>
            r'<thought>.*?</thought>',  # <thought>...</thought>
            r'<internal>.*?</internal>',  # <internal>...</internal>
            r'<scratchpad>.*?</scratchpad>',  # <scratchpad>...</scratchpad>
            r'<analysis>.*?</analysis>',  # <analysis>...</analysis>
            r'<reflection>.*?</reflection>',  # <reflection>...</reflection>
        ]
        
        for pattern in patterns:
            # 使用 DOTALL 标志使 . 匹配换行符，IGNORECASE 忽略大小写
            text = re.sub(pattern, '', text, flags=re.DOTALL | re.IGNORECASE)
        
        # 清理可能留下的多余空行
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        return text
    
    def _load_prompt(self, prompt_path: str) -> Optional[str]:
        """加载提示词模板"""
        if not prompt_path:
            return None
        
        # 尝试从 prompts 目录加载
        if not os.path.isabs(prompt_path):
            prompt_path = os.path.join(os.path.dirname(__file__), "..", "..", prompt_path)
        
        if os.path.exists(prompt_path):
            try:
                with open(prompt_path, 'r', encoding='utf-8') as f:
                    return f.read()
            except Exception as e:
                error_msg = f"加载提示词失败: {str(e)}"
                if self.logger:
                    self.logger.warning(error_msg)
                else:
                    print(error_msg)
        
        return None

