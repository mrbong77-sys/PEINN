# PEINN v2.1 심사 대응 실험 (Applied Artificial Intelligence 269417082, 1차)

작성 2026-10-15 (KST). 계획 원본은 Paper_factory `peinn/v21_revision/00_plan.md`입니다. 이 문서는 실행 설계이고, 실험을 돌리기 전에 고정합니다.
코드 `v21r/`, 결과 `results/`, 문장·응답 원문은 `cache/`(커밋하지 않음). 위성 실행도 이 폴더의 `ops/`가 맡습니다(PEINN_v2와 격리, 교수님 2026-10-15 22:41 KST). 기동 `python revision/aai_r1/station.py`, 명령 파일 `commands/station.json`.

## 0. 결정 (교수님)

| 일시 (KST) | 결정 |
|---|---|
| 10-15 21:34 | 리뷰 요구를 모두 받아들여 보완 실험. 위성 무인 실행, Claude 감독 |
| 10-15 21:58 | 에너지 교정기 **격리 재학습**: 깨끗한 데이터로 재학습, 검증 분할로 문턱 재적합, 전부 재실행 |
| 10-15 (기본값, 이견 없으면 확정) | LoRA 미세 조정 비교는 qwen2.5-7B 하나. 극단 에너지 차단을 라우팅 맨 앞으로 |

## 1. 고칠 설계 오류

1. 에너지 교정기 학습 풀에 평가 벤치(HarmBench, Taxonomy, XSTest, Ethics)가 있었습니다. → 3절의 깨끗한 코퍼스로 다시 학습합니다.
2. NeMo 팔은 모든 호출이 내부 오류 또는 고정 거절이었습니다(9,260건 중 실제 답 0). → fastembed 임베딩을 미리 받고, 시험 문항 3건이 정상 답을 내야 실행합니다(PEINN_v2 docs/76에서 확인한 방식).
3. 라우팅 순서상 I가 높고 F가 낮은 입력은 극단 에너지 차단을 우회합니다. → 극단 에너지 조건을 맨 앞에 둡니다.
4. 문턱이 벤치 결과를 본 뒤의 기본값을 포함했습니다. → 모든 변형의 문턱을 같은 절차로 검증 분할에서 적합합니다(4절).
5. 기존 지연 기록은 채점 시간이 섞여 경로 비용으로 쓸 수 없습니다. → 게이트·생성 호출·토큰을 따로 잽니다(7절).

## 2. 실행 환경

- PEAOS 체크아웃(교수님 PC, `paths.peaos()`)의 벤치 함수·채점기·Ollama를 그대로 씁니다. 실행기는 `v21r/peaos_patches.py`의 패치(조회 라우터, 생성 저장본, Ollama 복구, langchain 호환)를 가져다 씁니다.
- 기반 모델: zephyr:7b, qwen2.5:7b-instruct, gemma4:e4b, gemma3:12b. 판정기 qwen3:32b(투고본과 같음). 생성 temperature 0.3, top-p 0.95, 고정 seed.
- 실행 횟수: 투고본 규약대로 HarmBench·GGB 10회, 나머지 5회.

## 3. 깨끗한 코퍼스

1. 대상: PEAOS의 v4 헤드 코퍼스(`pea_eval/data/ee_3class/v4/`의 학습·held-out 파일).
2. 검사: (a) PEAOS ProvenanceGuard(정확 일치 + 5-gram 포함률 > 0.5), 벤치 파일이 하나라도 없으면 멈춤 (b) 위 가드에 실제 하네스가 보낸 라우팅 문장 전부(기록 단계)와 그 조각 추가 (c) MiniLM 코사인 ≥ 0.92인 벤치 문장이 있으면 제외.
3. 분할: 학습 파일 = train. held-out 파일을 (source, polar) 층화로 반씩 나눠 val(조기 종료·문턱)과 test(보정·보고). seed 42.
4. 보고: 출처별 제외 수, 이유별 수. 문장은 저장소에 올리지 않고 sha만 올립니다.

## 4. 변형과 학습 (모두 같은 코퍼스, 같은 교사 라벨, seed 42)

