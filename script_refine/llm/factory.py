"""LLM 工厂类"""

from typing import Dict
from .base import BaseLLM
from .online import OnlineLLM
from .local import LocalLLM


def create_llm(config: Dict) -> BaseLLM:
    """
    根据配置创建 LLM 实例
    
    Args:
        config: LLM 配置字典
        
    Returns:
        LLM 实例
    """
    llm_type = config.get("type", "online")
    
    if llm_type == "local":
        return LocalLLM(config.get("local", {}))
    elif llm_type == "online":
        return OnlineLLM(config.get("online", {}))
    else:
        raise ValueError(f"不支持的 LLM 类型: {llm_type}")

