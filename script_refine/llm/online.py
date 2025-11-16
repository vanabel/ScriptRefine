"""在线 LLM API 实现"""

import os
from typing import Optional, Dict
from .base import BaseLLM


class OnlineLLM(BaseLLM):
    """在线 LLM API 封装"""
    
    def __init__(self, config: Dict):
        super().__init__(config)
        self.provider = config.get("provider", "openai")
        self.model = config.get("model", "gpt-4-turbo-preview")
        # 优先使用配置中的 api_key，否则从环境变量获取
        self.api_key = config.get("api_key") or self._get_api_key()
        if not self.api_key:
            raise ValueError(f"未找到 {self.provider} 的 API 密钥，请在配置文件中设置或设置环境变量")
        self.base_url = config.get("base_url")
        self._client = None
        self._init_client()
    
    def _get_api_key(self) -> str:
        """从环境变量获取 API 密钥"""
        key_map = {
            "openai": "OPENAI_API_KEY",
            "deepseek": "DEEPSEEK_API_KEY",
            "qianwen": "DASHSCOPE_API_KEY",
            "zhipu": "ZHIPUAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "siliconflow": "SILICONFLOW_API_KEY",
        }
        env_key = key_map.get(self.provider, "OPENAI_API_KEY")
        return os.getenv(env_key, "")
    
    def _init_client(self):
        """初始化 API 客户端"""
        if self.provider == "openai":
            try:
                from openai import OpenAI
                # OpenAI 支持自定义 base_url（用于代理或其他兼容服务）
                client_kwargs = {"api_key": self.api_key}
                if self.base_url:
                    client_kwargs["base_url"] = self.base_url
                self._client = OpenAI(**client_kwargs)
            except ImportError:
                raise ImportError("请安装 openai: pip install openai")
        
        elif self.provider == "deepseek":
            try:
                from openai import OpenAI
                self._client = OpenAI(
                    api_key=self.api_key,
                    base_url="https://api.deepseek.com/v1"
                )
            except ImportError:
                raise ImportError("请安装 openai: pip install openai")
        
        elif self.provider == "siliconflow":
            try:
                from openai import OpenAI
                # SiliconFlow 兼容 OpenAI API
                # 如果 base_url 未设置或为空，使用默认值
                if not self.base_url or self.base_url.strip() == "":
                    base_url = "https://api.siliconflow.cn/v1"
                else:
                    base_url = self.base_url
                    # 确保 URL 包含 /v1 路径
                    if not base_url.endswith("/v1"):
                        base_url = base_url.rstrip("/") + "/v1"
                self._client = OpenAI(
                    api_key=self.api_key,
                    base_url=base_url
                )
            except ImportError:
                raise ImportError("请安装 openai: pip install openai")
        
        elif self.provider == "qianwen":
            try:
                import dashscope
                dashscope.api_key = self.api_key
                self._client = dashscope
            except ImportError:
                raise ImportError("请安装 dashscope: pip install dashscope")
        
        elif self.provider == "zhipu":
            try:
                import zhipuai
                self._client = zhipuai.ZhipuAI(api_key=self.api_key)
            except ImportError:
                raise ImportError("请安装 zhipuai: pip install zhipuai")
        
        elif self.provider == "anthropic":
            try:
                from anthropic import Anthropic
                self._client = Anthropic(api_key=self.api_key)
            except ImportError:
                raise ImportError("请安装 anthropic: pip install anthropic")
        
        else:
            raise ValueError(f"不支持的在线模型提供商: {self.provider}")
    
    def generate(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> str:
        """生成文本"""
        if self.provider in ["openai", "deepseek", "siliconflow"]:
            return self._generate_openai(prompt, system_prompt, **kwargs)
        elif self.provider == "qianwen":
            return self._generate_qianwen(prompt, system_prompt, **kwargs)
        elif self.provider == "zhipu":
            return self._generate_zhipu(prompt, system_prompt, **kwargs)
        elif self.provider == "anthropic":
            return self._generate_anthropic(prompt, system_prompt, **kwargs)
        else:
            raise ValueError(f"不支持的提供商: {self.provider}")
    
    def _generate_openai(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> str:
        """OpenAI/DeepSeek API"""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        response = self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=kwargs.get("temperature", self.temperature),
            max_tokens=kwargs.get("max_tokens", self.max_tokens),
        )
        return response.choices[0].message.content
    
    def _generate_qianwen(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> str:
        """阿里通义 API"""
        from dashscope import Generation
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        response = Generation.call(
            model=self.model,
            messages=messages,
            temperature=kwargs.get("temperature", self.temperature),
            max_tokens=kwargs.get("max_tokens", self.max_tokens),
        )
        
        if response.status_code == 200:
            return response.output.choices[0].message.content
        else:
            raise RuntimeError(f"通义 API 错误: {response.message}")
    
    def _generate_zhipu(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> str:
        """智谱 GLM API"""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        response = self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=kwargs.get("temperature", self.temperature),
            max_tokens=kwargs.get("max_tokens", self.max_tokens),
        )
        return response.choices[0].message.content
    
    def _generate_anthropic(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> str:
        """Anthropic Claude API"""
        messages = [{"role": "user", "content": prompt}]
        
        response = self._client.messages.create(
            model=self.model,
            messages=messages,
            system=system_prompt or "",
            temperature=kwargs.get("temperature", self.temperature),
            max_tokens=kwargs.get("max_tokens", self.max_tokens),
        )
        return response.content[0].text
    
    def count_tokens(self, text: str) -> int:
        """估算 token 数量（简单实现）"""
        # 简单估算：中文约 1.5 字符/token，英文约 4 字符/token
        chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        other_chars = len(text) - chinese_chars
        return int(chinese_chars / 1.5 + other_chars / 4)