특징: 감정 32 + MiniLM 384 + 원칙 384(헤드, 800차원), 감정 32 + mpnet 768(에너지). 원래 실행 코드로 계산합니다.

| 기호 | 변형 | 학습 | 라우팅 |
|---|---|---|---|
| A0 | 전체 PEINN | 헤드: 원 레시피(세 축 모두 지도하는 soft BCE: 라벨 없는 축의 자리표시 0도 음성으로 학습, 투고본 체크포인트 `n_sup` 1,880 = held-out 전부; I 가중 2.5, Adam 1e-3, 60에폭, val 손실 최소). 에너지: 원 레시피(focal BCE, 80에폭), 라벨 F ≥ 0.5 | 5계층 게이트(극단 에너지 먼저) |
| A1 | I 채널 없음 | T·F 두 출력 헤드 | Deliberation 없음 |
| A2 | softmax 3범주(안전/모호/유해) | 같은 특징·같은 용량, 교차 엔트로피. 라벨: F ≥ 0.5이고 F ≥ I면 유해, 아니면 I ≥ 0.5면 모호, 나머지 안전 | p(유해)를 F, p(모호)를 I 자리에 |
| A3 | 불확실성 라우팅 | 이진 유해 분류기(F ≥ 0.5) | \|p − 0.5\| ≤ δ이면 Deliberation (δ는 val에서 적합) |
| A4a/b/c/d | 고정 응답 전략 | 없음 | 항상 Direct / 항상 Deliberation / A0 차단 외 Direct / A0 차단 외 Deliberation |
| A5 | 감정 에너지 없음 | A0 헤드 | 에너지 조건 대신 F 문턱으로 차단, Soft 없음 |
| A6p | 원칙 앵커 없음 | 원칙 384 차원 빼고 재학습 | A0 게이트 |
| A6e | 감정 특징 없음 | 감정 32 차원 빼고 재학습 | A0 게이트 |
| A7 | 미세 조정 SBERT | MiniLM-L6 전체 미세 조정 + T/I/F 시그모이드, 같은 손실 | A0 게이트 |
| A8 | 보호 모델 LoRA | qwen2.5-7B, 같은 코퍼스·같은 교사 범주의 목표 응답(차단·숙고·직답)으로 LoRA (10절) | 라우터 없음(맨 프롬프트) |

## 5. 문턱 적합 (모든 변형 같은 절차, val만 씀)

- val 문항의 교사 범주: 유해(F ≥ 0.5), 딜레마(I ≥ 0.5, F < 0.5), 안전(나머지).
- 1단계(차단 문턱: 극단 에너지, harm 에너지 = soft 에너지, F): 논문 3.4절 목표 "유해 Hard-block ≥ 85%, 안전 Hard-block < 10%". 만족하는 조합 중 유해 Hard-block 최대. 없으면 유해 HB − 2 × 안전 HB 최대(투고본 `tune_neutro_gate` 점수와 같음).
- 2단계(Fref, I, Fblk, A3의 δ): 1단계를 고정하고 경로 비용 최소. 비용은 투고본 `train_neutro_head._route_cost` 기본값: 유해→직답 1, 안전→거절(HB·RR) 1, 유해→숙고 0.5, 안전→숙고 0.2, 딜레마→직답 0.6, 딜레마→거절 0.4.
- 곡선: 1단계의 "안전 Hard-block 상한"을 0.5, 1, 2, 5, 10, 15, 20, 30%로 바꿔 운영점을 여러 개 만듭니다(2단계는 다시 적합). 벤치 결과는 응답 행렬로 계산합니다(6절).
- 비교: 같은 UCR(XSTest 위험 순응, HarmBench·Taxonomy ASR 합)에서의 과잉 거부와 도덕 벤치 점수, 그리고 곡선 전체.

## 6. 응답 행렬

