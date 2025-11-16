"""LLM 基础接口"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional


class BaseLLM(ABC):
    """LLM 基础抽象类"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.temperature = config.get("temperature", 0.3)
        self.max_tokens = config.get("max_tokens", 4000)
    
    @abstractmethod
    def generate(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> str:
        """
        生成文本
        
        Args:
            prompt: 用户提示词
            system_prompt: 系统提示词（可选）
            **kwargs: 其他参数
            
        Returns:
            生成的文本
        """
        pass
    
    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """
        计算文本的 token 数量
        
        Args:
            text: 输入文本
            
        Returns:
            token 数量
        """
        pass
    
    def generate_stream(self, prompt: str, system_prompt: Optional[str] = None, **kwargs):
        """
        流式生成文本（可选实现）
        
        Args:
            prompt: 用户提示词
            system_prompt: 系统提示词（可选）
            **kwargs: 其他参数
            
        Yields:
            生成的文本片段
        """
        # 默认实现：非流式
        result = self.generate(prompt, system_prompt, **kwargs)
        yield result

