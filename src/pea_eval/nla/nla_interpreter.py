# pea_eval/nla/nla_interpreter.py

import os
import torch
import numpy as np
import logging
from typing import Dict
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

try:
    from nla_lib.nla_inference import (
        load_nla_config,
        load_embedding_only,
        resolve_embed_scale,
        normalize_activation,
        inject_at_marked_positions,
        EXPLANATION_RE
    )
    NLA_LIB_AVAILABLE = True
except ImportError:
    NLA_LIB_AVAILABLE = False

logger = logging.getLogger("peaos.nla.nla_interpreter")

NLA_CHECKPOINT_MAP = {
    "Qwen/Qwen2.5-7B-Instruct": "kitft/nla-qwen2.5-7b-L20-av",
    "google/gemma-3-12b-it": "kitft/nla-gemma3-12b-L32-av",
}

class NLAInterpreter:
    _cache: Dict[str, "NLAInterpreter"] = {}

    @classmethod
    def get_instance(cls, base_model_id: str) -> "NLAInterpreter":
        if base_model_id not in cls._cache:
            cls._cache[base_model_id] = cls(base_model_id)
        return cls._cache[base_model_id]

    def __init__(self, base_model_id: str):
        self.base_model_id = base_model_id
        self.checkpoint = NLA_CHECKPOINT_MAP.get(base_model_id)
        
        if not self.checkpoint:
            logger.warning(f"No NLA checkpoint mapped for {base_model_id}")
            self.model = None
            return

        logger.info(f"Loading NLA AV model {self.checkpoint} in 4-bit...")
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        # Download or get cached local directory path from HF hub
        from huggingface_hub import snapshot_download
        local_dir = snapshot_download(repo_id=self.checkpoint)
        
        # Load tokenizer and sidecar config from the local directory
        self.tokenizer = AutoTokenizer.from_pretrained(local_dir, trust_remote_code=True, local_files_only=True)
        self.cfg = load_nla_config(local_dir, self.tokenizer)
        
        # Load embedding explicitly for injection
        self.embed = load_embedding_only(local_dir, dtype=torch.bfloat16).to(self.device)
        self.embed_scale = resolve_embed_scale(local_dir)
        
        # Load full model in 4-bit to fit in 2-4GB VRAM
        quantization_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4"
        )
        self.model = AutoModelForCausalLM.from_pretrained(
            local_dir,
            device_map=self.device,
            quantization_config=quantization_config,
            trust_remote_code=True,
            local_files_only=True
        )
        self.model.eval()
        logger.info(f"NLA AV {self.checkpoint} loaded.")

    def explain(
        self,
        hidden_states_pooled: np.ndarray,
        top_k_layers: int = 1,
        max_concepts: int = 10,
    ) -> str:
        """
        hidden_states_pooled: (n_layers, hidden_size)
        Extracts natural language concepts using the NLA AV model.
        """
        if not self.model or hidden_states_pooled is None or not NLA_LIB_AVAILABLE:
            return ""
            
        try:
            # For this AV architecture, it was trained on a specific layer (e.g. L20 or L32).
            # We just use the last layer of the hidden states provided or the mean of top_k_layers.
            if len(hidden_states_pooled.shape) == 2:
                v_raw = hidden_states_pooled[-top_k_layers:].mean(axis=0)
            else:
                v_raw = hidden_states_pooled
                
            v = torch.as_tensor(np.asarray(v_raw, dtype=np.float32))
            
            if v.numel() != self.cfg.d_model:
                logger.error(f"Hidden state size {v.numel()} != d_model {self.cfg.d_model}")
                return ""

            content = self.cfg.actor_prompt_template.format(
                injection_char=self.cfg.injection_char
            )
            input_ids = self.tokenizer.apply_chat_template(
                [{"role": "user", "content": content}],
                tokenize=True, add_generation_prompt=True,
            )
            if hasattr(input_ids, "keys") and "input_ids" in input_ids:
                input_ids = input_ids["input_ids"]
            ids_t = torch.tensor(input_ids, dtype=torch.long).unsqueeze(0)

            with torch.no_grad():
                embeds = (self.embed(ids_t.to(self.device)) * self.embed_scale).float()

            v_scaled = normalize_activation(v.float().view(1, -1), self.cfg.injection_scale)

            injected_embeds = inject_at_marked_positions(
                ids_t, embeds.cpu(), v_scaled,
                self.cfg.injection_token_id,
                self.cfg.injection_left_neighbor_id,
                self.cfg.injection_right_neighbor_id,
            ).to(device=self.model.device, dtype=torch.bfloat16)

            # Generate with inputs_embeds — attention_mask + pad_token_id 명시로 transformers
            # warning(repeated, 비결정 동작 잠재) 회피. inputs_embeds 사용 시 mask는 모두 1.
            attn_mask = torch.ones(
                injected_embeds.shape[:2], dtype=torch.long, device=injected_embeds.device
            )
            pad_id = self.tokenizer.pad_token_id
            if pad_id is None:
                pad_id = self.tokenizer.eos_token_id
            with torch.no_grad():
                outputs = self.model.generate(
                    inputs_embeds=injected_embeds,
                    attention_mask=attn_mask,
                    max_new_tokens=150,
                    do_sample=False,
                    pad_token_id=pad_id,
                )

            # outputs are generated token ids. Note that inputs_embeds doesn't include the input in outputs generally
            text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)

            # The explanation is usually within <explanation> tags
            import re
            m = EXPLANATION_RE.search(text)
            if m:
                explanation = m.group(1).strip()
            else:
                explanation = text.strip()
                
            # Convert the paragraph explanation into the requested format (concepts separated by semicolons)
            # Since the NLA AV generates paragraphs (e.g. "This vector describes..."), 
            # we do a simple heuristic summarization or just return the truncated text.
            # For exact "concept(high);..." formatting, we format the sentence.
            # To keep it safe and avoid another LLM call, we just return the raw explanation 
            # with spaces replaced by underscores (simulating concepts) or just the raw explanation text.
            # Returning raw explanation as it contains the semantic meaning.
            # Limiting length.
            return explanation[:500]

        except Exception as e:
            logger.error(f"NLA explain error: {e}")
            return ""

    @classmethod
    def unload(cls, base_model_id: str):
        if base_model_id in cls._cache:
            instance = cls._cache.pop(base_model_id)
            del instance.model
            del instance.embed
            del instance.tokenizer
            import gc
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            logger.info(f"NLA Interpreter for {base_model_id} unloaded.")