- 경로가 같으면 답도 같습니다(같은 기반 모델·문항·회차·seed). 그래서 PEINN 팔을 **경로를 강제한 다섯 번**(Hard-block, Reasoned-Refusal, Deliberation, Soft-reasoning, Direct-Answer)만 돌리고, 모든 변형과 운영점은 문항별 경로 조회로 결과를 냅니다.
- 1차 생성(원 요청 그대로)은 다섯 번 모두 같은 프롬프트라 저장본에서 재사용합니다. Vanilla 팔도 같은 프롬프트라 재사용됩니다.
- 함께 다시 돌리는 팔: Vanilla(H01·H05·H08·H11), R2D2(H02), NeMo(H03·H06·H09·H12, 수정판), Llama Guard(H14–H17). 한 기반 모델씩 생성 → 판정 순서.
- 표는 모두 이번 실행에서 나옵니다.

## 7. 기타 측정

- 경로별 비용: 경로마다 문항을 뽑아 게이트 계산 시간(CPU 1스레드·GPU), 생성 호출 수, 입력·출력 토큰, 생성 시간을 Ollama 응답 필드로 잽니다. Hard-block은 게이트 비용만.
- T/I/F 보정: test 분할에서 감독된 축마다 신뢰도 도표 10구간, ECE, Brier. XSTest 사람 라벨 대비 F의 보정.
- I 구성 개념: test에서 I와 F 예측 불확실성(엔트로피)의 순위상관, 출처 묶음별(딜레마·탈옥 틀·유해·무해) I 분포, 채널 간 순위상관.

## 8. 단계 (`python -m v21r STEP`, 위성 `ops.run`)

| 단계 | 내용 | 자원 |
|---|---|---|
| R | 기록: 모의 LLM으로 여섯 벤치를 규약 횟수만큼 돌려 라우팅 문장 수집, 투고본 시트와 문항 수 대조 | CPU |
| C | 코퍼스 격리 검사와 분할 | CPU |
| F | 특징 계산(코퍼스 + 벤치 문장) | GPU 소량 |
| T | 변형 학습(A0–A7) | GPU 소량 |
| Θ | 문턱 적합과 곡선 운영점, 벤치 결과를 보기 전에 푸시 | CPU |
| P | 경로표(변형 × 운영점 × 벤치 문장) | CPU |
| N | NeMo 시험 3건 | GPU |
| M | 응답 행렬 + 다른 팔, 기반 모델별 생성 → 판정 | GPU 대량 |
| A8 | LoRA 비교(10절): 목표 응답 생성 → 학습 → Ollama 모델 → 벤치. 본 실행에서는 0.5B 점검(`a8-check`)을 먼저 | GPU |
| K | 경로별 비용 측정 | GPU 소량 |
| A | 분석·표 | CPU |

M 단계 전에 생성·판정 호출 수와 예상 시간을 보고하고 교수님 확인을 받습니다(대규모 GPU 규칙).

## 9. 구현 세부 (코드 작성 때 정함, 결과 보기 전)

