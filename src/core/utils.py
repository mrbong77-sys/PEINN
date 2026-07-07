"""
PEINN v0.00 - 유틸리티 함수
파라미터 수 계산, CUDA 관리 등
"""
import logging
from typing import Optional

logger = logging.getLogger("peinn.core.utils")


def count_parameters(model, trainable_only: bool = False) -> int:
    """
    모델의 파라미터 수를 계산합니다.
    
    Args:
        model: PyTorch nn.Module
        trainable_only: True면 학습 가능 파라미터만 카운트
    
    Returns:
        파라미터 수
    """
    if trainable_only:
        return sum(p.numel() for p in model.parameters() if p.requires_grad)
    return sum(p.numel() for p in model.parameters())


def model_size_mb(model) -> float:
    """
    모델의 메모리 크기를 MB 단위로 계산합니다.
    float32 기준: 파라미터 수 × 4 bytes
    """
    param_count = count_parameters(model)
    size_bytes = param_count * 4  # float32
    return size_bytes / (1024 * 1024)


def check_model_constraints(model, max_size_mb: float = 64.0, max_params: int = 15_000_000):
    """
    EE 모델이 설계 제약을 충족하는지 검증합니다.
    
    Args:
        model: PyTorch nn.Module
        max_size_mb: 최대 크기 (MB)
        max_params: 최대 파라미터 수
    
    Returns:
        dict: 검증 결과
    
    Raises:
        ValueError: 제약 조건 위반 시
    """
    total_params = count_parameters(model)
    trainable_params = count_parameters(model, trainable_only=True)
    size_mb = model_size_mb(model)

    result = {
        "total_parameters": total_params,
        "trainable_parameters": trainable_params,
        "frozen_parameters": total_params - trainable_params,
        "size_mb": round(size_mb, 2),
        "max_size_mb": max_size_mb,
        "max_params": max_params,
        "params_ok": total_params <= max_params,
        "size_ok": size_mb <= max_size_mb,
    }

    logger.info(f"모델 검증:")
    logger.info(f"  총 파라미터: {total_params:,} / {max_params:,}")
    logger.info(f"  학습 가능: {trainable_params:,}")
    logger.info(f"  동결: {total_params - trainable_params:,}")
    logger.info(f"  크기: {size_mb:.2f}MB / {max_size_mb}MB")

    if not result["params_ok"]:
        logger.error(f"파라미터 수 초과! {total_params:,} > {max_params:,}")
    if not result["size_ok"]:
        logger.error(f"크기 초과! {size_mb:.2f}MB > {max_size_mb}MB")

    return result


def get_device(prefer_cuda: bool = True):
    """
    사용 가능한 최적 디바이스를 반환합니다.
    CUDA가 사용 가능해도 실제 커널 호환성을 테스트합니다.
    (예: RTX 5080 sm_120이 현재 PyTorch에서 지원되지 않는 경우)
    """
    import torch

    if prefer_cuda and torch.cuda.is_available():
        try:
            # 실제 CUDA 커널 실행 테스트
            test = torch.zeros(1, device="cuda")
            _ = test + test
            del test
            device = torch.device("cuda")
            gpu_name = torch.cuda.get_device_name(0)
            logger.info(f"GPU 사용: {gpu_name}")
        except RuntimeError as e:
            logger.warning(f"CUDA 호환성 문제 감지, CPU로 폴백: {e}")
            device = torch.device("cpu")
    else:
        device = torch.device("cpu")
        logger.info("CPU 사용")

    return device


def log_vram_usage():
    """현재 VRAM 사용량을 로깅합니다."""
    try:
        import torch
        if torch.cuda.is_available():
            allocated = torch.cuda.memory_allocated(0) / (1024 ** 3)
            reserved = torch.cuda.memory_reserved(0) / (1024 ** 3)
            total = torch.cuda.get_device_properties(0).total_memory / (1024 ** 3)
            logger.info(
                f"VRAM: 할당 {allocated:.2f}GB, 예약 {reserved:.2f}GB, "
                f"전체 {total:.1f}GB"
            )
    except ImportError:
        pass
