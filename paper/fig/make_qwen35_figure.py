#!/usr/bin/env python3
"""Plot the Qwen3.5-Flash model-role comparison from extracted paired counts."""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

HERE = Path(__file__).resolve().parent
model = json.loads((HERE / "paper_numbers.json").read_text())["models"]["qwen35"]
attack, clean = model["paired"]["total"], model["clean"]
colors = ["#8995a2", "#b16c4f", "#1f5c7a"]
labels = ["Native", "Qwen3.5 auditor (v3.7)", "Qwen3.7 auditor + L2 formats (v3.8)"]

plt.rcParams.update({"font.family": "sans-serif", "font.sans-serif": ["Arial", "DejaVu Sans"],
                     "font.size": 8, "pdf.fonttype": 42, "axes.spines.top": False,
                     "axes.spines.right": False, "axes.spines.left": False})
fig, (left, right) = plt.subplots(1, 2, figsize=(7.16, 2.22), sharex=True)
fig.subplots_adjust(left=.138, right=.985, bottom=.27, top=.86, wspace=.38)
for ax, title in [(left, f"(a) Under attack ({attack['n']:,} paired keys)"),
                  (right, f"(b) Clean ({clean['paired_n']} paired tasks)")]:
    ax.set_title(title, loc="left", fontweight="bold", fontsize=8.5, pad=7)
    ax.set_xlim(0, 114)
    ax.set_xticks([0, 25, 50, 75, 100])
    ax.set_xlabel("Rate (%)", labelpad=2)
    ax.set_ylim(-.52, 1.52)
    ax.tick_params(axis="both", length=0, pad=3)
    for tick in (25, 50, 75):
        ax.axvline(tick, color="#e3e7eb", linewidth=.7, zorder=0)

for y, (prefix, suffix) in enumerate([("asr", "Native ASR"), ("tsr", "TSR")]):
    n = attack["n"]
    for offset, color, key in zip([.15, -.15], colors, ("base", "dscg")):
        k = attack[f"{key}_{prefix}"]
        rate = 100 * k / n
        left.barh(y + offset, rate, .25, color=color)
        precision = 2 if prefix == "asr" else 1
        left.text(rate + 2, y + offset, f"{rate:.{precision}f}", va="center")
left.set_yticks([0, 1], ["Native ASR", "TSR"])

for y, arm, color in zip([1, .5, 0], ("baseline", "dscg", "mixed"), colors):
    record = clean[arm]
    rate = 100 * record["tsr"] / record["n"]
    right.barh(y, rate, .30, color=color)
    right.text(rate + 2, y, f"{record['tsr']}/{record['n']}", va="center")
right.set_yticks([0, .5, 1], ["Mixed", "Same model", "Native"])
fig.legend([Patch(facecolor=color) for color in colors], labels, loc="lower center",
           ncol=3, frameon=False, fontsize=7.7, bbox_to_anchor=(.52, .005))

assert abs(left.get_position().width - right.get_position().width) < 1e-6
assert left.get_position().y0 == right.get_position().y0
for suffix in ("pdf", "png"):
    fig.savefig(HERE / f"qwen35-configurations.{suffix}", dpi=400)
