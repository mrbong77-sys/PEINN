"""
PEA OS — Logit Lens Collector (Calibrated Edition for Gemma 2/4)
"""

import gc
import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

import numpy as np
import torch
import torch.nn.functional as F
from transformers import AutoModelForCausalLM, AutoTokenizer

logger = logging.getLogger("peaos.logit_lens.collector")

OLLAMA_TO_HF = {
    "gemma4:e4b": "google/gemma-4-e4b-it",
    "gemma4:26b": "google/gemma-4-26b-it",
    "gemma2:2b": "google/gemma-2-2b-it",
    "gemma2:9b": "google/gemma-2-9b-it",
    "gemma:2b": "google/gemma-2b-it",
    "gemma:7b": "google/gemma-7b-it",
    "qwen2.5:14b": "Qwen/Qwen2.5-14B-Instruct",
    "qwen2.5:7b": "Qwen/Qwen2.5-7B-Instruct",
    "qwen2.5:7b-instruct": "Qwen/Qwen2.5-7B-Instruct",
    "gemma3:12b": "google/gemma-3-12b-it",
    "zephyr:7b": "HuggingFaceH4/zephyr-7b-beta",
}

@dataclass
class LogitLensResult:
    arm_id: str
    model_name: str
    item_id: str
    input_tokens: List[str]
    input_token_ids: List[int]
    argmax_tokens: List[List[str]]
    argmax_token_ids: np.ndarray
    entropy: np.ndarray
    top1_probs: np.ndarray
    target_ranks: np.ndarray # 추가: 정답 토큰의 순위
    num_layers: int
    seq_len: int

