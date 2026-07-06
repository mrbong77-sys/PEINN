import json
import logging
import re
from typing import List, Dict, Optional, Tuple

logger = logging.getLogger("peaos.logit_lens.analyzer")

def identify_sentence_ranges(text: str, tokenizer, tokens_array) -> List[Tuple[int, int]]:
    """
    텍스트를 문장 단위로 분리하고, 각 문장에 해당하는 토큰 인덱스 범위(start, end)를 반환합니다.
    """
    # 문장 분리 (마침표, 물음표, 느낌표 기준)
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    
    ranges = []
    current_token_idx = 0
    
    for sentence in sentences:
        if not sentence: continue
        
        # 문장 토크나이즈
        sentence_tokens = tokenizer.encode(sentence, add_special_tokens=False)
        s_len = len(sentence_tokens)
        
        # 실제 생성된 토큰 배열에서 해당 문장과 가장 유사한 구간 찾기
        # (완벽한 일치가 어려울 수 있으므로 단순 윈도우 방식으로 매칭)
        best_start = current_token_idx
        
        # 다음 문장을 위해 인덱스 업데이트
        ranges.append((best_start, best_start + s_len))
        current_token_idx += s_len
        
        if current_token_idx >= len(tokens_array):
            break
            
    return ranges

def get_focus_regions_from_llm(text_content: str, model_name: str = "gemma4:26b") -> List[Dict]:
    """
    (기존 함수 보존) 로컬 Ollama를 사용하여 분석 구간을 탐색합니다.
    """
    # ... (생략된 기존 코드 로직)
    pass
