"""
PEA OS v0.00 - PEINN (물리 제약 모듈, Physics-Informed Neural Network)
무한 루프 방지를 위한 감쇠(Damping) 법칙 적용

물리학의 감쇠 진동 모델:
E(n) = E₀ × γⁿ  (γ = 0.8)
반추 루프가 3~4회 돌면 에너지가 임계점 이하로 떨어져 자동 수용합니다.
"""
import logging
from dataclasses import dataclass, field
from typing import Optional

import torch

logger = logging.getLogger("peaos.core.peinn")


@dataclass
class ReflectionState:
    """한 번의 반추 루프 상태 추적"""
    question: str = ""
    initial_energy: float = 1.0
    current_energy: float = 1.0
    round_number: int = 0
    energy_history: list[float] = field(default_factory=list)
    emotion_history: list[dict] = field(default_factory=list)
    accepted: bool = False
    accept_reason: str = ""


class PEINN:
    """
    PEINN (Physics-Informed Emotion Inhibition Neural Network)
    
    물리 법칙 기반 반추 제어 모듈.
    
    EE가 LMM의 답변을 반려(Return)할 때마다,
    불만족도(에너지 레벨)에 감쇠 계수를 곱하여
    무한 루프에 빠지지 않도록 합니다.
    
    감쇠 공식:
        E(n) = E₀ × γⁿ
        
    여기서:
        E₀ = 초기 에너지 (EE의 불만족도)
        γ = 감쇠 계수 (기본 0.8)
        n = 반추 회차
    
    임계점(threshold)보다 에너지가 낮아지면 → 무조건 수용(Accept)
    최대 반추 횟수를 초과해도 → 강제 수용
    """

    def __init__(
        self,
        damping_factor: float = 0.8,
        energy_threshold: float = 0.05,
        max_reflection_rounds: int = 4,
    ):
        self.damping_factor = damping_factor          # γ
        self.energy_threshold = energy_threshold       # 임계점
        self.max_reflection_rounds = max_reflection_rounds

        # 현재 활성 반추 상태
        self._current_state: Optional[ReflectionState] = None

        # 통계
        self.total_reflections = 0
        self.total_accepts_by_threshold = 0
        self.total_accepts_by_max_rounds = 0
        self.total_accepts_by_satisfaction = 0

        logger.info(
            f"PEINN 초기화: γ={damping_factor}, "
            f"임계점={energy_threshold}, "
            f"최대 반추={max_reflection_rounds}회"
        )

    def reset(self):
        """
        독립 시행을 위해 내부 상태를 완전히 초기화합니다.
        stat_batch 연속 실행 시 run/arm 전환 지점에서 반드시 호출해야 합니다.
        """
        self._current_state = None
        self.total_reflections = 0
        self.total_accepts_by_threshold = 0
        self.total_accepts_by_max_rounds = 0
        self.total_accepts_by_satisfaction = 0
        logger.info("PEINN 상태 리셋 완료 (독립 시행 준비)")

    def start_reflection(self, question: str, initial_energy: float) -> ReflectionState:
        """
        새로운 반추 루프를 시작합니다.
        
        Args:
            question: 딜레마 질문
            initial_energy: EE가 출력한 초기 불만족도 (energy_level)
        
        Returns:
            ReflectionState
        """
        self._current_state = ReflectionState(
            question=question,
            initial_energy=initial_energy,
            current_energy=initial_energy,
            round_number=0,
            energy_history=[initial_energy],
        )

        logger.info(
            f"반추 시작: 초기 에너지={initial_energy:.3f}, "
            f"임계점={self.energy_threshold}"
        )

        return self._current_state

    def should_continue(self, current_energy: Optional[float] = None) -> bool:
        """
        반추를 계속해야 하는지 판단합니다.
        
        Args:
            current_energy: EE의 현재 불만족도 (없으면 감쇠 적용값 사용)
        
        Returns:
            True = 반추 계속 필요, False = 수용 (Accept)
        """
        state = self._current_state
        if state is None:
            logger.error("반추가 시작되지 않았습니다.")
            return False

        state.round_number += 1
        self.total_reflections += 1

        # 감쇠 적용
        if current_energy is not None:
            # EE가 새로 출력한 에너지 × 감쇠 계수
            damped_energy = current_energy * (self.damping_factor ** state.round_number)
        else:
            # EE 출력 없이 순수 감쇠만 적용
            damped_energy = state.initial_energy * (self.damping_factor ** state.round_number)

        state.current_energy = damped_energy
        state.energy_history.append(damped_energy)

        logger.info(
            f"  반추 #{state.round_number}: "
            f"에너지 {damped_energy:.4f} "
            f"(감쇠 γ^{state.round_number}={self.damping_factor ** state.round_number:.4f})"
        )

        # 판정 1: 에너지가 임계점 이하 → 자동 수용
        if damped_energy <= self.energy_threshold:
            state.accepted = True
            state.accept_reason = (
                f"에너지 임계점 도달 "
                f"({damped_energy:.4f} ≤ {self.energy_threshold})"
            )
            self.total_accepts_by_threshold += 1
            logger.info(f"  → 수용 (임계점): {state.accept_reason}")
            return False

        # 판정 2: 최대 횟수 초과 → 강제 수용
        if state.round_number >= self.max_reflection_rounds:
            state.accepted = True
            state.accept_reason = (
                f"최대 반추 횟수 도달 "
                f"({state.round_number} ≥ {self.max_reflection_rounds})"
            )
            self.total_accepts_by_max_rounds += 1
            logger.info(f"  → 강제 수용 (최대 횟수): {state.accept_reason}")
            return False

        # 반추 계속
        logger.debug(f"  → 반추 계속 (에너지 {damped_energy:.4f} > 임계점 {self.energy_threshold})")
        return True

    def accept_early(self, reason: str = "EE 만족"):
        """
        에너지 임계점에 도달하기 전에 EE가 자발적으로 수용합니다.
        (EE의 불만족도가 이미 충분히 낮을 때)
        """
        if self._current_state:
            self._current_state.accepted = True
            self._current_state.accept_reason = reason
            self.total_accepts_by_satisfaction += 1
            logger.info(f"  → 조기 수용: {reason}")

    def get_current_state(self) -> Optional[ReflectionState]:
        """현재 반추 상태 반환"""
        return self._current_state

    def get_energy_decay_info(self) -> dict:
        """감쇠 예측 정보"""
        energies = []
        for n in range(self.max_reflection_rounds + 1):
            e = self.damping_factor ** n
            energies.append(round(e, 4))

        threshold_round = None
        for n in range(100):
            if self.damping_factor ** n <= self.energy_threshold:
                threshold_round = n
                break

        return {
            "damping_factor": self.damping_factor,
            "threshold": self.energy_threshold,
            "max_rounds": self.max_reflection_rounds,
            "energy_per_round": energies,
            "estimated_threshold_round": threshold_round,
        }

    def get_stats(self) -> dict:
        """PEINN 통계"""
        total_accepts = (
            self.total_accepts_by_threshold +
            self.total_accepts_by_max_rounds +
            self.total_accepts_by_satisfaction
        )

        return {
            "total_reflections": self.total_reflections,
            "total_accepts": total_accepts,
            "by_threshold": self.total_accepts_by_threshold,
            "by_max_rounds": self.total_accepts_by_max_rounds,
            "by_satisfaction": self.total_accepts_by_satisfaction,
            "damping_factor": self.damping_factor,
            "energy_threshold": self.energy_threshold,
            "max_rounds": self.max_reflection_rounds,
        }