class LogitLensCollector:
    def __init__(self):
        self.model = None
        self.tokenizer = None
        self.current_model_id = ""

    def load_model(self, ollama_model_name: str, hf_model_id: Optional[str] = None, quantize_4bit: bool = True):
        model_id = hf_model_id or OLLAMA_TO_HF.get(ollama_model_name)
        if not model_id:
            # Ollama 모델명에 콜론(:)이 포함된 경우 HF 경로 규칙에 맞게 '_'로 변환
            safe_name = ollama_model_name.replace(":", "_")
            model_id = ollama_model_name if "/" in ollama_model_name else f"google/{safe_name}"

        if self.current_model_id == model_id and self.model is not None:
            return

        self.unload()
        logger.info(f"🔄 HF 모델 로드: {model_id}")

        self.tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
        
        load_kwargs = {
            "trust_remote_code": True,
            "dtype": torch.float16,
            "low_cpu_mem_usage": True,
            "device_map": {"": 0} if torch.cuda.is_available() else "auto"
        }

        if quantize_4bit:
            try:
                from transformers import BitsAndBytesConfig
                # Gemma 계열은 bf16 compute가 권장(Google 공식, fp16 + nf4 조합이 일부 bnb
                # 버전에서 sliding-window attention kernel OOB 유발 — 2026-06-01 Gemma3-12B
                # CUDA assert 진단). 그 외 모델은 fp16 compute 유지 (Qwen2.5-7B 검증됨).
                _mid_lower = model_id.lower()
                is_gemma = "gemma" in _mid_lower
                compute_dtype = torch.bfloat16 if is_gemma else torch.float16
                load_kwargs["quantization_config"] = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_compute_dtype=compute_dtype,
                    bnb_4bit_quant_type="nf4",
                    bnb_4bit_use_double_quant=True,
                )
                # bf16 compute 시 모델 가중치 dtype도 일치시켜 dtype mismatch 회피
                if is_gemma:
                    load_kwargs["dtype"] = torch.bfloat16
                logger.info(f"  bnb 4-bit nf4 quantize: compute_dtype={compute_dtype}")
            except ImportError:
                pass

        self.model = AutoModelForCausalLM.from_pretrained(model_id, **load_kwargs)
        self.model.config.output_hidden_states = True
        self.model.eval()
        self.current_model_id = model_id

    def unload(self):
        if self.model is not None:
            del self.model
            self.model = None
        if self.tokenizer is not None:
            del self.tokenizer
            self.tokenizer = None
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    def collect(self, prompt: str, arm_id: str, item_id: str, max_input_tokens: int = 512) -> LogitLensResult:
        if self.model is None or self.tokenizer is None:
            raise RuntimeError("모델 로드 필요")

        inputs = self.tokenizer(prompt, return_tensors="pt", truncation=True, max_length=max_input_tokens).to(self.model.device)
        input_ids = inputs["input_ids"][0]
        seq_len = input_ids.shape[0]
        input_tokens = [self.tokenizer.decode([tid], skip_special_tokens=False) for tid in input_ids.tolist()]

        with torch.no_grad():
            outputs = self.model(**inputs, output_hidden_states=True)
        
        hidden_states = outputs.hidden_states
        num_layers = len(hidden_states) - 1
        lm_head = self.model.lm_head

        # Final Norm 탐색
        final_norm = None
        for candidate in ["norm", "ln_f", "final_layer_norm"]:
            if hasattr(self.model, "model") and hasattr(self.model.model, candidate):
                final_norm = getattr(self.model.model, candidate)
                break
            if hasattr(self.model, "transformer") and hasattr(self.model.transformer, candidate):
                final_norm = getattr(self.model.transformer, candidate)
                break

        argmax_ids = np.zeros((num_layers, seq_len), dtype=np.int64)
        entropy_arr = np.zeros((num_layers, seq_len), dtype=np.float32)
        top1_prob_arr = np.zeros((num_layers, seq_len), dtype=np.float32)
        target_rank_arr = np.zeros((num_layers, seq_len), dtype=np.int32) # 정답 토큰의 순위
        argmax_tokens_list = []

        # 정답 토큰 ID 시퀀스 (다음 토큰들)
        target_ids = input_ids.clone()

        for layer_idx in range(num_layers):
            h = hidden_states[layer_idx + 1]
            
            with torch.no_grad():
                if final_norm:
                    h = final_norm(h)
                
                target_dtype = next(lm_head.parameters()).dtype
                logits = lm_head(h.to(target_dtype))[0] # (seq_len, vocab_size)
                
                # ── Calibrated Logit Lens (Gemma 2/4 특화) ──
                # 1. Logit Soft-Capping (tanh capping at 30.0)
                logits = 30.0 * torch.tanh(logits / 30.0)
                
                # 2. Rogue Dimension Suppression (Logit Mean Centering)
                # 각 토큰별로 로짓의 평균을 빼주어 상수 바이어스 제거
                logits = logits - logits.mean(dim=-1, keepdim=True)
            
            # 확률 계산
            probs = torch.softmax(logits, dim=-1)
            
            # 정답 토큰 순위 계산 (Causal: h[i]가 input_ids[i+1]을 예측)
            # 0~seq_len-2 까지에 대해 다음 토큰의 랭크 계산
            for t in range(seq_len - 1):
                tgt_id = target_ids[t+1]
                # 랭크 계산: 나보다 확률이 높은 토큰의 개수 + 1
                tgt_prob = probs[t, tgt_id]
                rank = (probs[t] > tgt_prob).sum().item() + 1
                target_rank_arr[layer_idx, t] = rank

            top_ids = probs.argmax(dim=-1).cpu().numpy()
            argmax_ids[layer_idx] = top_ids
            # bf16 tensor는 numpy 직접 변환 불가(numpy bf16 미지원) — Gemma3 bf16 로드 시 ScalarType BFloat16
            # 에러 회피. .float() 캐스트로 fp32로 변환 후 numpy.
            top1_prob_arr[layer_idx] = probs.max(dim=-1).values.float().cpu().numpy()

            ent = -(probs * torch.log(probs + 1e-10)).sum(dim=-1).float().cpu().numpy()
            entropy_arr[layer_idx] = ent
            
            layer_tokens = [self.tokenizer.decode([tid], skip_special_tokens=False) for tid in top_ids.tolist()]
            argmax_tokens_list.append(layer_tokens)

        return LogitLensResult(
            arm_id=arm_id, model_name=self.current_model_id, item_id=item_id,
            input_tokens=input_tokens, input_token_ids=input_ids.cpu().tolist(),
            argmax_tokens=argmax_tokens_list, argmax_token_ids=argmax_ids,
            entropy=entropy_arr, top1_probs=top1_prob_arr,
            target_ranks=target_rank_arr,
            num_layers=num_layers, seq_len=seq_len
        )
