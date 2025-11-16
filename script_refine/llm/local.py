"""本地 LLM 实现"""

from typing import Optional, Dict
import torch
from .base import BaseLLM


class LocalLLM(BaseLLM):
    """本地 LLM 封装"""
    
    def __init__(self, config: Dict):
        super().__init__(config)
        self.provider = config.get("provider", "qwen2.5")
        self.model_path = config.get("model_path", "")
        self.model_name = config.get("model_name", "")  # Ollama 模型名称
        self.device = config.get("device", "auto")
        self.max_length = config.get("max_length", 4096)
        self.ollama_base_url = config.get("ollama_base_url", "http://localhost:11434")
        self._model = None
        self._tokenizer = None
        self._use_ollama = False
        self._init_model()
    
    def _init_model(self):
        """初始化本地模型"""
        # 检查是否使用 Ollama
        if self.provider == "ollama" or self.model_name:
            self._use_ollama = True
            if not self.model_name:
                # 默认使用 qwen3:8b
                self.model_name = "qwen3:8b"
            print(f"使用 Ollama 模型: {self.model_name}")
            # 测试连接
            try:
                import requests
                response = requests.get(f"{self.ollama_base_url}/api/tags", timeout=5)
                if response.status_code == 200:
                    print("✅ Ollama 连接成功")
                else:
                    raise RuntimeError(f"Ollama API 响应错误: {response.status_code}")
            except ImportError:
                raise ImportError("使用 Ollama 需要安装 requests: pip install requests")
            except Exception as e:
                raise RuntimeError(f"无法连接到 Ollama: {str(e)}，请确保 Ollama 服务正在运行")
            return
        
        # 使用 transformers 加载模型
        if self.device == "auto":
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer
            
            if not self.model_path:
                # 默认模型映射
                model_map = {
                    "qwen2.5": "Qwen/Qwen2.5-7B-Instruct",
                    "llama": "meta-llama/Llama-2-7b-chat-hf",
                    "chatglm": "THUDM/chatglm3-6b",
                }
                self.model_path = model_map.get(self.provider, model_map["qwen2.5"])
            
            print(f"正在加载模型: {self.model_path} (设备: {self.device})")
            self._tokenizer = AutoTokenizer.from_pretrained(
                self.model_path,
                trust_remote_code=True
            )
            self._model = AutoModelForCausalLM.from_pretrained(
                self.model_path,
                trust_remote_code=True,
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                device_map=self.device if self.device == "cuda" else None,
            )
            
            if self.device == "cpu":
                self._model = self._model.to(self.device)
            
            self._model.eval()
            print("模型加载完成")
            
        except ImportError:
            raise ImportError("请安装 transformers: pip install transformers torch")
        except Exception as e:
            raise RuntimeError(f"模型加载失败: {str(e)}")
    
    def generate(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> str:
        """生成文本"""
        # 使用 Ollama
        if self._use_ollama:
            return self._generate_ollama(prompt, system_prompt, **kwargs)
        
        # 使用 transformers
        if not self._model or not self._tokenizer:
            raise RuntimeError("模型未初始化")
        
        # 构建完整提示词
        full_prompt = prompt
        if system_prompt:
            if self.provider == "qwen2.5":
                full_prompt = f"<|im_start|>system\n{system_prompt}<|im_end|>\n<|im_start|>user\n{prompt}<|im_end|>\n<|im_start|>assistant\n"
            elif self.provider == "chatglm":
                full_prompt = f"[Round 1]\n\n问：{system_prompt}\n{prompt}\n\n答："
            else:
                full_prompt = f"{system_prompt}\n\n{prompt}\n\n"
        
        # Tokenize
        inputs = self._tokenizer(
            full_prompt,
            return_tensors="pt",
            truncation=True,
            max_length=self.max_length
        ).to(self.device)
        
        # 生成
        with torch.no_grad():
            outputs = self._model.generate(
                **inputs,
                max_new_tokens=kwargs.get("max_tokens", self.max_tokens),
                temperature=kwargs.get("temperature", self.temperature),
                do_sample=True,
                pad_token_id=self._tokenizer.eos_token_id,
            )
        
        # Decode
        generated_text = self._tokenizer.decode(
            outputs[0][inputs["input_ids"].shape[1]:],
            skip_special_tokens=True
        )
        
        return generated_text.strip()
    
    def _generate_ollama(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> str:
        """使用 Ollama 生成文本"""
        try:
            import requests
            
            # 构建消息
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            # 调用 Ollama API
            payload = {
                "model": self.model_name,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": kwargs.get("temperature", self.temperature),
                    "num_predict": kwargs.get("max_tokens", self.max_tokens),
                }
            }
            
            response = requests.post(
                f"{self.ollama_base_url}/api/chat",
                json=payload,
                timeout=300  # 5分钟超时
            )
            
            if response.status_code != 200:
                raise RuntimeError(f"Ollama API 错误: {response.status_code} - {response.text}")
            
            result = response.json()
            return result.get("message", {}).get("content", "").strip()
        
        except ImportError:
            raise ImportError("使用 Ollama 需要安装 requests: pip install requests")
        except Exception as e:
            raise RuntimeError(f"Ollama 生成失败: {str(e)}")
    
    def count_tokens(self, text: str) -> int:
        """计算 token 数量"""
        if self._use_ollama:
            # Ollama 使用简单估算
            chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
            other_chars = len(text) - chinese_chars
            return int(chinese_chars / 1.5 + other_chars / 4)
        
        if not self._tokenizer:
            # 如果没有 tokenizer，使用简单估算
            chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
            other_chars = len(text) - chinese_chars
            return int(chinese_chars / 1.5 + other_chars / 4)
        
        return len(self._tokenizer.encode(text))

