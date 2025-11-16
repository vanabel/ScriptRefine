"""文本切片模块"""

from typing import List, Dict, Tuple
import re
from .speaker import SpeakerDetector

# 尝试导入 jieba 用于中文分词（可选）
try:
    import jieba
    JIEBA_AVAILABLE = True
except ImportError:
    JIEBA_AVAILABLE = False


class TextChunker:
    """文本切片器"""
    
    def __init__(self, config: Dict, llm=None):
        self.config = config
        self.max_tokens = config.get("max_tokens", 3000)
        self.overlap = config.get("overlap", 500)  # 增加默认重叠
        self.min_chunk_size = config.get("min_chunk_size", 100)
        self.preserve_speakers = config.get("preserve_speakers", True)
        self.use_chinese_segmentation = config.get("use_chinese_segmentation", True)  # 是否使用中文分词
        self.llm = llm  # 用于计算 token
        # 从 text_processing.speaker_detection 获取配置
        speaker_config = config.get("speaker_detection", {})
        self.speaker_detector = SpeakerDetector(speaker_config) if self.preserve_speakers else None
        
        # 初始化 jieba（如果可用）
        if JIEBA_AVAILABLE and self.use_chinese_segmentation:
            # 加载用户词典（如果有）
            jieba.initialize()
    
    def chunk(self, text: str) -> List[Dict[str, any]]:
        """
        将文本切片
        
        Args:
            text: 输入文本
            
        Returns:
            切片列表，每个切片包含：
            - text: 切片文本
            - start_idx: 原始文本中的起始位置
            - end_idx: 原始文本中的结束位置
            - speaker: 讲话人（如果有）
        """
        if not text:
            return []
        
        # 如果文本很短，直接返回
        token_count = self._count_tokens(text)
        if token_count <= self.max_tokens:
            return [{
                "text": text,
                "start_idx": 0,
                "end_idx": len(text),
                "speaker": self._detect_speaker(text) if self.speaker_detector else None,
            }]
        
        # 按段落分割
        paragraphs = self._split_into_paragraphs(text)
        
        # 构建切片
        chunks = []
        current_chunk = []
        current_tokens = 0
        
        for para in paragraphs:
            para_tokens = self._count_tokens(para["text"])
            para_speaker = para.get("speaker")
            
            # 如果单个段落就超过限制，需要进一步分割
            if para_tokens > self.max_tokens:
                # 先保存当前块
                if current_chunk:
                    chunks.append(self._create_chunk(current_chunk, text))
                    current_chunk = []
                    current_tokens = 0
                
                # 分割大段落
                sub_chunks = self._split_large_paragraph(para["text"], para["start_idx"])
                chunks.extend(sub_chunks)
                continue
            
            # 检查是否可以添加到当前块
            if current_tokens + para_tokens <= self.max_tokens:
                current_chunk.append(para)
                current_tokens += para_tokens
            else:
                # 保存当前块
                if current_chunk:
                    chunks.append(self._create_chunk(current_chunk, text))
                
                # 开始新块
                current_chunk = [para]
                current_tokens = para_tokens
        
        # 保存最后一个块
        if current_chunk:
            chunks.append(self._create_chunk(current_chunk, text))
        
        # 添加重叠
        if self.overlap > 0 and len(chunks) > 1:
            chunks = self._add_overlap(chunks, text)
        
        return chunks
    
    def _split_into_paragraphs(self, text: str) -> List[Dict]:
        """将文本分割为段落，处理没有良好分段的文本"""
        paragraphs = []
        lines = text.split('\n')
        
        current_para = []
        current_start = 0
        para_start_idx = 0
        
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            
            # 检测讲话人标记（作为段落边界）
            is_speaker_marker = False
            if self.speaker_detector and line_stripped:
                detected_speaker = self.speaker_detector.detect(line_stripped)
                if detected_speaker:
                    is_speaker_marker = True
            
            # 空行或讲话人标记作为段落边界
            if not line_stripped or is_speaker_marker:
                if current_para:
                    para_text = '\n'.join(current_para)
                    paragraphs.append({
                        "text": para_text,
                        "start_idx": para_start_idx,
                        "end_idx": para_start_idx + len(para_text),
                        "speaker": self._detect_speaker(para_text) if self.speaker_detector else None,
                    })
                    current_para = []
                
                # 如果是讲话人标记，开始新段落
                if is_speaker_marker:
                    para_start_idx = text.find(line, para_start_idx if paragraphs else 0)
                    current_para = [line]
                continue
            
            # 如果当前段落为空，记录起始位置
            if not current_para:
                para_start_idx = text.find(line, para_start_idx if paragraphs else 0)
            
            current_para.append(line)
        
        # 最后一个段落
        if current_para:
            para_text = '\n'.join(current_para)
            paragraphs.append({
                "text": para_text,
                "start_idx": para_start_idx,
                "end_idx": para_start_idx + len(para_text),
                "speaker": self._detect_speaker(para_text) if self.speaker_detector else None,
            })
        
        # 如果没有找到段落（文本没有空行且没有讲话人标记），按句子或长度分割
        if not paragraphs or (len(paragraphs) == 1 and len(paragraphs[0]["text"]) > 1000):
            paragraphs = self._split_continuous_text(text)
        
        return paragraphs
    
    def _split_continuous_text(self, text: str) -> List[Dict]:
        """分割没有明确段落边界的连续文本"""
        paragraphs = []
        import re
        
        # 方法1: 按讲话人标记分割
        speaker_patterns = [
            r'【[^】]+】',
            r'^[^：:]+[：:]',
        ]
        
        # 尝试按讲话人标记分割
        splits = []
        last_pos = 0
        
        for pattern in speaker_patterns:
            for match in re.finditer(pattern, text, re.MULTILINE):
                if match.start() > last_pos:
                    splits.append(match.start())
                last_pos = match.end()
        
        # 如果有分割点，按分割点分割
        if splits:
            splits = [0] + sorted(set(splits)) + [len(text)]
            for i in range(len(splits) - 1):
                para_text = text[splits[i]:splits[i+1]].strip()
                if para_text:
                    paragraphs.append({
                        "text": para_text,
                        "start_idx": splits[i],
                        "end_idx": splits[i+1],
                        "speaker": self._detect_speaker(para_text) if self.speaker_detector else None,
                    })
            return paragraphs
        
        # 方法2: 按句子和长度智能分割
        # 先按句号、问号、感叹号分割
        sentences = self._split_into_sentences(text)
        
        if not sentences:
            # 如果连句子都分不出来，按固定长度分割
            return self._split_by_length(text)
        
        # 按句子组合成段落，每个段落不超过一定长度
        current_para = []
        current_tokens = 0
        para_start = 0
        max_para_tokens = self.max_tokens // 2  # 段落最大 token 数
        
        for sent in sentences:
            sent_tokens = self._count_tokens(sent)
            
            # 如果单个句子就超过限制，单独成段
            if sent_tokens > max_para_tokens:
                # 先保存当前段落
                if current_para:
                    para_text = ''.join(current_para)
                    paragraphs.append({
                        "text": para_text,
                        "start_idx": para_start,
                        "end_idx": para_start + len(para_text),
                        "speaker": self._detect_speaker(para_text) if self.speaker_detector else None,
                    })
                    para_start += len(para_text)
                    current_para = []
                    current_tokens = 0
                
                # 长句子单独成段
                para_text = sent
                paragraphs.append({
                    "text": para_text,
                    "start_idx": para_start,
                    "end_idx": para_start + len(para_text),
                    "speaker": self._detect_speaker(para_text) if self.speaker_detector else None,
                })
                para_start += len(para_text)
            elif current_tokens + sent_tokens <= max_para_tokens:
                # 可以添加到当前段落
                current_para.append(sent)
                current_tokens += sent_tokens
            else:
                # 保存当前段落，开始新段落
                if current_para:
                    para_text = ''.join(current_para)
                    paragraphs.append({
                        "text": para_text,
                        "start_idx": para_start,
                        "end_idx": para_start + len(para_text),
                        "speaker": self._detect_speaker(para_text) if self.speaker_detector else None,
                    })
                    para_start += len(para_text)
                
                current_para = [sent]
                current_tokens = sent_tokens
        
        # 最后一个段落
        if current_para:
            para_text = ''.join(current_para)
            paragraphs.append({
                "text": para_text,
                "start_idx": para_start,
                "end_idx": para_start + len(para_text),
                "speaker": self._detect_speaker(para_text) if self.speaker_detector else None,
            })
        
        return paragraphs if paragraphs else [{
            "text": text,
            "start_idx": 0,
            "end_idx": len(text),
            "speaker": self._detect_speaker(text) if self.speaker_detector else None,
        }]
    
    def _split_by_length(self, text: str) -> List[Dict]:
        """按固定长度分割文本（最后手段），尽量在语义边界处断开"""
        paragraphs = []
        # 根据 token 限制估算字符数（中文更紧凑）
        chinese_ratio = sum(1 for c in text if '\u4e00' <= c <= '\u9fff') / max(len(text), 1)
        if chinese_ratio > 0.5:  # 主要是中文
            chunk_size = int(self.max_tokens * 1.3)  # 中文更紧凑
        else:
            chunk_size = int(self.max_tokens * 2)  # 混合文本
        
        start = 0
        
        while start < len(text):
            end = min(start + chunk_size, len(text))
            
            # 如果还没到文本末尾，尝试在语义边界处断开
            if end < len(text):
                # 优先在标点符号处断开
                for i in range(min(end - start, 100), 0, -1):
                    if text[start + i] in '。！？\n':
                        end = start + i + 1
                        break
                    elif text[start + i] in '，、；：':
                        # 逗号、分号作为次优选择
                        end = start + i + 1
                        break
                
                # 如果使用了 jieba，尝试在词边界处断开
                if JIEBA_AVAILABLE and self.use_chinese_segmentation:
                    chunk = text[start:end]
                    words = list(jieba.cut(chunk))
                    if words and len(words[-1]) < 5:  # 最后一个词很短，可能不完整
                        # 向前调整到词边界
                        word_end = len(chunk) - len(words[-1])
                        if word_end > chunk_size * 0.8:  # 至少保留 80% 的内容
                            end = start + word_end
            
            para_text = text[start:end].strip()
            if para_text:
                paragraphs.append({
                    "text": para_text,
                    "start_idx": start,
                    "end_idx": end,
                    "speaker": self._detect_speaker(para_text) if self.speaker_detector else None,
                })
            start = end
        
        return paragraphs if paragraphs else [{
            "text": text,
            "start_idx": 0,
            "end_idx": len(text),
            "speaker": self._detect_speaker(text) if self.speaker_detector else None,
        }]
    
    def _split_large_paragraph(self, text: str, start_idx: int) -> List[Dict]:
        """分割过大的段落"""
        chunks = []
        sentences = self._split_into_sentences(text)
        
        current_chunk = []
        current_tokens = 0
        
        for sent in sentences:
            sent_tokens = self._count_tokens(sent)
            
            if current_tokens + sent_tokens <= self.max_tokens:
                current_chunk.append(sent)
                current_tokens += sent_tokens
            else:
                if current_chunk:
                    chunk_text = ''.join(current_chunk)
                    chunks.append({
                        "text": chunk_text,
                        "start_idx": start_idx,
                        "end_idx": start_idx + len(chunk_text),
                        "speaker": self._detect_speaker(chunk_text) if self.speaker_detector else None,
                    })
                    start_idx += len(chunk_text)
                
                current_chunk = [sent]
                current_tokens = sent_tokens
        
        if current_chunk:
            chunk_text = ''.join(current_chunk)
            chunks.append({
                "text": chunk_text,
                "start_idx": start_idx,
                "end_idx": start_idx + len(chunk_text),
                "speaker": self._detect_speaker(chunk_text) if self.speaker_detector else None,
            })
        
        return chunks
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """将文本分割为句子，支持中文标点符号和边界"""
        # 中文标点符号：。！？，、；：；等
        # 先处理换行（可能是句子边界）
        text_normalized = re.sub(r'\n+', '。', text)
        
        # 按中文句号、问号、感叹号分割（全角和半角都支持）
        # 匹配：。！？.!?
        sentences = re.split(r'([。！？\.!?])', text_normalized)
        result = []
        for i in range(0, len(sentences) - 1, 2):
            if i + 1 < len(sentences):
                sent = sentences[i] + sentences[i + 1]
                sent = sent.strip()
                if sent:
                    result.append(sent)
        if len(sentences) % 2 == 1 and sentences[-1].strip():
            result.append(sentences[-1].strip())
        
        # 如果分割结果为空或太少，尝试更宽松的分割（按中文逗号、分号）
        if len(result) < 2:
            # 中文逗号、分号：，、；
            sentences = re.split(r'([，、；])', text)
            result = []
            for i in range(0, len(sentences) - 1, 2):
                if i + 1 < len(sentences):
                    sent = sentences[i] + sentences[i + 1]
                    sent = sent.strip()
                    if sent:
                        result.append(sent)
            if len(sentences) % 2 == 1 and sentences[-1].strip():
                result.append(sentences[-1].strip())
        
        # 如果还是没有结果，尝试按长度和语义分割（避免在词中间断开）
        if len(result) < 2 and len(text) > 100:
            result = self._split_by_semantic_boundary(text)
        
        # 如果还是没有结果，返回整个文本作为单个句子
        return [s for s in result if s] if result else [text]
    
    def _split_by_semantic_boundary(self, text: str) -> List[str]:
        """按语义边界分割文本（避免在词中间断开）"""
        if not JIEBA_AVAILABLE or not self.use_chinese_segmentation:
            # 如果没有 jieba，按固定长度分割，但尽量在标点处断开
            return self._split_by_punctuation_boundary(text)
        
        # 使用 jieba 分词，在词边界处分割
        # 将文本分成较小的块，每个块在词边界处结束
        chunk_size = 200  # 字符数
        chunks = []
        start = 0
        
        while start < len(text):
            end = min(start + chunk_size, len(text))
            chunk = text[start:end]
            
            # 如果还没到文本末尾，尝试在词边界处调整
            if end < len(text):
                # 使用 jieba 分词找到最近的词边界
                words = list(jieba.cut(chunk))
                # 如果最后一个词很短，可能是不完整的，向前调整
                if words and len(words[-1]) < 3:
                    # 尝试找到最近的标点符号
                    for i in range(len(chunk) - 1, max(len(chunk) - 50, 0), -1):
                        if chunk[i] in '。！？，、；':
                            chunk = text[start:start+i+1]
                            end = start + i + 1
                            break
            
            chunks.append(chunk)
            start = end
        
        return chunks if chunks else [text]
    
    def _split_by_punctuation_boundary(self, text: str) -> List[str]:
        """按标点符号边界分割文本"""
        chunk_size = 200  # 字符数
        chunks = []
        start = 0
        
        while start < len(text):
            end = min(start + chunk_size, len(text))
            
            # 如果还没到文本末尾，尝试在标点处断开
            if end < len(text):
                # 向后查找最近的标点符号
                for i in range(min(end - start, 50), 0, -1):
                    if text[start + i] in '。！？，、；':
                        end = start + i + 1
                        break
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            start = end
        
        return chunks if chunks else [text]
    
    def _create_chunk(self, paragraphs: List[Dict], full_text: str) -> Dict:
        """创建切片"""
        chunk_text = '\n\n'.join([p["text"] for p in paragraphs])
        start_idx = paragraphs[0]["start_idx"]
        end_idx = paragraphs[-1]["end_idx"]
        
        # 获取讲话人（如果所有段落都是同一人）
        speakers = [p.get("speaker") for p in paragraphs if p.get("speaker")]
        speaker = speakers[0] if len(set(speakers)) == 1 else None
        
        return {
            "text": chunk_text,
            "start_idx": start_idx,
            "end_idx": end_idx,
            "speaker": speaker,
        }
    
    def _add_overlap(self, chunks: List[Dict], full_text: str) -> List[Dict]:
        """添加重叠内容"""
        if len(chunks) <= 1:
            return chunks
        
        overlapped = []
        for i, chunk in enumerate(chunks):
            if i == 0:
                # 第一个块：添加下一个块的开头
                if i + 1 < len(chunks):
                    next_chunk = chunks[i + 1]
                    overlap_text = self._get_overlap_text(
                        chunk["text"], next_chunk["text"], self.overlap
                    )
                    chunk["text"] = chunk["text"] + "\n\n" + overlap_text
            elif i == len(chunks) - 1:
                # 最后一个块：添加前一个块的结尾
                prev_chunk = chunks[i - 1]
                overlap_text = self._get_overlap_text(
                    prev_chunk["text"], chunk["text"], self.overlap
                )
                chunk["text"] = overlap_text + "\n\n" + chunk["text"]
            else:
                # 中间块：添加前后重叠
                prev_chunk = chunks[i - 1]
                next_chunk = chunks[i + 1]
                prev_overlap = self._get_overlap_text(
                    prev_chunk["text"], chunk["text"], self.overlap
                )
                next_overlap = self._get_overlap_text(
                    chunk["text"], next_chunk["text"], self.overlap
                )
                chunk["text"] = prev_overlap + "\n\n" + chunk["text"] + "\n\n" + next_overlap
            
            overlapped.append(chunk)
        
        return overlapped
    
    def _get_overlap_text(self, text1: str, text2: str, overlap_tokens: int) -> str:
        """获取重叠文本"""
        # 简单实现：从 text2 开头取一定 token 的内容
        sentences = self._split_into_sentences(text2)
        overlap_text = ""
        tokens = 0
        
        for sent in sentences:
            sent_tokens = self._count_tokens(sent)
            if tokens + sent_tokens <= overlap_tokens:
                overlap_text += sent
                tokens += sent_tokens
            else:
                break
        
        return overlap_text
    
    def _detect_speaker(self, text: str) -> str:
        """检测讲话人"""
        if self.speaker_detector:
            return self.speaker_detector.detect(text)
        return None
    
    def _count_tokens(self, text: str) -> int:
        """计算 token 数量，对中文进行优化"""
        if self.llm:
            return self.llm.count_tokens(text)
        else:
            # 更准确的中文 token 估算
            # 统计中文字符、中文标点、英文、数字等
            chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
            chinese_punctuation = sum(1 for c in text if '\u3000' <= c <= '\u303f' or c in '。！？，、；：')
            other_chars = len(text) - chinese_chars - chinese_punctuation
            
            # 不同模型的 token 化不同，这里使用更保守的估算
            # 中文：约 1.2-1.5 字符/token（根据模型不同）
            # 中文标点：约 1 字符/token
            # 其他：约 3-4 字符/token
            tokens = int(chinese_chars / 1.3 + chinese_punctuation / 1.0 + other_chars / 3.5)
            return max(tokens, 1)  # 至少返回 1

