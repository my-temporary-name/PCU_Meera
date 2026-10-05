"""One time-series PNG per biomarker, with threshold bands from threshold_ranges_full.csv."""

import argparse
import csv
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

from v0_code.data import loaders
from v0_code.logic.threshold import age_on, select_row

INF = float("inf")
LINE = "#2a6f97"
REJECT = "#b3261e"
BAND_COLORS = {"normal": "#2e7d32", "borderline": "#f9a825", "abnormal": "#c62828"}
BAND_ALPHA = {"normal": 0.12, "borderline": 0.20, "abnormal": 0.09}


def _num(row: dict[str, str], key: str) -> float | None:
    return float(row[key]) if row.get(key, "") not in ("", None) else None


def bands(row: dict[str, str]) -> list[tuple[float, float, str]]:
    """Disjoint (low, high, kind) segments covering the whole axis, mirroring assign_status."""
    n_low, n_high = _num(row, "normal_low"), _num(row, "normal_high")
    b_low, b_high = _num(row, "borderline_low"), _num(row, "borderline_high")
    abn_high = _num(row, "abnormal_high")
    nl, nh = (n_low if n_low is not None else -INF), (n_high if n_high is not None else INF)

    out = [(nl, nh, "normal")]
    if nh != INF:
        if b_low is not None and b_high is not None and b_low >= nh:
            top = abn_high if abn_high is not None and abn_high > nh else b_high
            out += [(nh, top, "borderline"), (top, INF, "abnormal")]
        else:
            out.append((nh, INF, "abnormal"))
    if nl != -INF:
        if b_low is not None and b_high is not None and b_high < nl:
            out += [(b_low, nl, "borderline"), (-INF, b_low, "abnormal")]
        else:
            out.append((-INF, nl, "abnormal"))
    return out


def _read(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _ts(value: str) -> datetime:
    return datetime.fromisoformat(value).replace(tzinfo=None)


def plot_biomarker(
    biomarker: str,
    points: list[tuple[datetime, float]],
    rejected: list[tuple[datetime, float]],
    row: dict[str, str],
    out_path: Path,
) -> None:
    points.sort()
    xs, ys = [p[0] for p in points], [p[1] for p in points]

    fig, ax = plt.subplots(figsize=(11, 4.2))
    if len(points) <= 60:
        ax.plot(xs, ys, color=LINE, linewidth=1.6, marker="o", markersize=5)
    else:
        ax.plot(xs, ys, color=LINE, linewidth=0.7, alpha=0.9)

    lo, hi = min(ys), max(ys)
    pad = (hi - lo) * 0.12 or max(abs(hi) * 0.1, 1.0)
    y_min, y_max = lo - pad, hi + pad
    ax.set_ylim(y_min, y_max)

    for b_lo, b_hi, kind in bands(row):
        ax.axhspan(
            max(b_lo, y_min),
            min(b_hi, y_max),
            color=BAND_COLORS[kind],
            alpha=BAND_ALPHA[kind],
            linewidth=0,
            zorder=0,
        )

    off_axis = []
    for t, v in rejected:
        if y_min <= v <= y_max:
            ax.scatter([t], [v], color=REJECT, marker="x", s=40, zorder=3)
        else:
            off_axis.append(v)
    if off_axis:
        ax.text(
            0.995,
            0.97 if max(off_axis) > y_max else 0.03,
            f"{len(off_axis)} rejected reading(s) off-axis: {min(off_axis):g}–{max(off_axis):g}",
            transform=ax.transAxes,
            ha="right",
            va="top" if max(off_axis) > y_max else "bottom",
            color=REJECT,
            fontsize=8.5,
        )

    ax.set_title(
        f"{biomarker}  ({row['unit']}, thresholds: {row['age_group']})",
        loc="left",
        fontsize=12,
    )
    ax.set_ylabel(row["unit"])
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    plt.setp(ax.get_xticklabels(), rotation=0, fontsize=8.5)
    ax.grid(axis="y", color="#000000", alpha=0.08, linewidth=0.6)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)

    handles = [
        Patch(color=BAND_COLORS[k], alpha=BAND_ALPHA[k] * 2.2, label=label)
        for k, label in (("normal", "Normal"), ("borderline", "Borderline"), ("abnormal", "Abnormal"))
    ]
    if rejected:
        handles.append(
            plt.Line2D([], [], color=REJECT, marker="x", linestyle="", label="Rejected (implausible)")
        )
    ax.legend(handles=handles, loc="upper left", bbox_to_anchor=(0, -0.1), ncol=len(handles), frameon=False, fontsize=8.5)

    fig.tight_layout()
    fig.savefig(out_path, dpi=130)
    plt.close(fig)


def make_plots(data_dir: Path, ranges_dir: Path, output_dir: Path) -> list[Path]:
    threshold_rows = loaders.load_threshold_rows(ranges_dir)
    dob, sex = loaders.load_patient_facts(data_dir)
    evaluated = _read(output_dir / "threshold_evaluation_results.csv")
    filtered = _read(output_dir / "plausibility_filter_results.csv")

    points: dict[str, list[tuple[datetime, float]]] = defaultdict(list)
    for r in evaluated:
        points[r["biomarker"]].append((_ts(r["timestamp"]), float(r["value"])))

    rejected: dict[str, list[tuple[datetime, float]]] = defaultdict(list)
    for r in filtered:
        if r["filter_result"] != "PASS":
            rejected[r["biomarker"]].append((_ts(r["timestamp"]), float(r["raw_value"])))

    plots_dir = output_dir / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for biomarker, pts in sorted(points.items()):
        age = age_on(dob, max(p[0] for p in pts).isoformat())
        row = select_row(threshold_rows, biomarker, age, sex)
        if row is None:
            continue
        path = plots_dir / f"{biomarker}.png"
        plot_biomarker(biomarker, pts, rejected.get(biomarker, []), row, path)
        written.append(path)
    return written


def main() -> None:
    parser = argparse.ArgumentParser(description="Plot one time series per biomarker")
    parser.add_argument("--data-dir", default="final")
    parser.add_argument("--ranges-dir", default="ranges")
    parser.add_argument("--output-dir", default="output")
    args = parser.parse_args()

    out = Path(args.output_dir)
    if not (out / "threshold_evaluation_results.csv").exists():
        raise SystemExit("Run `uv run v0-code` first to produce the result CSVs.")
    written = make_plots(Path(args.data_dir), Path(args.ranges_dir), out)
    print(f"Wrote {len(written)} plots to {out / 'plots'}")
