"""语稿智能整理系统主模块"""

import os
import yaml
from typing import Optional, Dict
from pathlib import Path
from dotenv import load_dotenv

from .llm import create_llm
from .text_processor import TextCleaner
from .rewriter import TextRewriter
from .summarizer import MeetingSummarizer
from .output import DocumentExporter


class ScriptRefiner:
    """语稿智能整理系统主类"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化系统
        
        Args:
            config_path: 配置文件路径，如果为 None 则使用默认配置
        """
        # 加载环境变量
        load_dotenv()
        
        # 加载配置
        self.config = self._load_config(config_path)
        
        # 初始化组件
        self.llm = create_llm(self.config.get("llm", {}))
        text_processing_config = self.config.get("text_processing", {})
        self.cleaner = TextCleaner(text_processing_config.get("cleaning", {}))
        chunking_config = text_processing_config.get("chunking", {})
        # 将 speaker_detection 配置添加到 chunking_config 中
        chunking_config["speaker_detection"] = text_processing_config.get("speaker_detection", {})
        self.rewriter = TextRewriter(self.llm, {
            "chunking": chunking_config,
            "prompts": self.config.get("prompts", {}),
            "logging": self.config.get("logging", {}),
            "temperature": self.config.get("llm", {}).get("online", {}).get("temperature", 0.3),
            "max_tokens": self.config.get("llm", {}).get("online", {}).get("max_tokens", 4000),
        })
        self.summarizer = MeetingSummarizer(self.llm, {
            "prompts": self.config.get("prompts", {}),
            "output": self.config.get("output", {}),
            "logging": self.config.get("logging", {}),
            "temperature": self.config.get("llm", {}).get("online", {}).get("temperature", 0.3),
            "max_tokens": self.config.get("llm", {}).get("online", {}).get("max_tokens", 4000),
        })
        self.exporter = DocumentExporter(self.config.get("output", {}))

    def _load_config(self, config_path: Optional[str]) -> Dict:
        """
        按优先级加载配置文件：
        1. 显式传入的 config_path
        2. 项目根目录下的 config_local.yaml
        3. 项目根目录下的 config.yaml（兼容旧版本）
        4. 项目根目录下的 config.yaml.example（仅作为示例 / 回退）
        """
        # 如果显式传入了路径，优先使用
        candidates = []
        if config_path:
            candidates.append(config_path)

        root_dir = os.path.join(os.path.dirname(__file__), "..")
        candidates.extend([
            os.path.join(root_dir, "config_local.yaml"),
            os.path.join(root_dir, "config.yaml"),          # 兼容旧项目
            os.path.join(root_dir, "config.yaml.example"),  # 示例 / 回退
        ])

        for path in candidates:
            if path and os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    cfg = yaml.safe_load(f)
                print(f"📂 使用配置文件: {path}")
                return cfg or {}

        raise FileNotFoundError(
            "未找到配置文件，请创建 config_local.yaml，或提供 --config 参数，"
            "或者复制 config.yaml.example 为 config_local.yaml 后再修改。"
        )
    
    def process(
        self,
        input_path: str,
        output_mode: str = "full",
        output_dir: Optional[str] = None,
        show_progress: bool = True
    ) -> Dict[str, str]:
        """
        处理文本文件
        
        Args:
            input_path: 输入文件路径
            output_mode: 输出模式，"full" 为完整版，"summary" 为会议纪要，"both" 为两者
            output_dir: 输出目录，如果为 None 则使用配置中的目录
            show_progress: 是否显示进度条
            
        Returns:
            导出文件路径字典
        """
        # 读取输入文件
        print(f"📖 读取文件: {input_path}")
        text = self._read_input(input_path)
        
        if not text:
            raise ValueError("输入文件为空")
        
        print(f"📊 原始文本长度: {len(text)} 字符")
        
        # 文本清洗
        print("🧹 开始文本清洗...")
        cleaned_text = self.cleaner.clean(text)
        print(f"✅ 清洗完成，长度: {len(cleaned_text)} 字符")
        
        # 根据模式处理
        results = {}
        rewritten_text = None
        
        if output_mode in ["full", "both"]:
            print("✍️ 开始文本重写...")
            rewritten_text = self.rewriter.rewrite(cleaned_text, show_progress=show_progress)
            print("✅ 重写完成")
            
            # 导出完整版
            filename_template = self.config.get("output", {}).get("full_version", {}).get(
                "filename_template", "完整版_{timestamp}.md"
            )
            exported = self.exporter.export(
                rewritten_text,
                filename_template,
                mode="full"
            )
            results.update(exported)
            print(f"📄 完整版已导出: {list(exported.values())}")
        
        if output_mode in ["summary", "both"]:
            print("📋 开始生成会议纪要...")
            # 使用重写后的文本（如果有）或清洗后的文本
            source_text = rewritten_text if rewritten_text else cleaned_text
            summary_text = self.summarizer.summarize(source_text)
            print("✅ 会议纪要生成完成")
            
            # 导出会议纪要
            filename_template = self.config.get("output", {}).get("summary_version", {}).get(
                "filename_template", "会议纪要_{timestamp}.md"
            )
            exported = self.exporter.export(
                summary_text,
                filename_template,
                mode="summary"
            )
            results.update({f"summary_{k}": v for k, v in exported.items()})
            print(f"📄 会议纪要已导出: {list(exported.values())}")
        
        return results
    
    def _read_input(self, input_path: str) -> str:
        """读取输入文件"""
        path = Path(input_path)
        
        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {input_path}")
        
        # 根据扩展名选择读取方式
        suffix = path.suffix.lower()
        
        if suffix in [".txt", ".md"]:
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        else:
            # 尝试作为文本文件读取
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    return f.read()
            except Exception as e:
                raise ValueError(f"无法读取文件: {str(e)}")
    
    def process_text(
        self,
        text: str,
        output_mode: str = "full",
        show_progress: bool = True
    ) -> Dict[str, str]:
        """
        直接处理文本（不读取文件）
        
        Args:
            text: 输入文本
            output_mode: 输出模式
            show_progress: 是否显示进度条
            
        Returns:
            处理后的文本字典 {"full": "...", "summary": "..."}
        """
        if not text:
            raise ValueError("输入文本为空")
        
        print(f"📊 原始文本长度: {len(text)} 字符")
        
        # 文本清洗
        print("🧹 开始文本清洗...")
        cleaned_text = self.cleaner.clean(text)
        print(f"✅ 清洗完成，长度: {len(cleaned_text)} 字符")
        
        results = {}
        
        if output_mode in ["full", "both"]:
            print("✍️ 开始文本重写...")
            rewritten_text = self.rewriter.rewrite(cleaned_text, show_progress=show_progress)
            print("✅ 重写完成")
            results["full"] = rewritten_text
        
        if output_mode in ["summary", "both"]:
            print("📋 开始生成会议纪要...")
            source_text = rewritten_text if output_mode == "both" else cleaned_text
            summary_text = self.summarizer.summarize(source_text)
            print("✅ 会议纪要生成完成")
            results["summary"] = summary_text
        
        return results

