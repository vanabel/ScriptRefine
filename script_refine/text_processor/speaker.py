"""讲话人识别模块"""

import re
from typing import Optional, Dict, List


class SpeakerDetector:
    """讲话人检测器"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.enabled = config.get("enabled", True)
        self.patterns = config.get("patterns", [
            r"【.*?】",
            r".*?:",
            r"^[A-Z].*?:",
        ])
        self._compiled_patterns = [re.compile(p) for p in self.patterns]
    
    def detect(self, text: str) -> Optional[str]:
        """
        检测文本中的讲话人
        
        Args:
            text: 输入文本
            
        Returns:
            讲话人名称，如果未检测到则返回 None
        """
        if not self.enabled or not text:
            return None
        
        # 检查第一行
        first_line = text.split('\n')[0].strip()
        
        for pattern in self._compiled_patterns:
            match = pattern.match(first_line)
            if match:
                speaker = match.group(0).strip()
                # 清理格式
                speaker = speaker.strip('【】:：')
                if speaker and len(speaker) < 50:  # 合理的讲话人名称长度
                    return speaker
        
        return None
    
    def extract_all_speakers(self, text: str) -> List[str]:
        """
        提取文本中所有讲话人
        
        Args:
            text: 输入文本
            
        Returns:
            讲话人列表
        """
        speakers = set()
        lines = text.split('\n')
        
        for line in lines:
            speaker = self.detect(line)
            if speaker:
                speakers.add(speaker)
        
        return sorted(list(speakers))
    
    def format_speaker(self, speaker: str) -> str:
        """
        格式化讲话人标记
        
        Args:
            speaker: 讲话人名称
            
        Returns:
            格式化后的标记，如 "【主持人】"
        """
        if not speaker:
            return ""
        
        # 如果已经有标记，直接返回
        if speaker.startswith('【') and speaker.endswith('】'):
            return speaker
        
        return f"【{speaker}】"

