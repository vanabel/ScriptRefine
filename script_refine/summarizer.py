"""会议纪要生成模块"""

import os
import logging
from datetime import datetime
from typing import Dict, Optional
from .llm import BaseLLM


class MeetingSummarizer:
    """会议纪要生成器"""
    
    def __init__(self, llm: BaseLLM, config: Dict):
        self.llm = llm
        self.config = config
        self.summary_prompt = self._load_prompt(config.get("prompts", {}).get("summary_prompt", ""))
        self.structure = config.get("output", {}).get("summary_version", {}).get("structure", [])
        self.logger = self._init_logger(config.get("logging", {}))
    
    def summarize(self, text: str) -> str:
        """
        生成会议纪要
        
        Args:
            text: 完整文本（可以是原始文本或重写后的文本）
            
        Returns:
            会议纪要
        """
        # 构建提示词
        prompt = self._build_prompt(text)
        system_prompt = self._get_system_prompt()
        
        # 记录信息
        if self.logger:
            self.logger.info(f"\n{'='*80}")
            self.logger.info(f"📋 生成会议纪要")
            self.logger.info(f"{'='*80}")
            self.logger.info(f"📝 输入文本长度: {len(text)} 字符")
            self.logger.info(f"💬 提示词 ({len(prompt)} 字符):")
            self.logger.info(f"{'-'*80}")
            # 记录完整提示词（不截断）
            self.logger.info(prompt)
            self.logger.info(f"{'-'*80}")
        
        # 调用 LLM
        try:
            if self.logger:
                self.logger.info("⏳ 正在调用 LLM 生成会议纪要...")
            
            summary = self.llm.generate(
                prompt,
                system_prompt=system_prompt,
                temperature=self.config.get("temperature", 0.3),
                max_tokens=self.config.get("max_tokens", 4000),
            )
            
            # 移除 LLM 推理标记
            summary = self._remove_reasoning_markers(summary)
            
            result = summary.strip()
            
            if self.logger:
                self.logger.info(f"✅ 会议纪要生成完成 ({len(result)} 字符)")
                self.logger.info(f"📤 会议纪要内容:")
                self.logger.info(f"{'-'*80}")
                self.logger.info(result)
                self.logger.info(f"{'-'*80}")
                self.logger.info(f"{'='*80}\n")
            
            return result
        
        except Exception as e:
            error_msg = f"生成会议纪要时出错: {str(e)}"
            if self.logger:
                self.logger.error(error_msg)
                self.logger.exception("详细错误信息:")
            else:
                print(error_msg)
            return ""
    
    def _build_prompt(self, text: str) -> str:
        """构建摘要提示词"""
        structure_text = ""
        if self.structure:
            structure_text = "\n\n请按照以下结构组织内容：\n"
            for i, section in enumerate(self.structure, 1):
                structure_text += f"{i}. {section}\n"
        
        if self.summary_prompt:
            prompt = self.summary_prompt.format(
                text=text,
                structure=structure_text
            )
        else:
            prompt = f"""请根据以下会议记录，生成一份结构化的会议纪要。

要求：
1. **提取核心内容**：保留重要观点、决策、行动计划
2. **结构化组织**：按照逻辑结构组织内容
3. **简洁明了**：去除冗余信息，突出要点
4. **保持准确性**：不添加原文没有的内容{structure_text}

会议记录：
{text}

请输出会议纪要（直接输出，不要添加额外说明）："""
        
        return prompt
    
    def _get_system_prompt(self) -> str:
        """获取系统提示词"""
        return """你是一位专业的会议纪要撰写专家，擅长从会议记录中提取关键信息，生成结构清晰、内容准确的会议纪要。
你的任务是：
- 准确提取核心观点和决策
- 按照逻辑结构组织内容
- 保持信息的准确性和完整性
- 输出正式、专业的会议纪要"""
    
    def _init_logger(self, logging_config: Dict) -> Optional[logging.Logger]:
        """初始化日志记录器"""
        if not logging_config.get("enabled", False):
            return None
        
        logger = logging.getLogger("ScriptRefine.Summarizer")
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

