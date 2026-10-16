# v2.1 심사 대응 무인 실행 상태: 실행 중

- 시각 2026-10-16 09:50:32 (UTC 2026-10-16 00:50:32), 시도 8, 비컨 #64 (주기 10분, 명령 확인 2분마다, 명령 파일 `revision/aai_r1/commands/run.json`)
- 실행 코드: 994fea1 v21r P: route tables of every variant and operating point (counts)
- 현재 단계: gate-diag (0.0분째)
- 마지막 출력 후: 0.0분
- GPU(사용 MiB, 전체 MiB, 사용률, 온도): 1565 MiB, 32607 MiB, 0 %, 38
- 다음 동작: 단계 진행
- 사유: 정기 보고
- 마지막으로 처리한 명령: 20261016T003308Z-rerun rerun (대기 끝, 재시도, 2026-10-16 00:34:03 UTC)
- 남은 단계: gate-diag; preview-check; preview; gate-review; matrix; nemo-doc; a8-check; a8; cost; analyze; release
- 끝난 단계(코드): record, nemo, approval, nemo-doc-early, supp-check, supplement, audit, unload-1, features, split, train, thresholds, routes, gate-diag-check

## 마지막 로그

```
    res["xstest"] = symptom(lab, th, a0, shp)
                    ~~~~~~~^^^^^^^^^^^^^^^^^^
  File "D:\Projects\PEINN\revision\aai_r1\v21r\gate_diag.py", line 95, in symptom
    t = th[cap]["th"]
        ~~^^^^^
KeyError: '0.005'

# 게이트 진단 (DESIGN.md 11)

주 운영점 0.1 문턱: {}

## 2. 출처별 라벨

| 출처 | 행 | F 라벨 있음 | 에너지 라벨 1 | polar F | polar F인데 라벨 0 | polar T인데 라벨 1 |
|---|---|---|---|---|---|---|

## 3. 출처별 에너지와 차단 (val + test, 주 운영점)

| 출처 | 행 | 라벨 0 차단 | 라벨 0 극단 E | 라벨 1 차단 | 라벨 0 E 중앙값 |
|---|---|---|---|---|---|

## 오류

```
Traceback (most recent call last):
  File "D:\Projects\PEINN\revision\aai_r1\v21r\gate_diag.py", line 214, in gate_diag
    res = run(check)
  File "D:\Projects\PEINN\revision\aai_r1\v21r\gate_diag.py", line 171, in run
    res["xstest"] = symptom(lab, th, a0, shp)
                    ~~~~~~~^^^^^^^^^^^^^^^^^^
  File "D:\Projects\PEINN\revision\aai_r1\v21r\gate_diag.py", line 95, in symptom
    t = th[cap]["th"]
        ~~^^^^^
KeyError: '0.005'

```


[v21r] ===== gate-diag: gate diagnosis: why the isolated gate blocks XSTest safe texts (CPU, counts only) =====
[ops] $ C:\Users\bojung\miniconda3\python.exe -u -m v21r gate-diag
```