- **회차 seed:** 같은 요청(모델·프롬프트)의 k번째 호출에 seed 42 + k를 씁니다. 그래서 회차마다 답이 다르고(투고본의 회차별 시드와 같은 취지), 같은 회차는 태그가 달라도 같은 seed라 1차 생성이 재사용됩니다. 판정기는 seed 42 고정이고, 같은 질문·같은 답의 판정은 한 번만 하고 재사용합니다(`peaos_driver.seeds`).
- **행과 라우팅 문장 연결:** 실행기가 라우팅 문장의 sha1을 `neutro_posture` 끝에 붙입니다(`PEINN2_POSTURE_SHA`). 기록 단계에서 모든 벤치의 CSV 행이 기록된 문장에 연결되는지 셉니다(`record_stats.json`의 `rows_sha_recorded`).
- **1단계 적합:** 차단 조건(극단 에너지, 또는 harm 에너지와 F)만으로 유해·안전 Hard-block 비율을 셉니다. soft 에너지 문턱은 harm 에너지 문턱과 같게 둡니다(투고본과 같음).
- **비용표의 경로:** Hard-block·Reasoned-Refusal = 거절, Deliberation = 숙고, Soft-reasoning·Direct-Answer = 답함.
- **A3:** I 자리에 1 − 2|p − 0.5|를 넣어 같은 게이트로 띠를 적합합니다(δ = (1 − τ_I)/2). Fblk 조건은 적합 범위에 그대로 둡니다.
- **UCR:** HarmBench ASR, Taxonomy 위험 응답률, XSTest 위험 순응의 단순 평균. 세 값도 따로 보고합니다. ORR은 XSTest 안전 문항 과잉 거부입니다.
- **경로 비용:** "하네스" 값(평가가 실제로 한 호출 전부)과 "배치" 값(Hard-block은 게이트만; 하네스가 기록용으로 만드는 1차 답은 뺌)을 함께 둡니다. 토큰과 Ollama 시간은 같은 seed로 한 번 더 호출해 응답 필드에서 읽습니다.
- **승인 관문:** 본 실행은 N 단계 뒤 `M0-approval`에서 멈춥니다. 교수님 확인 후 `ops/run.py`의 `APPROVED_M`을 켜서 푸시하면 이어서 돕니다.
- **R2D2 모델(H02):** Ollama 라이브러리에 없으므로 `cais/zephyr_7b_r2d2`의 GGUF를 zephyr:7b와 같은 양자화(Q4_0, `hf.co/RichardErkhov/cais_-_zephyr_7b_r2d2-gguf:Q4_0`)로 받아, zephyr:7b의 채팅 템플릿·정지어·매개변수를 그대로 붙여 `zephyr-r2d2:latest`로 만듭니다(`common.ensure_r2d2`, 만든 Modelfile은 `results/r2d2_Modelfile`). 모델은 기반 모델마다 그 차례 직전에 받으므로, 한 모델이 없어도 앞 기반 모델은 멈추지 않습니다.
- **점검(`--check`):** qwen 하나, GGB·XSTest 1회로 모든 단계를 돌리고 결과를 `results/check/`에, 전체 호출 수·시간 추정을 `results/estimate_before_M.json`에 올립니다.

## 10. A8: 보호 모델 LoRA (자원 맞춘 미세 조정 비교, R1-4 b)

목적: 같은 감독(같은 코퍼스, 같은 교사 범주)을 라우터 대신 보호 모델의 가중치에 넣으면 어떻게 되는지를 봅니다. 추론 때는 라우터 없이 맨 프롬프트만 받습니다(Vanilla 팔 H05와 같은 호출).

1. **목표 응답:** 격리 코퍼스의 train·val 문항마다 교사 범주(5절)가 정하는 답을 붙입니다. 유해 → Hard-block 거절문(`HARD_BLOCK_RESPONSE`), 딜레마 → Deliberation 경로의 시스템 프롬프트로 qwen2.5:7b-instruct가 낸 답, 안전 → 같은 모델의 맨 답. 프롬프트는 벤치를 돌리는 PEAOS 체크아웃의 `prompt_builder`에서 읽습니다(`PEAOS_EE_ENGINE=neutro_v21`). 생성은 temperature 0.3, top-p 0.95, seed 42, 최대 512토큰.
2. **학습(`a8_train.py`):** `Qwen/Qwen2.5-7B-Instruct`(받은 스냅샷 해시를 보고서에 기록), 모델 자체 채팅 템플릿, 손실은 답 토큰만. LoRA rank 16, alpha 32, dropout 0.05, 주의·MLP 투영 7종 전부. AdamW 1e-4, 1에폭, 배치 4 × 누적 4, 코사인(워밍업 3%), 최대 1,024토큰, seed 42. 학습 전후 val 손실을 보고합니다. 어댑터를 기반 가중치에 합쳐 저장하고, 어댑터만 따로도 저장합니다.
3. **서빙:** 합친 모델을 qwen2.5:7b-instruct와 같은 양자화(q4_K_M)로 Ollama에 올리고, 그 모델의 채팅 템플릿·정지어·매개변수를 그대로 붙입니다(`qwen2.5-a8:latest`). 한 문항 시험 답이 비면 멈춥니다.
4. **벤치:** 투고본 규약(HarmBench·GGB 10회, 나머지 5회)으로 H05 팔을 돌리되 생성 모델만 A8 모델로 바꿉니다(`peaos_driver_a8.py --model-map`, 판정 호출은 그대로). 결과는 qwen 표의 방어 행 "A8"로 나옵니다.
5. **점검:** 본 실행은 7B 전에 `a8-check`(Qwen2.5-0.5B-Instruct, 범주별 8문항, GGB·XSTest 1회)로 전체 경로를 먼저 통과시킵니다.


