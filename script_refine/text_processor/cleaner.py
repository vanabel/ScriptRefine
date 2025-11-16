"""文本清洗模块"""

import re
from typing import List, Dict


class TextCleaner:
    """文本清洗器"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.remove_filler_words = config.get("remove_filler_words", True)
        self.merge_broken_sentences = config.get("merge_broken_sentences", True)
        self.remove_duplicates = config.get("remove_duplicates", True)
        self.fix_encoding = config.get("fix_encoding", True)
        self.remove_llm_reasoning = config.get("remove_llm_reasoning", True)
        
        # 常见语气词和口头禅
        self.filler_words = [
            "嗯", "呃", "那个", "这个", "就是", "然后", "所以", "但是",
            "啊", "哦", "呀", "吧", "呢", "嘛", "哈", "额",
            "其实", "基本上", "大概", "可能", "应该", "好像",
            "怎么说呢", "怎么说", "就是那个", "这个那个"
        ]
    
    def clean(self, text: str) -> str:
        """
        清洗文本
        
        Args:
            text: 原始文本
            
        Returns:
            清洗后的文本
        """
        if not text:
            return ""
        
        # 修复编码
        if self.fix_encoding:
            text = self._fix_encoding(text)
        
        # 移除 LLM 推理标记（如 <think>...</think>, <think>...</think>）
        if self.remove_llm_reasoning:
            text = self._remove_llm_reasoning_markers(text)
        
        # 移除 ASR 冗余符号
        text = self._remove_asr_artifacts(text)
        
        # 合并断裂句子
        if self.merge_broken_sentences:
            text = self._merge_broken_sentences(text)
        
        # 去除重复词
        if self.remove_duplicates:
            text = self._remove_duplicates(text)
        
        # 去除语气词
        if self.remove_filler_words:
            text = self._remove_filler_words(text)
        
        # 规范化标点
        text = self._normalize_punctuation(text)
        
        # 规范化空白
        text = self._normalize_whitespace(text)
        
        return text.strip()
    
    def _fix_encoding(self, text: str) -> str:
        """修复常见编码问题"""
        # 替换常见乱码字符
        replacements = {
            "锘?": "",
            "鈥?": "",
            "鈥?": "",
            "鈥?": "",
            "鈥?": "",
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        return text
    
    def _remove_llm_reasoning_markers(self, text: str) -> str:
        """移除 LLM 推理过程标记"""
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
    
    def _remove_asr_artifacts(self, text: str) -> str:
        """移除 ASR 识别产生的冗余符号"""
        # 移除重复的标点
        text = re.sub(r'[。，、]{3,}', '。', text)
        text = re.sub(r'[！]{2,}', '！', text)
        text = re.sub(r'[？]{2,}', '？', text)
        text = re.sub(r'[，]{2,}', '，', text)
        
        # 移除时间戳标记（如 [00:01:23]）
        text = re.sub(r'\[\d{2}:\d{2}:\d{2}\]', '', text)
        text = re.sub(r'\(\d{2}:\d{2}:\d{2}\)', '', text)
        
        # 移除识别置信度标记（如 (0.95)）
        text = re.sub(r'\(0\.\d+\)', '', text)
        
        return text
    
    def _merge_broken_sentences(self, text: str) -> str:
        """合并断裂的句子"""
        # 如果句子以逗号结尾且下一句很短，可能是断句错误
        lines = text.split('\n')
        merged = []
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if not line:
                merged.append('')
                i += 1
                continue
            
            # 检查是否需要合并
            if i < len(lines) - 1:
                next_line = lines[i + 1].strip()
                # 如果当前行以逗号结尾，且下一行很短（可能是断句）
                if line.endswith('，') and len(next_line) < 20:
                    line = line + next_line
                    i += 1
            
            merged.append(line)
            i += 1
        
        return '\n'.join(merged)
    
    def _remove_duplicates(self, text: str) -> str:
        """去除重复的词和短语"""
        # 去除连续重复的词（如"很好很好" -> "很好"）
        text = re.sub(r'(.{2,10})\1{2,}', r'\1', text)
        
        # 去除重复的短句
        sentences = re.split(r'[。！？\n]', text)
        seen = set()
        cleaned_sentences = []
        for sent in sentences:
            sent = sent.strip()
            if sent and sent not in seen:
                seen.add(sent)
                cleaned_sentences.append(sent)
        
        return '。'.join(cleaned_sentences)
    
    def _remove_filler_words(self, text: str) -> str:
        """去除语气词和口头禅"""
        # 在句子开头和结尾去除
        for word in self.filler_words:
            # 开头
            text = re.sub(rf'^{re.escape(word)}[，。、\s]*', '', text, flags=re.MULTILINE)
            # 结尾
            text = re.sub(rf'[，。、\s]*{re.escape(word)}$', '', text, flags=re.MULTILINE)
            # 中间（保留标点）
            text = re.sub(rf'[，。、\s]+{re.escape(word)}[，。、\s]+', '，', text)
        
        return text
    
    def _normalize_punctuation(self, text: str) -> str:
        """规范化标点符号"""
        # 统一中文标点
        replacements = {
            '，': '，',
            '。': '。',
            '！': '！',
            '？': '？',
            '：': '：',
            '；': '；',
        }
        
        # 确保句子以标点结尾
        text = re.sub(r'([^。！？\n])(\n|$)', r'\1。\2', text)
        
        return text
    
    def _normalize_whitespace(self, text: str) -> str:
        """规范化空白字符"""
        # 多个空格合并为一个
        text = re.sub(r' +', ' ', text)
        # 多个换行合并为最多两个
        text = re.sub(r'\n{3,}', '\n\n', text)
        # 移除行首行尾空格
        lines = [line.strip() for line in text.split('\n')]
        return '\n'.join(lines)

