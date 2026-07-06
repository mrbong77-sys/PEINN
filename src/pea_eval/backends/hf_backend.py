import os
# Offline mode is opt-in: set PEAOS_HF_OFFLINE=1 to load only from the local
# Hugging Face cache. By default the backend may download the model from the Hub,
# so a newcomer can graft PEINN onto a base model they have not pre-downloaded.
_HF_OFFLINE = os.environ.get("PEAOS_HF_OFFLINE") == "1"
if _HF_OFFLINE:
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

import torch
import re
import time
import logging
import gc
import numpy as np
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Tuple
from transformers import AutoTokenizer, AutoModelForCausalLM

logger = logging.getLogger("peaos.backends.hf_backend")

@dataclass
class HFGenerationResult:
    """HF Transformers 생성 결과 및 내부 상태 컨테이너"""
    text: str
    thought_block: str
    latency_sec: float
    model_name: str
    hidden_states_pooled: Any  # np.ndarray or None. shape: (n_layers, hidden_size)
    generated_token_ids: List[int] = field(default_factory=list)
    error: str = ""

class HFModelBackend:
    _cache: Dict[str, "HFModelBackend"] = {}
    _lock: Any = None  # threading.Lock

    @classmethod
    def unload_all_models(cls):
        """모든 캐시된 HF 모델을 메모리에서 해제합니다."""
        import threading
        if cls._lock is None:
            cls._lock = threading.Lock()
            
        with cls._lock:
            if not cls._cache:
                return
                
            logger.info(f"🗑️ 모든 HF 모델 언로드 중 ({len(cls._cache)}개)...")
            for model_id, instance in list(cls._cache.items()):
                if hasattr(instance, 'model'):
                    del instance.model
                if hasattr(instance, 'tokenizer'):
                    del instance.tokenizer
                del cls._cache[model_id]
            
            import torch
            import gc
            gc.collect()
            torch.cuda.empty_cache()
            logger.info("✅ 모든 HF VRAM 해제 완료")

    @classmethod
    def get_instance(cls, model_id: str, device: str = "auto") -> "HFModelBackend":
        import threading
        if cls._lock is None:
            cls._lock = threading.Lock()
        
        with cls._lock:
            if model_id not in cls._cache:
                try:
                    cls._cache[model_id] = cls(model_id, device)
                except Exception as e:
                    if model_id in cls._cache:
                        del cls._cache[model_id]
                    raise e
            return cls._cache[model_id]

    def __init__(self, model_id: str, device: str = "auto"):
        self.model_id = model_id
        logger.info(f"Loading HF model: {model_id} (device_map={device})")
        
        try:
            # Try loading as a local path first if possible
            resolved_path = model_id
            if not os.path.exists(model_id):
                # 1. Check standard hub cache structure
                repo_id_slug = f"models--{model_id.replace('/', '--')}"
                hub_path = os.path.expanduser(f"~/.cache/huggingface/hub/{repo_id_slug}/snapshots")
                if os.path.exists(hub_path):
                    snapshots = sorted(os.listdir(hub_path))
                    if snapshots:
                        best_snapshot = os.path.join(hub_path, snapshots[-1])
                        logger.info(f"Auto-resolved HF cache path: {best_snapshot}")
                        resolved_path = best_snapshot
                
                # 2. Check extra local model dirs (colon-separated) if not in hub cache.
                #    Configure via PEAOS_HF_LOCAL_DIRS, e.g. "/data/models:/mnt/models".
                if resolved_path == model_id:
                    _extra_dirs = [d for d in os.environ.get("PEAOS_HF_LOCAL_DIRS", "").split(os.pathsep) if d]
                    possible_paths = [os.path.join(d, model_id.split("/")[-1]) for d in _extra_dirs]
                    for p in possible_paths:
                        if os.path.exists(p):
                            logger.info(f"Found local model at: {p}")
                            resolved_path = p
                            break
            
            self.tokenizer = AutoTokenizer.from_pretrained(
                resolved_path, 
                trust_remote_code=True, 
                local_files_only=_HF_OFFLINE,
                use_fast=False  # Force slow tokenizer to avoid sentencepiece/fast-tokenizer conversion issues
            )
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
                
            self.model = AutoModelForCausalLM.from_pretrained(
                resolved_path,
                dtype=torch.bfloat16,
                device_map=device,
                trust_remote_code=True,
                local_files_only=_HF_OFFLINE
            )
            self.model.eval()
            logger.info(f"Model {model_id} loaded successfully from {resolved_path}.")
        except Exception as e:
            logger.error(f"Failed to load HF model {model_id}: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            raise e

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        max_new_tokens: int = 2048,
        temperature: float = 0.3,
        seed: Optional[int] = None,
        capture_hidden_states: bool = True,
        thinking_mode: bool = False,
    ) -> HFGenerationResult:
        start_time = time.time()
        
        if seed is not None:
            torch.manual_seed(seed)
            np.random.seed(seed)
            
        messages = []
        if system_prompt:
            if thinking_mode and "gemma" not in self.model_id.lower():
                # Fallback for non-Gemma if thinking mode requested
                messages.append({"role": "system", "content": system_prompt + "\n[Think step by step before answering and output thoughts in <think> tags]"})
            else:
                messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_prompt})

        # Tokenize using chat template with attention_mask
        try:
            encoding = self.tokenizer.apply_chat_template(
                messages,
                add_generation_prompt=True,
                return_tensors="pt",
                return_dict=True
            )
            input_ids = encoding["input_ids"].to(self.model.device)
            attention_mask = encoding["attention_mask"].to(self.model.device)
        except Exception as e:
            # Fallback if standard apply fails
            encoding = self.tokenizer(f"{system_prompt}\n{user_prompt}", return_tensors="pt")
            input_ids = encoding.input_ids.to(self.model.device)
            attention_mask = encoding.attention_mask.to(self.model.device)

        input_len = input_ids.shape[1]

        try:
            # HOTFIX: model.generate is a synchronous CUDA call that holds the GIL
            # for the entire forward pass (can be 10–60s). Awaiting it directly
            # inside `async def generate` blocks the asyncio event loop completely
            # — progress loggers, signal handlers, and concurrent tasks all stall.
            # Off-load to a worker thread so the loop keeps spinning.
            import asyncio
            def _do_generate():
                with torch.no_grad():
                    return self.model.generate(
                        input_ids,
                        attention_mask=attention_mask,
                        max_new_tokens=max_new_tokens,
                        do_sample=(temperature > 0),
                        temperature=temperature if temperature > 0 else None,
                        pad_token_id=self.tokenizer.pad_token_id,
                        return_dict_in_generate=True,
                        output_hidden_states=capture_hidden_states,
                        output_attentions=False,
                    )
            outputs = await asyncio.to_thread(_do_generate)
        except Exception as e:
            logger.error(f"Generation error: {e}")
            return HFGenerationResult(
                text="", thought_block="", latency_sec=time.time() - start_time,
                model_name=self.model_id, hidden_states_pooled=None, error=str(e)
            )

        gen_sequences = outputs.sequences[0]
        generated_tokens = gen_sequences[input_len:].tolist()
        full_text = self.tokenizer.decode(generated_tokens, skip_special_tokens=True)
        
        # Parse thinking block
        clean_text, thought_block = self._parse_thinking_block(full_text)
        
        # Process hidden states
        hidden_states_pooled = None
        if capture_hidden_states and hasattr(outputs, "hidden_states") and outputs.hidden_states:
            # outputs.hidden_states is a tuple of length generating steps
            # Each step is a tuple of layer hidden states (num_layers + 1)
            # shape of each layer: (batch_size, sequence_length, hidden_size)
            
            all_step_states = [] # list of (n_layers, hidden_size)
            for step_idx, step_layers in enumerate(outputs.hidden_states):
                # step_layers: tuple of length num_layers + 1
                # Skip the embedding layer (index 0) to get n_layers
                # In typical HF models, layer 0 is embedding, layer 1 to n are transformer layers
                layer_states = []
                for layer_idx in range(1, len(step_layers)):
                    # Get the last token of this sequence/step and cast to float32 before numpy()
                    layer_h = step_layers[layer_idx][0, -1, :].to(torch.float32).cpu().numpy()
                    layer_states.append(layer_h)
                
                # Stack to (n_layers, hidden_size)
                all_step_states.append(np.stack(layer_states))
                
            # Average across all generation steps
            if all_step_states:
                hidden_states_pooled = np.mean(all_step_states, axis=0) # (n_layers, hidden_size)

        latency = time.time() - start_time
        return HFGenerationResult(
            text=clean_text,
            thought_block=thought_block,
            latency_sec=latency,
            model_name=self.model_id,
            hidden_states_pooled=hidden_states_pooled,
            generated_token_ids=generated_tokens
        )

    @staticmethod
    def _parse_thinking_block(text: str) -> Tuple[str, str]:
        THINK_PATTERN = re.compile(r'<think>(.*?)</think>', re.DOTALL | re.IGNORECASE)
        matches = THINK_PATTERN.findall(text)
        thought_block = "\n---\n".join(m.strip() for m in matches) if matches else ""
        clean_text = THINK_PATTERN.sub("", text).strip()
        return clean_text, thought_block

    @classmethod
    def unload(cls, model_id: str):
        if model_id in cls._cache:
            instance = cls._cache.pop(model_id)
            del instance.model
            del instance.tokenizer
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            logger.info(f"Model {model_id} unloaded and memory cleared.")