## 11. 게이트 진단 (2026-10-16, 교수님 지시 08:13 KST)

- **증상:** 경로표(`results/routes_summary.json`)에서 A0 주 운영점이 XSTest 라우팅 문장 191개(안전 108, 위험 83) 가운데 133개를 Hard-block합니다. 따라서 안전 문장은 최소 50개가 막힙니다.
- **원칙:**
  - 원인을 정확히 진단하고, 교수님 확인을 받은 뒤에만 재학습합니다.
  - XSTest는 증상으로만 읽습니다. 문턱, 라벨, 모델을 XSTest에 맞추지 않습니다.
  - 고치는 근거는 코퍼스 안에서 찾습니다(라벨 오류, 출처별 차단).
- **진단 단계 `gate-diag`:** CPU만 쓰고 모델을 호출하지 않습니다. 개수와 통계만 남기고 문장은 남기지 않습니다(`v21r/gate_diag.py`).
  1. XSTest 문장이 어떤 차단 조건으로 막혔는지 셉니다. 차단 조건은 극단 에너지, 또는 harm 에너지와 F입니다. 격리·출하 E와 F의 AUROC도 냅니다.
  2. 출처별 라벨을 셉니다. F 라벨 유무, 에너지 라벨(F ≥ 0.5), polar, 그리고 둘의 불일치입니다. F 라벨이 없는 행은 자리표시 0이라 "안전"으로 학습됩니다.
  3. val+test 출처별로 E 분포와 주 운영점 차단 수를 냅니다.
  4. XSTest 문장마다 학습 이웃 5개를 찾고(mpnet 코사인), 그 출처와 에너지 라벨을 셉니다.
- **단계 순서:** matrix → nemo-doc → gate-diag-check(check 캐시 사전 시험) → gate-diag → **gate-review**(`REVIEWED_GATE`가 참이 될 때까지 멈춤) → a8-check → a8 → cost → analyze → release.
  - A8 목표 응답도 같은 교사 라벨을 쓰므로 진단 뒤로 미룹니다.
- **진단 결과와 결정 (2026-10-16 09:00–09:06 KST, `results/diag/gate_diag.md`):**
  - 원인 ①(구현 오류): 헤드를 2-of-3 마스크(neg_weight 0)로 학습해 F가 음성을 거의 보지 못했습니다. 투고본처럼 세 축 모두 지도하도록 고칩니다(`models.SHIPPED_NEG_W` = 1.0). A1, A6p, A6e, A7도 같습니다.
  - 원인 ②: 격리 에너지가 XSTest형 표현에 높게 반응합니다. 차단된 안전 문장의 학습 이웃 44%가 trick_safe입니다.
  - 결정(교수님, 결정 카드 "빼고 재학습"): XSTest 안전 문항의 범주를 참고해 만든 합성 출처 trick_safe, benign_harm_discuss를 코퍼스에서 뺍니다(`data.EXCLUDE_SOURCES`). 분할 뒤에 빼므로 다른 행의 분할은 바뀌지 않습니다. 평가 벤치 격리는 벤치를 보고 설계한 학습 출처까지 포함합니다.
  - 다시 돌리는 단계: split → train → thresholds → routes → gate-diag-check → gate-diag. 그다음 gate-review에서 다시 멈추고, 교수님 확인 뒤에만 행렬을 재개합니다. 이미 생성한 qwen, gemma4 답변은 다시 채점만 합니다.
- **재진단 결과 (09:13 KST):** A0 F의 XSTest AUROC 0.73 → 0.82(투고본 0.84), 안전 문장 F 중앙값 0.86 → 0.11. 교정기 val AUROC 0.970. 주 운영점 val: 유해 Hard-block 96.0%, 안전 9.9%. XSTest 안전 문장 차단 55/108은 대부분 극단 에너지(51) 조건입니다. 같은 조건에서 투고본 헤드·교정기(SHIPPED, XSTest 학습)도 XSTest 191문장 중 119개를 거절 경로로 보냅니다.
- **미리보기 `preview` (CPU):** 행렬이 끝난 기반 모델(qwen, gemma4)의 답을 새 게이트로 다시 채점해 벤치 지표를 냅니다(`results/analysis_preview/`). 생성 답변은 강제 계층별이라 게이트와 무관하므로 그대로 씁니다. 순서: gate-diag → preview-check → preview → gate-review.

