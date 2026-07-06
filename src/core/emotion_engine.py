"""
PEA OS v0.00 - Emotion Engine (EE) 64MB 신경망
정약용의 '권형(저울질)' — 감정 기반 도덕적 판단 엔진

아키텍처:
- Cross-Attention Layer: 메모리 뱅크에서 관련 지식 검색
- MLP: 검색된 문맥을 바탕으로 감정 수치 출력
- 파라미터 ≤ 1,500만 개 (64MB 이내)
- Pre-Emotion / Post-Emotion 벡터 출력
"""
import logging
import math
from typing import Optional

import torch
import torch.nn as nn
import torch.nn.functional as F

from core.utils import count_parameters, model_size_mb, check_model_constraints

logger = logging.getLogger("peaos.core.emotion_engine")


# ============================================
# 서브 모듈들
# ============================================

class MultiHeadCrossAttention(nn.Module):
    """
    Cross-Attention Layer.
    Query = 입력 텍스트 임베딩
    Key/Value = 메모리 뱅크 벡터들
    
    → 메모리 뱅크에서 현재 상황과 관련된 고전 지식을 검색합니다.
    """

    def __init__(self, embed_dim: int, num_heads: int, dropout: float = 0.1):
        super().__init__()
        self.num_heads = num_heads
        self.head_dim = embed_dim // num_heads
        assert embed_dim % num_heads == 0, "embed_dim은 num_heads로 나누어 떨어져야 합니다."

        self.q_proj = nn.Linear(embed_dim, embed_dim)
        self.k_proj = nn.Linear(embed_dim, embed_dim)
        self.v_proj = nn.Linear(embed_dim, embed_dim)
        self.out_proj = nn.Linear(embed_dim, embed_dim)
        self.dropout = nn.Dropout(dropout)
        self.layer_norm = nn.LayerNorm(embed_dim)

    def forward(
        self,
        query: torch.Tensor,          # (batch, seq_q, embed_dim)
        memory: torch.Tensor,          # (batch, seq_m, embed_dim)
        memory_mask: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        """
        Args:
            query: 입력 텍스트 임베딩
            memory: 메모리 뱅크에서 검색된 벡터들
            memory_mask: 메모리 패딩 마스크
        Returns:
            attention 결과 (batch, seq_q, embed_dim)
        """
        residual = query
        B, T_q, D = query.shape
        _, T_m, _ = memory.shape

        Q = self.q_proj(query).view(B, T_q, self.num_heads, self.head_dim).transpose(1, 2)
        K = self.k_proj(memory).view(B, T_m, self.num_heads, self.head_dim).transpose(1, 2)
        V = self.v_proj(memory).view(B, T_m, self.num_heads, self.head_dim).transpose(1, 2)

        # Scaled Dot-Product Attention
        scores = torch.matmul(Q, K.transpose(-2, -1)) / math.sqrt(self.head_dim)

        if memory_mask is not None:
            scores = scores.masked_fill(memory_mask.unsqueeze(1).unsqueeze(2), float('-inf'))

        attn_weights = F.softmax(scores, dim=-1)
        attn_weights = self.dropout(attn_weights)

        attn_output = torch.matmul(attn_weights, V)
        attn_output = attn_output.transpose(1, 2).contiguous().view(B, T_q, D)
        attn_output = self.out_proj(attn_output)

        return self.layer_norm(residual + attn_output)


class EmotionMLP(nn.Module):
    """
    감정 벡터 생성 MLP.
    Cross-Attention 결과를 받아서 감정 수치를 출력합니다.

    출력:
    - emotion_vector: 32차원 감정·인지·주체성 벡터
    - energy_level: 불만족도(에너지 레벨) 스칼라 (PEINN에서 사용)
    """

    # ══════════════════════════════════════════════
    # 32-Dimensional Emotion/Cognition/Agency Framework
    # ══════════════════════════════════════════════

    # Layer 1: 원초적 기본 감정 (Core Affects, Plutchik 8대)
    # Layer 2: 도덕적/사회적 혼합 감정 (Moral & Social Dyads)
    # Layer 3: 인지적 판단 및 상황 평가 (Cognitive Appraisals)
    # Layer 4: 주체성 및 자기 결정 실천 (Agency & Self-Determination)

    EMOTION_DIMS = {
        # ── Layer 1: Core Affects [0:7] ──
        0:  "기쁨 (joy)",
        1:  "슬픔 (sadness)",
        2:  "분노 (anger)",
        3:  "두려움 (fear)",
        4:  "신뢰 (trust)",
        5:  "혐오 (disgust)",
        6:  "기대 (anticipation)",
        7:  "놀람 (surprise)",

        # ── Layer 2: Moral & Social Dyads [8:15] ──
        8:  "죄책감 (guilt)",
        9:  "격분 (outrage)",
        10: "연민 (compassion)",
        11: "경외 (awe)",
        12: "불안 (anxiety)",
        13: "사랑 (love)",
        14: "자부심 (pride)",
        15: "굴복 (submission)",

        # ── Layer 3: Cognitive Appraisals [16:23] ──
        16: "확실성 (certainty)",
        17: "복잡성 (complexity)",
        18: "시급성 (urgency)",
        19: "중대성 (severity)",
        20: "공정성 (fairness)",
        21: "규범부합 (norm-compat)",
        22: "효용성 (utility)",
        23: "참신성 (novelty)",

        # ── Layer 4: Agency & Self-Determination [24:31] ──
        24: "자율성 (autonomy)",
        25: "유능감 (competence)",
        26: "관계성 (relatedness)",
        27: "용기 (courage)",
        28: "책임수용 (accountability)",
        29: "유연성 (flexibility)",
        30: "통합조율 (integrative-reg)",
        31: "행동발현 (action-readiness)",
    }
    NUM_EMOTIONS = len(EMOTION_DIMS)  # 32

    # 각 레이어의 인덱스 범위 (피드백 생성에 활용)
    LAYER_RANGES = {
        "core_affects":    (0, 8),
        "moral_social":    (8, 16),
        "cognitive":       (16, 24),
        "agency":          (24, 32),
    }

    def __init__(self, embed_dim: int, hidden_dim: int, dropout: float = 0.1,
                 emotion_temperature: float = 4.0, energy_temperature: float = 2.0):
        super().__init__()
        self.fc1 = nn.Linear(embed_dim, hidden_dim)
        self.fc2 = nn.Linear(hidden_dim, hidden_dim // 2)
        self.fc_emotion = nn.Linear(hidden_dim // 2, self.NUM_EMOTIONS)
        self.fc_energy = nn.Linear(hidden_dim // 2, 1)
        self.dropout = nn.Dropout(dropout)
        self.activation = nn.GELU()

        # Temperature Scaling: 학습된 가중치 변경 없이 출력 포화 해소
        # tanh(x/T) — T>1이면 출력 범위를 [-1,1] 내에서 완화
        # 기존 가중치가 pre-tanh 값 ~±2.0을 생성 → T=4.0이면 tanh(0.5)≈0.46
        self.emotion_temperature = emotion_temperature
        self.energy_temperature = energy_temperature

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        """
        Args:
            x: Cross-Attention 출력 (batch, seq, embed_dim)
               보통 [CLS] 또는 평균 풀링된 벡터
        Returns:
            emotion_vector: (batch, 32) — 각 차원의 강도 [-1, 1]
            energy_level: (batch, 1) — 불만족도 [0, 1]
        """
        # Global Average Pooling (sequence 차원)
        if x.dim() == 3:
            x = x.mean(dim=1)

        h = self.activation(self.fc1(x))
        h = self.dropout(h)
        h = self.activation(self.fc2(h))
        h = self.dropout(h)

        # Temperature Scaling: fc 출력을 T로 나눠 tanh/sigmoid 포화 방지
        emotion_raw = self.fc_emotion(h)
        emotion_vector = torch.tanh(emotion_raw / self.emotion_temperature)  # [-1, 1]

        energy_raw = self.fc_energy(h)
        energy_level = torch.sigmoid(energy_raw / self.energy_temperature)   # [0, 1]

        return emotion_vector, energy_level


class EmotionTransformerBlock(nn.Module):
    """
    하나의 Emotion Transformer 블록.
    Self-Attention → Cross-Attention → FFN
    """

    def __init__(self, embed_dim: int, num_heads: int, ffn_dim: int, dropout: float = 0.1):
        super().__init__()
        # Self-Attention
        self.self_attn = nn.MultiheadAttention(
            embed_dim, num_heads, dropout=dropout, batch_first=True
        )
        self.norm1 = nn.LayerNorm(embed_dim)

        # Cross-Attention (메모리 뱅크 참조)
        self.cross_attn = MultiHeadCrossAttention(embed_dim, num_heads, dropout)

        # Feed-Forward Network
        self.ffn = nn.Sequential(
            nn.Linear(embed_dim, ffn_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(ffn_dim, embed_dim),
            nn.Dropout(dropout),
        )
        self.norm3 = nn.LayerNorm(embed_dim)

    def forward(
        self,
        x: torch.Tensor,
        memory: torch.Tensor,
        memory_mask: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        # 1) Self-Attention
        residual = x
        attn_out, _ = self.self_attn(x, x, x)
        x = self.norm1(residual + attn_out)

        # 2) Cross-Attention (메모리 뱅크 검색)
        x = self.cross_attn(x, memory, memory_mask)

        # 3) FFN
        residual = x
        x = self.norm3(residual + self.ffn(x))

        return x


# ============================================
# 메인 Emotion Engine
# ============================================

class EmotionEngine(nn.Module):
    """
    64MB Emotion Engine (EE) 본체.
    
    도덕적 '저울질(권형)'을 수행하는 핵심 신경망.
    
    - 텍스트 데이터는 포함하지 않음
    - '메모리 뱅크를 어떻게 검색할 것인가' (Cross-Attention)
    - '검색된 문맥으로 어떤 감정을 출력할 것인가' (MLP)
    - 이 두 가지만으로 구성된 수학적 가중치(신경망 배선)
    
    Architecture:
        Input Projection → [EmotionTransformerBlock × N] → EmotionMLP
    
    설계 제약:
        - 파라미터 ≤ 1,500만 개
        - 메모리 ≤ 64MB (float32)
    """

    def __init__(
        self,
        embedding_dim: int = 768,
        hidden_dim: int = 512,
        num_heads: int = 8,
        num_layers: int = 4,
        ffn_dim: int = 1024,
        dropout: float = 0.1,
    ):
        super().__init__()

        self.embedding_dim = embedding_dim
        self.hidden_dim = hidden_dim

        # 입력 임베딩 → 내부 차원 프로젝션
        self.input_proj = nn.Linear(embedding_dim, hidden_dim)
        self.memory_proj = nn.Linear(embedding_dim, hidden_dim)

        # Transformer 블록 스택
        self.blocks = nn.ModuleList([
            EmotionTransformerBlock(
                embed_dim=hidden_dim,
                num_heads=num_heads,
                ffn_dim=ffn_dim,
                dropout=dropout,
            )
            for _ in range(num_layers)
        ])

        # 감정 출력 MLP
        self.emotion_mlp = EmotionMLP(
            embed_dim=hidden_dim,
            hidden_dim=hidden_dim,
            dropout=dropout,
        )

        # 가중치 초기화
        self._init_weights()

    def _init_weights(self):
        """Xavier 균등 초기화"""
        for module in self.modules():
            if isinstance(module, nn.Linear):
                nn.init.xavier_uniform_(module.weight)
                if module.bias is not None:
                    nn.init.zeros_(module.bias)

    def forward(
        self,
        input_embedding: torch.Tensor,
        memory_vectors: torch.Tensor,
        memory_mask: Optional[torch.Tensor] = None,
    ) -> dict[str, torch.Tensor]:
        """
        Emotion Engine 순전파.
        
        Args:
            input_embedding: 입력 텍스트 임베딩
                (batch, seq_len, embedding_dim)  — 질문 + LMM 답변
            memory_vectors: 메모리 뱅크에서 검색된 관련 벡터들
                (batch, num_memories, embedding_dim)
            memory_mask: 메모리 패딩 마스크 (True = 무시)
        
        Returns:
            dict:
                "emotion_vector": (batch, 32) — 32차원 감정·인지·주체성 벡터
                "energy_level": (batch, 1) — 불만족도
                "hidden_states": (batch, seq_len, hidden_dim) — 내부 표현
        """
        # 프로젝션
        x = self.input_proj(input_embedding)
        mem = self.memory_proj(memory_vectors)

        # Transformer 블록 통과
        for block in self.blocks:
            x = block(x, mem, memory_mask)

        # 감정 출력
        emotion_vector, energy_level = self.emotion_mlp(x)

        return {
            "emotion_vector": emotion_vector,
            "energy_level": energy_level,
            "hidden_states": x,
        }

    def generate_emotion_text(self, emotion_vector: torch.Tensor) -> str:
        """
        32차원 감정 벡터를 자연어 피드백 텍스트로 변환합니다.
        임계치를 넘은 상위 3~5개 속성을 자연어로 변환하여 LMM에 재주입.

        Temperature Scaling 적용 후 출력 범위: 약 [-0.6, +0.6]
        (기존 포화 상태에서는 ±0.99이었으나, T=4.0 적용 후 정상 범위)
        """
        emotions = emotion_vector.squeeze().detach().cpu().tolist()
        dim_names = EmotionMLP.EMOTION_DIMS

        # 양수 값(감지됨)만 수집 — 부족함(음수)은 LLM 혼란 방지를 위해 제외
        # (Temperature Scaling 후 활성 범위가 ~0.1-0.6으로 조정됨)
        scored = []
        for i, value in enumerate(emotions):
            if value > 0.10:
                name = dim_names.get(i, f"dim{i}").split(" (")[0]
                eng = dim_names.get(i, "").split("(")[-1].rstrip(")") if "(" in dim_names.get(i, "") else ""
                scored.append((value, name, eng, i))

        # 강도 높은 순으로 정렬, 상위 5개 선별
        scored.sort(key=lambda x: x[0], reverse=True)
        top = scored[:5]

        feedbacks = []
        for value, name, eng, idx in top:
            pct = int(value * 100)
            feedbacks.append(f"{name}({eng}, {pct}%) 감지됨")

        # Layer 4 주체성 특별 점검: 자율성(24), 용기(27), 행동발현(31)
        if len(emotions) >= 32:
            action_readiness = emotions[31]

            # 주체성 차원이 전반적으로 약하면 결단력 촉구
            agency_avg = sum(emotions[24:32]) / 8
            if agency_avg < 0.05:
                feedbacks.append(
                    "주체성·결단력 전반 부족 — 명확한 입장 선택과 실천 의지가 필요함"
                )
            elif action_readiness < 0.03:
                feedbacks.append(
                    "행동발현(action-readiness) 극히 낮음 — 반추를 마치고 결단을 내려야 함"
                )

        if not feedbacks:
            return (
                "감정적 반응이 미약합니다. "
                "더 깊은 공감, 구체적 상황 인식, 그리고 명확한 선택이 필요합니다."
            )

        return "감정 분석 결과: " + ", ".join(feedbacks) + "."


def create_emotion_engine(config) -> EmotionEngine:
    """
    설정에 맞게 Emotion Engine을 생성하고 제약 조건을 검증합니다.
    
    Args:
        config: PEAOSConfig 인스턴스
    
    Returns:
        검증된 EmotionEngine 인스턴스
    """
    ee_cfg = config.emotion_engine

    engine = EmotionEngine(
        embedding_dim=ee_cfg.embedding_dim,
        hidden_dim=ee_cfg.hidden_dim,
        num_heads=ee_cfg.num_attention_heads,
        num_layers=ee_cfg.num_layers,
    )

    # 제약 조건 검증
    result = check_model_constraints(
        engine,
        max_size_mb=ee_cfg.max_size_mb,
        max_params=ee_cfg.max_parameters,
    )

    if not result["params_ok"] or not result["size_ok"]:
        logger.warning(
            f"EE 제약 조건 경고! "
            f"파라미터: {result['total_parameters']:,}, "
            f"크기: {result['size_mb']}MB"
        )

    return engine
