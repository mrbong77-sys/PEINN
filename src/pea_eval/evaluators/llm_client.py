"""
PEINN UNESCO Eval — 평가 전용 LLM 클라이언트
Ollama(Local), Gemini(External), LM Studio(OpenAI-compatible) 호출을 통합 래핑합니다.

기존 integrations/ollama_client.py, integrations/gemini_api.py를 재사용하되,
평가 파이프라인에 맞는 간결한 인터페이스를 제공합니다.
"""
import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger("peinn.pea_eval.llm_client")


@dataclass
class LLMResponse:
    """LLM 호출 결과"""
    text: str
    latency_ms: int
    model_name: str
    thought_block: str = ""
    error: str = ""


class EvalLLMClient:
    """
    평가 파이프라인용 LLM 통합 클라이언트.

    - call_local(): Ollama 호출
    - call_external(): Gemini 호출
    - call_lmstudio(): LM Studio (OpenAI-compatible) 호출
    - reflect_local(): Ollama 반추 호출
    - reflect_external(): Gemini 반추 호출
    """

    def __init__(self, ollama_config=None, gemini_config=None, lmstudio_config=None):
        self._ollama_config = ollama_config
        self._gemini_config = gemini_config
        self._lmstudio_config = lmstudio_config
        self._ollama_client = None
        self._gemini_client = None
        # stat_batch 통제 변인 — set_eval_controls()로 설정
        self._eval_temperature: float | None = None  # None=config 기본값 사용
        self._eval_seed: int | None = None           # None=시드 미지정(자연 분산)
        self._current_model: str | None = None       # 현재 VRAM에 로드된 모델명

    def _get_ollama(self):
        """Ollama 클라이언트 (지연 초기화).
        PEAOS_VLLM_URL 환경변수가 설정되면 vLLM OpenAI-호환 어댑터를 대신 반환한다
        (드롭인 — call_local 등 호출자 코드는 영향 없음)."""
        if self._ollama_client is None:
            from integrations.vllm_openai_client import vllm_base_url, vllm_resolve_model
            cfg = self._ollama_config
            vurl = vllm_base_url()
            if vurl:
                from integrations.vllm_openai_client import VLLMOpenAIClient
                self._ollama_client = VLLMOpenAIClient(
                    base_url=vurl,
                    model=vllm_resolve_model(cfg.model),
                    temperature=cfg.temperature,
                    max_tokens=cfg.max_tokens,
                    timeout_seconds=cfg.timeout_seconds,
                )
                logger.info(f"vLLM 클라이언트 초기화 (default): {vurl} 모델={cfg.model}")
            else:
                from integrations.ollama_client import OllamaClient
                self._ollama_client = OllamaClient(
                    host=cfg.host,
                    port=cfg.port,
                    model=cfg.model,
                    temperature=cfg.temperature,
                    max_tokens=cfg.max_tokens,
                    timeout_seconds=cfg.timeout_seconds,
                )
                logger.info(
                    f"Ollama 클라이언트 초기화: {cfg.host}:{cfg.port} "
                    f"모델={cfg.model}"
                )
        return self._ollama_client

    def _get_gemini(self):
        """Gemini 클라이언트 (지연 초기화)"""
        if self._gemini_client is None:
            from integrations.gemini_api import GeminiClient
            cfg = self._gemini_config
            self._gemini_client = GeminiClient(
                api_key=cfg.api_key,
                model=cfg.model,
                temperature=cfg.temperature,
                max_tokens=cfg.max_tokens,
            )
            logger.info(
                f"Gemini 클라이언트 초기화: 모델={cfg.model}"
            )
        return self._gemini_client

    def _get_ollama_for_model(self, model_name: str):
        """특정 모델용 클라이언트 (캐싱). PEAOS_VLLM_URL 설정 시 vLLM 어댑터 반환."""
        if not hasattr(self, '_ollama_model_cache'):
            self._ollama_model_cache = {}
        if model_name not in self._ollama_model_cache:
            from integrations.vllm_openai_client import vllm_base_url, vllm_resolve_model
            cfg = self._ollama_config
            vurl = vllm_base_url()
            if vurl:
                from integrations.vllm_openai_client import VLLMOpenAIClient
                self._ollama_model_cache[model_name] = VLLMOpenAIClient(
                    base_url=vurl,
                    model=vllm_resolve_model(model_name),
                    temperature=cfg.temperature,
                    max_tokens=cfg.max_tokens,
                    timeout_seconds=cfg.timeout_seconds,
                )
                logger.info(f"vLLM 클라이언트 초기화 (override): {vurl} 모델={model_name}")
            else:
                from integrations.ollama_client import OllamaClient
                self._ollama_model_cache[model_name] = OllamaClient(
                    host=cfg.host,
                    port=cfg.port,
                    model=model_name,
                    temperature=cfg.temperature,
                    max_tokens=cfg.max_tokens,
                    timeout_seconds=cfg.timeout_seconds,
                )
                logger.info(f"Ollama 클라이언트 초기화 (override): 모델={model_name}")
        return self._ollama_model_cache[model_name]

    def set_eval_controls(
        self,
        temperature: float | None = None,
        seed: int | None = None,
    ):
        """
        stat_batch 통제 변인을 설정합니다.

        Args:
            temperature: 평가 고정 온도 (0.3 권장)
            seed: 난수 시드 (run마다 다른 값 부여)
        """
        self._eval_temperature = temperature
        self._eval_seed = seed
        logger.info(
            f"Eval 통제 변인 설정: temp={temperature}, seed={seed}"
        )

    async def call(
        self,
        backend: str,
        system_prompt: str,
        user_prompt: str,
        model_override: str = "",
        max_tokens: int | None = None,
        stop: list[str] | None = None,
        options: dict | None = None,
    ) -> LLMResponse:
        """
        백엔드 통합 디스패처.
        """
        if backend == "lmstudio":
            return await self.call_lmstudio(
                system_prompt, user_prompt,
                model_override=model_override,
                max_tokens=max_tokens,
                options=options,
            )
        elif backend == "local":
            return await self.call_local(
                system_prompt, user_prompt,
                model_override=model_override,
                max_tokens=max_tokens,
                stop=stop,
                options=options,
            )
        elif backend == "hf":
            return await self.call_hf(
                system_prompt, user_prompt,
                model_override=model_override,
                max_tokens=max_tokens,
                options=options,
            )
        else:
            return await self.call_external(system_prompt, user_prompt)

    async def call_hf(
        self,
        system_prompt: str,
        user_prompt: str,
        model_override: str = "",
        max_tokens: int | None = None,
        options: dict | None = None,
    ) -> LLMResponse:
        """HF Transformers (Local) 호출."""
        from pea_eval.backends.hf_backend import HFModelBackend
        
        actual_model = model_override or self._ollama_config.model # fallback to default if not provided
        backend = HFModelBackend.get_instance(actual_model, device="cuda")
        
        start = time.time()
        try:
            capture_nla = False
            thinking = False  # [Fix] Initialize with default value
            
            if options:
                capture_nla = options.get("capture_hidden_states", False)
                thinking = options.get("thinking", False)
                if "temperature" in options:
                    self._eval_temperature = options["temperature"]
                if "max_tokens" in options:
                    max_tokens = options["max_tokens"]

            # HOTFIX: HF default cap was 2048 → on Qwen-7B that's 30–60s per call
            # for typical safety prompts that only need ~100–300 tokens of refusal
            # text. With xstest's 45 items at HF concurrency=1, this added up to
            # 20–40min of apparent hang. Cap to 512 by default; analysis paths
            # (NLA / logit-lens) that need long completions pass explicit max_tokens.
            _max = max_tokens if max_tokens is not None else 512
            logger.info(
                f"  ▶ HF generate start: model={actual_model} "
                f"max_new_tokens={_max} capture_hidden={capture_nla}"
            )
            gen_result = await backend.generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_new_tokens=_max,
                temperature=self._eval_temperature or 0.3,
                thinking_mode=thinking,
                capture_hidden_states=capture_nla
            )
            
            latency = int((time.time() - start) * 1000)
            return LLMResponse(
                text=gen_result.text,
                thought_block=gen_result.thought_block,
                latency_ms=latency,
                model_name=actual_model,
                error=gen_result.error,
            )
        except Exception as e:
            latency = int((time.time() - start) * 1000)
            logger.error(f"HF 호출 실패 ({actual_model}): {e}")
            return LLMResponse(
                text="",
                latency_ms=latency,
                model_name=actual_model,
                error=str(e),
            )

    async def call_local(
        self,
        system_prompt: str,
        user_prompt: str,
        model_override: str = "",
        max_tokens: int | None = None,
        stop: list[str] | None = None,
        options: dict | None = None,
    ) -> LLMResponse:
        """
        Ollama (Local LLM) 호출.
        """
        if model_override:
            client = self._get_ollama_for_model(model_override)
            actual_model = model_override
        else:
            client = self._get_ollama()
            actual_model = self._ollama_config.model
        start = time.time()
        try:
            if options:
                if "temperature" in options:
                    self._eval_temperature = options["temperature"]
                if "max_tokens" in options:
                    max_tokens = options["max_tokens"]

            messages = [{"role": "user", "content": user_prompt}]

            # max_tokens 미지정 시 256으로 cap (HF 백엔드는 512지만 Ollama는
            # Spark Blackwell dynamic-batching 환경에서 슬롯당 6~8 tok/s까지
            # 떨어져 per-request 시간이 cap에 비례한다 — 관측: H11/gemma3:12b
            # Vanilla, 512 cap에서 0.05 req/s, slot당 80s).
            # XSTest/HarmBench refusal·judge JSON·간단 narrative 모두 256으로
            # 충분. 더 긴 답변이 필요한 모듈(unesco 등)은 prompt_builder의
            # client_options.max_tokens로 override.
            _max = max_tokens if max_tokens is not None else 256

            # Ollama 백엔드에서는 thinking 플래그를 전달하지 않는다 — 일부
            # llama.cpp 빌드(Gemma 신규 아키텍처 포함)가 unknown option으로
            # strict-reject해 500을 유발한다. <think> 태그 기반 reasoning은
            # 프롬프트 단에서 처리되며, HF 백엔드는 별도의 thinking_mode 경로를 쓴다.
            text = await client.chat(
                messages=messages,
                system_prompt=system_prompt,
                temperature=self._eval_temperature,
                max_tokens=_max,
                seed=self._eval_seed,
                stop=stop,
                keep_alive=options.get("keep_alive") if options else None,
            )
            
            # 사고 과정(Thinking Trace) 추출
            import re
            THINK_PATTERN = re.compile(r'<think>(.*?)</think>', re.DOTALL | re.IGNORECASE)
            matches = THINK_PATTERN.findall(text)
            thought_block = "\n---\n".join(m.strip() for m in matches) if matches else ""
            clean_text = THINK_PATTERN.sub("", text).strip()
            
            latency = int((time.time() - start) * 1000)
            return LLMResponse(
                text=clean_text,
                thought_block=thought_block,
                latency_ms=latency,
                model_name=actual_model,
            )
        except Exception as e:
            latency = int((time.time() - start) * 1000)
            logger.error(f"Ollama 호출 실패 ({actual_model}): {e}")
            return LLMResponse(
                text="",
                latency_ms=latency,
                model_name=actual_model,
                error=str(e),
            )

    async def call_lmstudio(
        self,
        system_prompt: str,
        user_prompt: str,
        model_override: str = "",
        max_tokens: int | None = None,
        options: dict | None = None,
    ) -> LLMResponse:
        """
        LM Studio 호출 (OpenAI-compatible /v1/chat/completions).
        """
        import httpx

        cfg = self._lmstudio_config
        if cfg is None:
            return LLMResponse(
                text="", latency_ms=0,
                model_name="lmstudio",
                error="LMStudioConfig not provided",
            )

        actual_model = model_override or cfg.model
        
        # options 적용
        thinking = False
        if options:
            thinking = options.get("thinking", False)
            if "temperature" in options:
                self._eval_temperature = options["temperature"]
            if "max_tokens" in options:
                max_tokens = options["max_tokens"]

        temperature = self._eval_temperature if self._eval_temperature is not None else cfg.temperature
        tokens = max_tokens or cfg.max_tokens

        url = f"{cfg.base_url}/chat/completions"
        payload = {
            "model": actual_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": tokens,
            "stream": False,
        }
        
        # thinking 플래그가 True면 payload에 추가 (지원하는 백엔드용)
        if thinking:
            payload["thinking"] = True

        if self._eval_seed is not None:
            payload["seed"] = self._eval_seed

        start = time.time()
        try:
            async with httpx.AsyncClient(timeout=cfg.timeout_seconds) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()

            # OpenAI 응답에서 텍스트 추출
            msg = data["choices"][0]["message"]
            text = msg.get("content", "") or ""

            # Gemma4 reasoning 모델: content가 비어있으면 reasoning_content 사용 (기존 백업용)
            if not text.strip() and msg.get("reasoning_content"):
                text = msg["reasoning_content"]
                logger.info(
                    f"LM Studio: content 비어있음 → reasoning_content 사용 "
                    f"({len(text)}자)"
                )

            latency = int((time.time() - start) * 1000)
            return LLMResponse(
                text=text,
                latency_ms=latency,
                model_name=actual_model,
            )
        except Exception as e:
            latency = int((time.time() - start) * 1000)
            logger.error(f"LM Studio 호출 실패 ({actual_model}): {e}")
            return LLMResponse(
                text="",
                latency_ms=latency,
                model_name=actual_model,
                error=str(e),
            )

    async def call_external(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> LLMResponse:
        """
        Gemini (External LLM) 호출.

        Args:
            system_prompt: 시스템 프롬프트
            user_prompt: 사용자 프롬프트

        Returns:
            LLMResponse
        """
        client = self._get_gemini()
        start = time.time()
        try:
            # Gemini는 단일 프롬프트로 전달
            full_prompt = f"[System]\n{system_prompt}\n\n[User]\n{user_prompt}"
            text = await client.generate(full_prompt)
            latency = int((time.time() - start) * 1000)
            return LLMResponse(
                text=text,
                latency_ms=latency,
                model_name=self._gemini_config.model,
            )
        except Exception as e:
            latency = int((time.time() - start) * 1000)
            logger.error(f"Gemini 호출 실패: {e}")
            return LLMResponse(
                text="",
                latency_ms=latency,
                model_name=self._gemini_config.model,
                error=str(e),
            )

    async def unload_model(self, model_name: str):
        """
        Ollama에서 특정 모델을 명시적으로 언로드합니다 (Swap용).
        keep_alive: 0 요청을 보냅니다.
        """
        if not model_name: return
        try:
            client = self._get_ollama_for_model(model_name)
            await client.chat(
                messages=[{"role": "user", "content": "unload"}],
                keep_alive=0
            )
            logger.info(f"Ollama 모델 언로드 완료: {model_name}")
        except Exception as e:
            logger.warning(f"모델 언로드 실패 ({model_name}): {e}")

    async def reflect_local(
        self,
        question: str,
        draft_answer: str,
        emotion_feedback: str,
        persona_prompt: str = "",
        round_number: int = 1,
    ) -> LLMResponse:
        """
        Ollama 반추 호출 — EE 피드백을 반영하여 답변 수정.

        기존 OllamaClient.reflect_with_emotion() 활용.
        """
        client = self._get_ollama()
        start = time.time()
        try:
            text = await client.reflect_with_emotion(
                question=question,
                draft_answer=draft_answer,
                emotion_feedback=emotion_feedback,
                persona_prompt=persona_prompt,
                round_number=round_number,
            )
            latency = int((time.time() - start) * 1000)
            return LLMResponse(
                text=text,
                latency_ms=latency,
                model_name=self._ollama_config.model,
            )
        except Exception as e:
            latency = int((time.time() - start) * 1000)
            logger.error(f"Ollama 반추 호출 실패: {e}")
            return LLMResponse(
                text=draft_answer,  # 실패 시 원본 유지
                latency_ms=latency,
                model_name=self._ollama_config.model,
                error=str(e),
            )

    async def reflect_external(
        self,
        question: str,
        draft_answer: str,
        emotion_feedback: str,
        persona_prompt: str = "",
        round_number: int = 1,
    ) -> LLMResponse:
        """
        Gemini 반추 호출 — EE 피드백을 반영하여 답변 수정.
        """
        client = self._get_gemini()
        start = time.time()
        try:
            prompt = (
                f"[System]\n{persona_prompt}\n\n"
                f"[Question]\n{question}\n\n"
                f"[Current Answer]\n{draft_answer}\n\n"
                f"[Emotion Engine Feedback - Reflection #{round_number}]\n"
                f"{emotion_feedback}\n\n"
                "Please refine your answer based on the above feedback.\n"
                "Core rules:\n"
                "1. Maintain one clear position throughout.\n"
                "2. Do not use emotion words directly; express them through tone and depth of reasoning.\n"
                "3. No evasive conclusions. Present a clear choice.\n"
                "4. Your answer must be at least 600 characters.\n"
                "5. End with a complete sentence. Do not cut off mid-sentence.\n"
                "6. Respond in English.\n"
            )
            text = await client.generate(prompt)
            latency = int((time.time() - start) * 1000)
            return LLMResponse(
                text=text,
                latency_ms=latency,
                model_name=self._gemini_config.model,
            )
        except Exception as e:
            latency = int((time.time() - start) * 1000)
            logger.error(f"Gemini 반추 호출 실패: {e}")
            return LLMResponse(
                text=draft_answer,
                latency_ms=latency,
                model_name=self._gemini_config.model,
                error=str(e),
            )

    async def reflect_lmstudio(
        self,
        question: str,
        draft_answer: str,
        emotion_feedback: str,
        persona_prompt: str = "",
        round_number: int = 1,
    ) -> LLMResponse:
        """LM Studio 반추 호출"""
        import httpx

        cfg = self._lmstudio_config
        if cfg is None:
            return LLMResponse(
                text=draft_answer, latency_ms=0,
                model_name="lmstudio",
                error="LMStudioConfig not provided",
            )

        actual_model = cfg.model
        is_gemma4 = "gemma-4" in actual_model.lower()

        url = "http://localhost:1234/v1/chat/completions"
        messages = [
            {"role": "system", "content": persona_prompt},
            {"role": "user", "content": question},
            {"role": "assistant", "content": draft_answer},
            {
                "role": "user",
                "content": (
                    f"[Emotion Engine Feedback - Reflection #{round_number}]\n"
                    f"{emotion_feedback}\n\n"
                    "Please refine your answer based on the above feedback.\n"
                    "Core rules:\n"
                    "1. Maintain one clear position throughout.\n"
                    "2. Do not use emotion words directly; express them through tone and depth of reasoning.\n"
                    "3. No evasive conclusions. Present a clear choice.\n"
                    "4. Your answer must be at least 600 characters.\n"
                    "5. End with a complete sentence. Do not cut off mid-sentence.\n"
                    "6. Respond in English.\n"
                )
            }
        ]

        payload = {
            "model": actual_model,
            "messages": messages,
            "temperature": self._eval_temperature if self._eval_temperature is not None else cfg.temperature,
            "max_tokens": cfg.max_tokens,
            "stream": False,
        }

        if self._eval_seed is not None:
            payload["seed"] = self._eval_seed

        start = time.time()
        try:
            async with httpx.AsyncClient(timeout=cfg.timeout_seconds) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()

            msg = data["choices"][0]["message"]
            text = msg.get("content", "") or ""

            if not text.strip() and msg.get("reasoning_content"):
                text = msg["reasoning_content"]

            latency = int((time.time() - start) * 1000)
            return LLMResponse(
                text=text,
                latency_ms=latency,
                model_name=actual_model,
            )
        except Exception as e:
            latency = int((time.time() - start) * 1000)
            logger.error(f"LM Studio 반추 호출 실패: {e}")
            return LLMResponse(
                text=draft_answer,
                latency_ms=latency,
                model_name=actual_model,
                error=str(e),
            )

    async def reflect(
        self,
        backend: str,
        question: str,
        draft_answer: str,
        emotion_feedback: str,
        persona_prompt: str = "",
        round_number: int = 1,
    ) -> LLMResponse:
        """백엔드 종류에 따라 반추(reflection) 호출을 디스패치합니다."""
        if backend == "local":
            return await self.reflect_local(
                question=question,
                draft_answer=draft_answer,
                emotion_feedback=emotion_feedback,
                persona_prompt=persona_prompt,
                round_number=round_number,
            )
        elif backend == "lmstudio":
            return await self.reflect_lmstudio(
                question=question,
                draft_answer=draft_answer,
                emotion_feedback=emotion_feedback,
                persona_prompt=persona_prompt,
                round_number=round_number,
            )
        else:
            return await self.reflect_external(
                question=question,
                draft_answer=draft_answer,
                emotion_feedback=emotion_feedback,
                persona_prompt=persona_prompt,
                round_number=round_number,
            )

    async def check_connections(self) -> dict:
        """Ollama, Gemini, LM Studio 연결 상태를 확인합니다."""
        results = {}

        # Ollama
        try:
            client = self._get_ollama()
            conn = await client.check_connection()
            results["ollama"] = conn
        except Exception as e:
            results["ollama"] = {"connected": False, "error": str(e)}

        # Gemini
        try:
            client = self._get_gemini()
            conn = await client.check_connection()
            results["gemini"] = conn
        except Exception as e:
            results["gemini"] = {"connected": False, "error": str(e)}

        # LM Studio
        if self._lmstudio_config:
            import httpx
            try:
                # /v1/models 엔드포인트로 연결 확인 + 로드된 모델 목록 조회
                async with httpx.AsyncClient(timeout=5) as client:
                    resp = await client.get("http://localhost:1234/v1/models")
                    resp.raise_for_status()
                    data = resp.json()
                    models = [m.get("id", "") for m in data.get("data", [])]
                results["lmstudio"] = {
                    "connected": True,
                    "models": models,
                }
                logger.info(f"LM Studio 연결 확인: {models}")
            except Exception as e:
                # 사용하지 않는 경우가 많으므로 실패해도 경고를 띄우지 않도록 결과를 생략합니다.
                pass

        return results

    async def close(self):
        """클라이언트 정리"""
        if self._ollama_client:
            await self._ollama_client.close()
        if hasattr(self, '_ollama_model_cache'):
            for client in self._ollama_model_cache.values():
                await client.close()
            self._ollama_model_cache.clear()
        # Gemini는 close 불필요

    async def unload_model(self, model_name: str):
        """
        Ollama에서 특정 모델을 VRAM에서 언로드합니다.
        keep_alive=0 으로 빈 generate 요청을 보내면 즉시 언로드됩니다.
        vLLM 모드에서는 모델 언로드 개념이 없으므로 HF 백엔드 정리만 수행한다.
        """
        from integrations.vllm_openai_client import vllm_base_url
        if vllm_base_url():
            try:
                from pea_eval.backends.hf_backend import HFModelBackend
                HFModelBackend.unload_all_models()
                import torch, gc
                gc.collect()
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except Exception as e:
                logger.warning(f"HF unload skipped under vLLM mode: {e}")
            self._current_model = None
            logger.info(f"🔄 vLLM 모드 — Ollama unload 건너뜀 ({model_name})")
            return

        import httpx
        import asyncio
        try:
            # 1. Ollama 모델 언로드 요청 (keep_alive=0)
            cfg = self._ollama_config
            base_url = f"{cfg.host}:{cfg.port}"
            async with httpx.AsyncClient(timeout=10) as client:
                await client.post(
                    f"{base_url}/api/generate",
                    json={"model": model_name, "keep_alive": 0},
                )

            # 2. /api/ps로 실제 unload 완료 polling — 5초 sleep 추측보다 정확.
            #    Ollama가 OLLAMA_MAX_LOADED_MODELS=2 등으로 캐싱하고 있으면 fire-
            #    and-forget만으로는 즉시 evict되지 않아 다음 모델과 VRAM 충돌 발생
            #    (관측: H07→H08 전환 시 Qwen 잔존 → Gemma4 부분 로드 → 일부 응답
            #    누락). 최대 20초 polling, 그 안에 evict되지 않으면 warning만 남김.
            max_wait_s = 20.0
            poll_interval = 0.5
            elapsed = 0.0
            evicted = False
            async with httpx.AsyncClient(timeout=5) as ps_client:
                while elapsed < max_wait_s:
                    try:
                        ps_resp = await ps_client.get(f"{base_url}/api/ps")
                        if ps_resp.status_code == 200:
                            loaded = {m.get("name", "") for m in ps_resp.json().get("models", [])}
                            if not any(model_name.split(":", 1)[0] in name for name in loaded):
                                evicted = True
                                break
                    except Exception:
                        pass
                    await asyncio.sleep(poll_interval)
                    elapsed += poll_interval

            if evicted:
                logger.info(f"🔄 Ollama unload 완료: {model_name} ({elapsed:.1f}s)")
            else:
                logger.warning(
                    f"⚠️ Ollama unload 대기 시간 초과 ({max_wait_s}s) — {model_name}이 "
                    f"여전히 /api/ps에 보입니다. OLLAMA_MAX_LOADED_MODELS=1을 고려하세요."
                )

            # 3. HF 백엔드 정리 및 VRAM 해제
            from pea_eval.backends.hf_backend import HFModelBackend
            HFModelBackend.unload_all_models()

            import torch
            import gc
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

            self._current_model = None

            # 4. 캐시에서도 제거
            if hasattr(self, '_ollama_model_cache') and model_name in self._ollama_model_cache:
                await self._ollama_model_cache[model_name].close()
                del self._ollama_model_cache[model_name]

        except Exception as e:
            logger.warning(f"모델 언로드 실패 ({model_name}): {e}")

    async def warmup_model(self, model_name: str):
        """모델 웜업 (Ollama/HF/vLLM State-aware)"""
        if self._current_model == model_name:
            logger.info(f"☕ 모델 {model_name} 이미 로드됨 (Warmup 건너뜀)")
            return

        from integrations.vllm_openai_client import vllm_base_url
        if vllm_base_url() and "/" not in model_name:
            # vLLM 모드: 모델은 vllm serve 시 이미 로드됨. 웜업 불필요.
            self._current_model = model_name
            logger.info(f"🔥 vLLM 백엔드 — {model_name} 웜업 불필요 (서버가 상주 로딩)")
            return

        logger.info(f"🔥 모델 웜업 시작: {model_name}")

        # [NEW] HF 모델 판별 (슬래시 포함 여부)
        if "/" in model_name:
            try:
                # HF 백엔드는 첫 호출 시 모델 로드 + CUDA JIT 컴파일 발생
                # 빈 프롬프트로 더미 호출 수행
                await self.call_hf(
                    system_prompt="Warmup",
                    user_prompt="Hi",
                    model_override=model_name,
                    max_tokens=1
                )
                self._current_model = model_name
                logger.info(f"🔥 HF 모델 웜업 완료 (First Inference OK): {model_name}")
            except Exception as e:
                logger.warning(f"HF 모델 웜업 실패 ({model_name}): {e}")
            return

        # Ollama 웜업: tag 존재 여부 preflight + 실패 시 hard-fail.
        # 이전 정책(warning만 찍고 진행)은 모델 로딩 실패를 evaluator가 알 수
        # 없게 만들어, 모든 prompt가 500을 받아 `[ERROR: ...]`로 저장되는 결과를
        # 초래했다 (H08/H09/H10 Gemma4-E4B 사례). 여기서 즉시 raise하여 호출자가
        # 해당 arm을 깔끔히 skip하거나 사용자에게 actionable error를 노출한다.
        import httpx
        cfg = self._ollama_config
        base_url = f"{cfg.host}:{cfg.port}"

        # 1. /api/tags로 모델이 실제 설치돼 있는지 확인 (404가 아닌, 잘못된 태그
        #    포함 케이스를 잡는다)
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                tags_resp = await client.get(f"{base_url}/api/tags")
                tags_resp.raise_for_status()
                installed = {m.get("name", "") for m in tags_resp.json().get("models", [])}
        except Exception as e:
            raise RuntimeError(
                f"Ollama /api/tags 접근 실패 — 서버가 살아있고 {base_url}로 응답하는지 확인하세요: {e}"
            ) from e

        # `gemma4:e4b`만 명시해도 일부 환경은 `:latest` 접미 등으로 변형되므로
        # prefix 매칭도 허용한다.
        def _is_installed(name: str) -> bool:
            if name in installed:
                return True
            head = name.split(":", 1)[0]
            return any(inst.split(":", 1)[0] == head for inst in installed)

        if not _is_installed(model_name):
            raise RuntimeError(
                f"Ollama에 모델 `{model_name}`이 설치되어 있지 않습니다. "
                f"`ollama pull {model_name}`을 실행하거나 arms YAML의 llm_model 태그를 "
                f"확인하세요. 현재 설치된 모델: {sorted(installed) or '(없음)'}"
            )

        # 2. 실제 generate 호출로 웜업 — empty prompt + keep_alive=5m
        try:
            async with httpx.AsyncClient(timeout=180) as client:
                resp = await client.post(
                    f"{base_url}/api/generate",
                    json={"model": model_name, "prompt": "", "keep_alive": "5m"},
                )
            if resp.status_code != 200:
                body = (resp.text or "")[:400].replace("\n", " ")
                raise RuntimeError(
                    f"Ollama 웜업 실패 ({model_name}): HTTP {resp.status_code} — {body}. "
                    f"`ollama run {model_name} 'hi'`로 단독 호출이 되는지, "
                    f"Ollama 버전이 해당 아키텍처를 지원하는지 확인하세요."
                )
            self._current_model = model_name
            logger.info(f"🔥 Ollama 모델 웜업 완료: {model_name}")
        except RuntimeError:
            raise
        except Exception as e:
            raise RuntimeError(f"Ollama 모델 웜업 실패 ({model_name}): {e}") from e