## 12. 격리된 다양한 학습 자료와 헤드 학습 가중 (2026-10-16, 교수님 지시 09:26·09:28 KST)

- **배경:** 수정한 게이트(11절)는 val에서 목표를 맞추지만, 재채점한 XSTest 과잉 거절이 31–54%입니다(qwen, gemma4). XSTest형 합성 출처를 뺀 뒤 코퍼스에 유해해 보이는 무해 문장이 거의 없기 때문입니다(추론). CPEG의 "평가 벤치 문항 없음" 재학습(과잉 거절 평균 9.9%)은 공개 과잉 거절·적대 학습 자료를 썼습니다.
- **자료 (`v21r/supplement.py`, step `supplement`):** 여섯 평가 벤치가 아니고 XSTest를 보고 만들지 않은 공개 자료만 씁니다. 라벨은 각 자료의 것입니다(무해: T 1, I 0, F 0 / 유해: F 1). seed 42 표집, 분할은 출처·라벨별 80/10/10(v4 행의 분할은 그대로).
  - 무해: OR-Bench-80k 3,000, FalseReject train 2,000, PHTest harmless 500, CoCoNot contrast 최대 1,000, WildJailbreak train 적대 무해 1,000, WildGuardMix train 적대 무해 500.
  - 유해: OR-Bench-toxic 1,500, WildJailbreak train 적대 유해 1,000, WildGuardMix train 적대 유해 500.
  - 격리 검사(3절: 정확 일치, 5-gram 포함률, MiniLM 코사인 ≥ 0.92)가 라우팅 문장과 겹치는 행을 그대로 뺍니다.
- **헤드 학습 가중 (`models.ROW_WEIGHT`):** 행마다 sqrt(N / (K·n_출처)) 가중(train 평균 1). 작은 출처가 큰 출처에 묻히지 않게 하고, 한 출처가 경계를 정하지 않게 합니다. A0–A7 헤드, 교정기(클래스 가중과 곱), A7 미세 조정에 같게 씁니다.
- **사전 테스트:** 본 실행 전에 `supp-check`가 supplement → audit → features → split → train → thresholds → routes를 check 캐시에서 끝까지 돌립니다.
- **사전 기준 (결과 전에 정함):** 주 운영점에서 qwen, gemma4 재채점 XSTest ORR ≤ 15%, UCR ≤ 5%. val 목표(유해 Hard-block ≥ 85%, 안전 < 10%)는 그대로입니다. 판단은 val과 보충 자료 test 분할로 하고, XSTest 결과를 보고 자료나 가중을 고치지 않습니다. 기준을 못 맞추면 그대로 보고합니다.
- **GPU:** 특징 추출(수 분)만 씁니다. 응답 행렬은 교수님 확인 전에는 재개하지 않습니다(gate-review).
- **결과 (09:51 KST):** 주 운영점 qwen UCR 5.8% / ORR 26.4%, gemma4 4.7% / 29.6%. 사전 기준을 못 맞췄습니다(`results/analysis_preview/preview.md`).

## 13. 인코더 미세 조정 A0ft (2026-10-16, 교수님 결정 대기 중 준비)

- **근거(평가 벤치 아님):** 12절 결과에서 test 분할의 적대 형식 무해 문장(WildJailbreak, WildGuardMix)이 23–44% 막히고, v4의 유해 출처 라벨 0 행은 에너지가 높습니다. 고정 특징이 표면 주제를 따라가는 것으로 봅니다(추론). CPEG ablation에서도 주된 이득은 미세 조정 인코더였습니다.
- **구성 (`models.train_ft`, 변형 `A0ft`):** v2.1 망을 그대로 두고 문장 인코더만 끝까지 학습합니다.
  - 에너지: [감정 32 | mpnet 768] → 교정기. mpnet(all-mpnet-base-v2)을 미세 조정하고, 초점 BCE에 클래스·출처 가중을 씁니다. val AUROC로 고릅니다.
  - 헤드: [감정 32 | MiniLM 384 | 원칙 384] → Neutro Head. MiniLM(all-MiniLM-L6-v2)을 미세 조정하고, 세 축 모두 지도에 출처 가중을 씁니다. val 손실로 고릅니다.
  - 3에폭, 인코더 lr 2e-5, 출력층 lr 1e-3, 배치 32, 최대 256 토큰, seed 42.
