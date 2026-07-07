"""
PEINN — Logit Lens Heatmap Visualizer (Calibrated Visualization Edition)
"""

import logging
import re
from pathlib import Path
from typing import Optional, List, Dict
import warnings

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import matplotlib.patches as patches

warnings.filterwarnings("ignore", category=UserWarning, module="matplotlib")
logger = logging.getLogger("peinn.logit_lens.visualizer")

def _setup_fonts():
    font_candidates = ["Noto Sans CJK KR", "Noto Sans CJK JP", "DejaVu Sans", "NanumGothic"]
    extra_paths = [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    ]
    for path in extra_paths:
        if Path(path).exists():
            try: fm.fontManager.addfont(path)
            except: pass
    available = [f.name for f in fm.fontManager.ttflist]
    for cand in font_candidates:
        if any(cand in f for f in available):
            matplotlib.rc('font', family=cand)
            return True
    return False

_setup_fonts()
matplotlib.rcParams['axes.unicode_minus'] = False
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output" / "logit_lens"

# 폰트가 렌더 못 하는 글리프(아랍/히브리/태국/이모지/희귀)를 '·'로 치환해 □ 박스 제거.
# 허용: ASCII, Latin 확장(악센트), 공통 구두점, CJK/가나/한글.
_ALLOWED_GLYPH = re.compile(
    r"[^"
    r" -~"   # ASCII printable
    r"¡-ſ"   # Latin-1 + Latin Extended-A
    r"‐-‧"   # dashes/quotes/…
    r"　-ヿ"   # CJK punct, Hiragana, Katakana
    r"㐀-鿿"   # CJK Unified (+ ext A)
    r"가-힣"   # Hangul
    r"↵→…"
    r"]"
)


def _safe_glyph(s: str) -> str:
    return _ALLOWED_GLYPH.sub("·", s)


def _truncate_token(tok: str, max_len: int = 12) -> str:
    tok = tok.replace(" ", " ").replace("\n", "↵").replace("\t", "→").replace("$", "\\$")
    tok = _safe_glyph(tok)
    if len(tok) > max_len: return tok[:max_len-1] + "…"
    return tok

def plot_sentence_heatmaps(result, start, end, label, mode="entropy", output_dir=None, file_stem=None, top_layers=0):
    """
    특정 문장 구간의 레이어×토큰 히트맵을 생성합니다(교정된 로짓 렌즈).

    output_dir : Path|None. None이면 모듈 기본 OUTPUT_DIR 사용.
    file_stem  : str|None. 지정 시 파일명을 `{file_stem}_{mode}.png`로 강제.
    top_layers : int. >0이면 출력에 가까운 상위 N개 레이어만 표시(논문 figure용; 0=전체).
    """
    out_root = Path(output_dir) if output_dir else OUTPUT_DIR
    out_root.mkdir(parents=True, exist_ok=True)

    num_layers_full = result.num_layers
    if top_layers and 0 < top_layers < num_layers_full:
        layers_subset = list(range(num_layers_full - top_layers, num_layers_full))  # 상위 N (output 쪽)
    else:
        layers_subset = list(range(num_layers_full))

    # Causal Alignment (i -> i+1)
    data_start = max(0, start - 1)
    data_end = max(1, end - 1)

    data = result.entropy if mode == "entropy" else result.top1_probs
    plot_data = data[layers_subset, data_start:data_end]
    num_layers_disp = len(layers_subset)
    display_len = data_end - data_start

    if display_len == 0: return

    # 사이즈: 표시 레이어 수에 비례(상위 N만이면 짧게)
    fig, ax = plt.subplots(figsize=(max(15, display_len * 1.2), max(5, num_layers_disp * 0.62)))
    cmap = plt.cm.RdBu_r if mode == "entropy" else plt.cm.YlOrRd
    vmin, vmax = (0, 10.0) if mode == "entropy" else (0, 1.0)
    
    im = ax.imshow(plot_data, aspect="auto", cmap=cmap, vmin=vmin, vmax=vmax, interpolation="nearest", origin="lower")
    
    for i, orig_layer_idx in enumerate(layers_subset):
        for j in range(display_len):
            h_pos = data_start + j
            
            # 정답 토큰의 랭크 확인
            rank = result.target_ranks[orig_layer_idx, h_pos]
            pred_tok = result.argmax_tokens[orig_layer_idx][h_pos]
            
            # 랭크 기반 정밀 하이라이트 (Rank 1: 선명, Rank 2~5: 중간, Rank 6~15: 연하게)
            highlight_color = None
            alpha = 0.0
            
            if rank == 1:
                highlight_color = "cyan" if mode == "entropy" else "lime"
                alpha = 0.8
            elif 2 <= rank <= 5:
                highlight_color = "deepskyblue" if mode == "entropy" else "yellow"
                alpha = 0.4
            elif 6 <= rank <= 15:
                highlight_color = "lightskyblue" if mode == "entropy" else "gold"
                alpha = 0.2
            
            if highlight_color:
                rect = patches.Rectangle((j - 0.5, i - 0.5), 1, 1, linewidth=1, edgecolor='white', 
                                        facecolor=highlight_color, alpha=alpha, zorder=1)
                ax.add_patch(rect)
            
            tok_disp = _truncate_token(pred_tok, max_len=9)
            val = plot_data[i, j]
            
            # 텍스트 색상 및 강조
            if rank == 1:
                text_color, weight = "black", "bold"
            elif val < (vmin + (vmax-vmin)*0.3) or val > (vmin + (vmax-vmin)*0.7):
                text_color, weight = "white", "normal"
            else:
                text_color, weight = "black", "normal"
            
            ax.text(j, i, tok_disp, ha="center", va="center", fontsize=8.5, color=text_color, 
                    fontweight=weight, zorder=2)

    # 축 설정
    x_labels = []
    for k in range(display_len):
        target_idx = data_start + k + 1
        if target_idx < len(result.input_tokens):
            t = result.input_tokens[target_idx]
            x_labels.append(f"[{target_idx}]\n{_truncate_token(t)}")
        else: x_labels.append("")
            
    ax.set_xticks(range(display_len))
    ax.set_xticklabels(x_labels, rotation=0, fontsize=11, fontweight="bold")
    
    # y축: 표시 행(0..num_layers_disp-1) → 실제 레이어 인덱스(layers_subset) 매핑
    step = 5 if num_layers_disp > 14 else 2
    tick_pos = list(range(0, num_layers_disp, step))
    if (num_layers_disp - 1) not in tick_pos: tick_pos.append(num_layers_disp - 1)
    y_labels = [("output" if layers_subset[p] == num_layers_full - 1 else str(layers_subset[p])) for p in tick_pos]
    ax.set_yticks(tick_pos)
    ax.set_yticklabels(y_labels, fontsize=10)
    
    title = f"{result.arm_id} | {label} | {mode.upper()}\n(Highlights: Rank 1=Solid, Rank 2-5=Med, Rank 6-15=Light)"
    ax.set_title(title, fontsize=20, fontweight="bold", pad=25)
    
    plt.colorbar(im, ax=ax, label=mode.capitalize(), shrink=0.7)
    
    if file_stem:
        out_path = out_root / f"{file_stem}_{mode}.png"
    else:
        out_path = out_root / f"{mode}_{result.arm_id}_{label.lower()}_{result.item_id}.png"
    fig.savefig(out_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return out_path