- **비교 (결과 전에 정함, `gate_diag` 5절):** test 분할 집단별 거절 비율(Hard-block + Reasoned-Refusal)을 주 운영점에서 A0와 비교합니다. 집단은 v4 안전, v4 유해, 과잉 거절형 무해, 적대 무해, 보충 유해입니다.
  - A0ft를 PEINN으로 쓰는 조건: 과잉 거절형·적대 무해 거절이 함께 줄고, 유해 두 집단의 거절이 각각 2%p 넘게 줄지 않을 것.
  - XSTest와 벤치 재채점은 그 뒤에 한 번만 보고, 이것으로 구성을 확정합니다.

## 14. 목표: Llama Guard 동등 이상 (교수님 지시 2026-10-16 10:02 KST)

- **목표:** ORR과 ASR 모두 Llama Guard와 같거나 더 좋을 것. 특징과 학습을 목표에 이를 때까지 개선합니다.
- **반복 규칙 (평가 벤치 격리 유지):**
  - 개선은 평가 벤치가 아닌 검증 자료로만 판단합니다. 코퍼스 test 분할의 다섯 집단(v4 안전·유해, 과잉 거절형 무해, 적대 무해, 보충 유해)에서 Llama Guard 3 입력 판정(`dev-guard`)과 비교합니다.
  - 무해 집단은 거절이 같거나 적고, 유해 집단은 거절이 같거나 많으면 "동등"입니다(`gate_diag.parity`).
  - 평가 벤치 재채점(`preview`)은 동등에 이른 변형이 있을 때에만 합니다(`analyze.PREVIEW_NEEDS_DEV_PARITY`).
- **1차 반복 후보 (한 번에 학습):**
  - A0ft: mpnet·MiniLM 미세 조정(13절).
  - 에너지 인코더는 바꾸지 않습니다(교수님 지시 2026-10-16 10:21 KST). DeBERTa로 바꾼 변형은 빼고, mpnet·MiniLM은 그대로 두고 미세 조정만 합니다.
- **사전 테스트:** `supp-check`(check 캐시에서 새 학습 코드 포함 전 사슬)와 `dev-guard-check`(40행)를 먼저 돌립니다.

## 15. 2차 반복: 평이한 요청 보충 (2026-10-16 10:5x KST)

- **1차 결과:** A0ft@0.02가 코퍼스 test 다섯 집단에서 Llama Guard와 동등 이상이었지만, qwen·gemma4 재채점에서는 UCR 10.5·6.1%, ORR 12.8·15.2%로 Llama Guard(4.2·3.6%, 6.4·12.8%)에 못 미쳤습니다. HarmBench 500문항 중 175문항이 직접 응답으로 통과했습니다.
- **판단(추론):** 개발 집단의 유해 문장은 적대 형식과 v4 출처가 중심이라 평가 문항 대부분의 형식인 평이한 직접 요청이 적었습니다. 평이하지만 유해해 보이는 무해 문장도 적었습니다.
- **보충:** WildJailbreak train의 vanilla_benign 2,000·vanilla_harmful 2,000, WildGuardMix train의 비적대 무해 1,000·유해 1,000을 더합니다(seed 42, 자료 자체 라벨, 격리 감사 그대로). 두 자료는 CPEG 격리 학습에서도 썼습니다.
- **개발 집단:** 무해는 v4·과잉 거절형·적대·평이(새 vanilla 무해), 유해는 v4·평이(OR-Bench-toxic와 새 vanilla 유해)·적대로 나눕니다. 동등 판정과 평가 벤치 재채점 규칙은 14절과 같습니다.
