r"""Every figure in the paper, drawn at \columnwidth in one visual system.

Two things this file is opinionated about.

*Chart type follows the claim.* The category figures are paired bars because
they compare a count and an average across categories, which bars do well.
Nothing else here is a bar chart by default: concentration is a Lorenz curve, a
distribution whose spread is the finding is a strip plot, a two-regime split is
a scatter with iso-ratio guides, and a series over time is a line.

*One palette.* Everything uses seaborn's "crest" ramp, with a single coral
accent from its companion "flare" reserved for the series a reader should be
alarmed by. No figure introduces a hue of its own.

Drawn at 252pt (the elsarticle two-column \columnwidth) and included at
width=\linewidth, so 8pt labels render at 8pt. One chart per figure environment.
"""

import csv
import datetime
import json
import pathlib
import statistics

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from matplotlib import patheffects
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib.ticker import FuncFormatter, MaxNLocator

import stats

ROOT = stats.ROOT
OUT = ROOT.parent / "paper/figures"
PANEL_CSV = ROOT / "data/raw/t1_search_projects.csv"

COL = 3.49          # \columnwidth in inches
sns.set_theme(style="white")
plt.rcParams.update({
    "font.size": 8, "axes.labelsize": 8, "xtick.labelsize": 7.5,
    "ytick.labelsize": 7.5, "legend.fontsize": 7, "pdf.fonttype": 42,
    "axes.edgecolor": "#444444", "axes.linewidth": 0.8,
})

CREST = sns.color_palette("crest", 6)   # light green -> deep blue
INK, TEAL = CREST[5], CREST[3]          # #254b7f, #287a8c
MIST = "#a9c0dc"                        # a light tint of INK, for count bars
CORAL = sns.color_palette("flare", 6)[0]  # #e98d6b, the one warm accent
GREY = "#9a9a9a"
HALO = [patheffects.withStroke(linewidth=1.6, foreground="white")]


def save(fig, name):
    fig.savefig(OUT / name, format="pdf", bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)
    print(f"  wrote {name}")


def panel_rows():
    with PANEL_CSV.open(encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


gini = stats.gini


# --- the paired-bar pair, kept as bars and recoloured ------------------------

def paired_bars(labels, counts, values, *, count_label, value_label,
                count_axis, value_axis, value_fmt, tick_fmt, solid,
                height=2.45,
                rotation=0, legend_loc="upper right"):
    r"""A count on the left axis and a per-item value on the right, overlaid.

    This is the layout the category figures use and the one the comparison
    calls for: two quantities per category, on incomparable scales.
    """
    fig, ax1 = plt.subplots(figsize=(COL, height))
    x = np.arange(len(labels))
    width = 0.38

    ax1.bar(x - width / 2, counts, width, color=MIST, edgecolor="white",
            linewidth=0.7)
    ax2 = ax1.twinx()
    ax2.bar(x + width / 2, values, width, color=solid, edgecolor="white",
            linewidth=0.7)

    ax1.set_ylim(0, max(counts) * 1.28)
    ax2.set_ylim(0, max(values) * 1.28)
    ax1.yaxis.set_major_locator(MaxNLocator(integer=True, nbins=6))
    ax2.yaxis.set_major_formatter(FuncFormatter(lambda v, p: tick_fmt(v)))
    ax1.set_ylabel(count_axis)
    ax2.set_ylabel(value_axis)
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels, rotation=rotation,
                        ha="right" if rotation else "center")

    vtop = ax2.get_ylim()[1]
    ctop = ax1.get_ylim()[1]
    count_labels, value_labels = [], []
    for i, (c, v) in enumerate(zip(counts, values)):
        # Both labels go on ax2 so neither is painted under a bar.
        count_labels.append(ax2.annotate(
            f"{c:,.0f}", (i - width / 2, c / ctop * vtop), xytext=(0, 1.5),
            textcoords="offset points", ha="center", va="bottom", fontsize=6.2))
        value_labels.append(ax2.annotate(
            value_fmt(v), (i + width / 2, v), xytext=(0, 1.5),
            textcoords="offset points", ha="center", va="bottom", fontsize=6.2))

    ax1.legend(handles=[Patch(facecolor=MIST, label=count_label),
                        Patch(facecolor=solid, label=value_label)],
               loc=legend_loc, frameon=True, framealpha=0.95, borderpad=0.4)
    fig.tight_layout(pad=0.35)

    # A money label is wider than its bar pair, so it can run into a label of
    # its own group or of a neighbouring one. Counts stay on their bars; each
    # money label is lifted until it clears every label already placed.
    renderer = fig.canvas.get_renderer()
    gap = 2.5 * fig.dpi / 72                      # clearance between labels
    pad = lambda b: b.padded(gap)
    placed = [pad(a.get_window_extent(renderer)) for a in count_labels]
    for a in value_labels:
        dy = 1.5
        box = a.get_window_extent(renderer)
        while any(box.overlaps(p) for p in placed):
            dy += 1.5
            a.xyann = (0, dy)
            box = a.get_window_extent(renderer)
        placed.append(pad(box))
    return fig


# Display names. The taxonomy itself -- which slug belongs to which primary
# category, and which rows count as classified -- lives in stats.py, so a figure
# and the sentence beside it cannot disagree about the coding.
PRIMARY_NAME = {"incubation": "Incubation", "infrastructure": "Infrastructure",
                "financial": "Financial", "creative": "Creative"}
SUBCATEGORY = {
    "builder": "Builder", "launchpad": "Launchpad",
    "infrastructure": "Agent Protocol", "trust": "Trust Layer",
    "copilot": "AI Development", "defai": "DeFAI", "analytics": "Analytics",
    "game": "Game", "digital-twin": "Game",
    "content-creation": "Content", "rwa": "RWA",
}
NETWORK_NAMES = {
    "binance-smart-chain": "BNB Chain", "arbitrum-one": "Arbitrum",
    "polygon-pos": "Polygon", "optimistic-ethereum": "Optimism",
}
NETWORK_MIN = 10   # a lower floor puts more chains on the axis than fit


def fig_marketcap():
    """Project count and average market cap by primary category."""
    by = stats.by_primary(stats.cls())
    order = stats.PRIMARY_ORDER
    save(paired_bars(
        [PRIMARY_NAME[c] for c in order],
        [by[c]["n"] for c in order], [by[c]["mean"] for c in order],
        count_label="Projects", value_label="Avg market cap",
        count_axis="Number of Projects",
        value_axis="Avg Market Cap per Project",
        value_fmt=lambda v: f"${v/1e6:.1f}M",
        tick_fmt=lambda v: f"${v/1e6:.0f}M", solid=INK),
        "marketcap.pdf")


def fig_networks():
    """Project count and average market cap by blockchain network.

    A project deployed on several chains is counted on each, so the bars sum to
    deployments rather than to projects. Tokens CoinGecko lists with no platform
    are native coins of their own chain and are dropped rather than guessed at.
    """
    by = stats.by_platform(stats.cls())
    counts = {n: b["n"] for n, b in by.items()}
    mcap = {n: b["mcap"] for n, b in by.items()}
    small = [n for n, c in counts.items() if c < NETWORK_MIN]
    counts["Others"] = sum(counts.pop(n) for n in small)
    mcap["Others"] = sum(mcap.pop(n) for n in small)
    # "Others" is a residue, not a network: it reads as a rank when it sits
    # mid-axis, so it goes last regardless of size.
    order = sorted(counts, key=counts.get, reverse=True)
    order.append(order.pop(order.index("Others")))
    save(paired_bars(
        [NETWORK_NAMES.get(n, n.title()) for n in order],
        [counts[n] for n in order], [mcap[n] / counts[n] for n in order],
        count_label="Deployments", value_label="Avg market cap",
        count_axis="Number of Deployments",
        value_axis="Avg Market Cap per Deployment",
        value_fmt=lambda v: f"${v/1e6:.1f}M",
        tick_fmt=lambda v: f"${v/1e6:.0f}M", solid=INK,
        rotation=30),
        "networks.pdf")


# --- new figures -------------------------------------------------------------

def fig_lorenz():
    """Concentration at both timepoints, as Lorenz curves.

    A tier histogram shows where the tokens are; a Lorenz curve shows the
    inequality itself, puts both snapshots on one pair of axes, and makes the
    Gini coefficient something the reader can see rather than take on trust.
    """
    cohort = stats.read("t1_cohort")
    t1 = [r["t1_market_cap_usd"] for r in cohort["projects"]
          if (r["t1_market_cap_usd"] or 0) > 0]
    pop = stats.pop()
    t2 = [v for v in pop["values"] if v > 0]
    label_t1, label_t2 = cohort["t1_date"][:7], pop["date"][:7]

    fig, ax = plt.subplots(figsize=(COL, 2.7))
    ax.plot([0, 1], [0, 1], color=GREY, lw=0.9, ls=(0, (4, 3)), zorder=1)
    ax.annotate("perfect equality", (0.62, 0.62), rotation=38, fontsize=6.2,
                color=GREY, ha="center", va="bottom")

    for values, label, colour, ls in [
            (t1, f"{label_t1}  ({len(t1)} tokens)", TEAL, "--"),
            (t2, f"{label_t2}  ({len(t2)} tokens)", INK, "-")]:
        v = np.sort(np.asarray(values, dtype=float))
        cum = np.concatenate([[0], np.cumsum(v) / v.sum()])
        share = np.linspace(0, 1, len(v) + 1)
        ax.plot(share, cum, color=colour, lw=1.5, ls=ls, zorder=3,
                label=f"{label},  Gini {gini(v):.3f}")
        if ls == "-":
            ax.fill_between(share, cum, share, color=colour, alpha=0.07,
                            zorder=2)

    # The top decile is the statistic the original paper reported, so mark it.
    ax.axvline(0.9, color=GREY, lw=0.7, ls=":", zorder=1)
    for values, colour, dy in [(t1, TEAL, 6), (t2, INK, 6)]:
        v = np.sort(np.asarray(values, dtype=float))
        top = v[int(np.ceil(0.9 * len(v))):].sum() / v.sum()
        ax.annotate(f"top 10% hold {top*100:.1f}%", (0.9, 1 - top),
                    xytext=(-8, dy), textcoords="offset points", ha="right",
                    fontsize=6.3, color=colour, path_effects=HALO)

    ax.set_xlabel("Cumulative share of tokens (poorest first)")
    ax.set_ylabel("Cumulative share of market cap")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, p: f"{v*100:.0f}%"))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, p: f"{v*100:.0f}%"))
    ax.legend(loc="upper left", frameon=False, handlelength=1.8)
    fig.tight_layout(pad=0.35)
    save(fig, "mcap_lorenz.pdf")
    print(f"  T1 gini={gini(t1):.3f} n={len(t1)}; T2 gini={gini(t2):.3f} "
          f"n={len(t2)}")


def fig_panel_retention():
    """Per-project value retention by subcategory, as a strip plot.

    The finding is the spread, not the average: a bar of medians would hide
    that every subcategory contains both survivors and near-total losses.
    """
    by_cat = {}
    for k, v in stats.panel_by_subcategory().items():
        by_cat.setdefault(SUBCATEGORY[k], []).extend(v["retention"])
    keep = {c: v for c, v in by_cat.items() if len(v) >= 3}
    order = sorted(keep, key=lambda c: statistics.median(keep[c]))

    fig, ax = plt.subplots(figsize=(COL, 2.9))
    rng = np.random.default_rng(0)
    for i, cat in enumerate(order):
        v = np.asarray(keep[cat])
        ax.scatter(v, i + rng.uniform(-0.17, 0.17, len(v)), s=11,
                   color=TEAL, alpha=0.7, linewidths=0, zorder=3)
        med = statistics.median(v)
        ax.plot([med], [i], marker="|", ms=9, mew=2.0, color=INK, zorder=4)
        ax.annotate(f"n={len(v)}", (1.0, i), xytext=(4, 0), xycoords=("axes fraction", "data"),
                    textcoords="offset points", va="center", fontsize=6.2,
                    color=GREY, annotation_clip=False)

    ax.axvline(1.0, color=CORAL, lw=0.9, ls=(0, (3, 2)), zorder=2)
    ax.annotate("no change", (1.0, len(order) - 0.35), xytext=(3, 0),
                textcoords="offset points", fontsize=6.3, color=CORAL,
                va="center")
    ax.annotate("median", (statistics.median(keep[order[-1]]), len(order) - 0.35),
                xytext=(-3, 0), textcoords="offset points", ha="right",
                va="center", fontsize=6.3, color=INK)
    ax.set_xscale("log")
    ax.set_xlim(2e-3, 3e1)
    ax.set_xticks([0.01, 0.1, 1, 10])
    ax.set_xticklabels(["0.01x", "0.1x", "1x", "10x"])
    ax.set_yticks(range(len(order)))
    ax.set_yticklabels(order)
    t1 = datetime.date.fromisoformat(stats.coh()["t1_date"])
    ax.set_xlabel(f"Value retained since {t1:%B %Y} (log scale)")
    ax.set_ylim(-0.6, len(order) - 0.2)
    ax.grid(axis="x", color="#e8e8e8", lw=0.6, zorder=0)
    ax.set_axisbelow(True)
    fig.tight_layout(pad=0.35)
    save(fig, "panel_retention.pdf")
    for c in reversed(order):
        print(f"  {c:16s} n={len(keep[c]):2d} "
              f"median={statistics.median(keep[c]):.3f}x")


# Hand-placed value labels for fig_x402, keyed by month:
# (text, (dx, dy) in points, ha, va, anchor). Both large months sit above their
# marker where the panel is empty; the rest form a row under the baseline,
# because above the markers they land on the steep segments into and out of
# December or inside the bars.
X402_VALUE_LABELS = {
    "2025-11": ("$528",    (0, -4), "center", "top",    "axis"),
    "2025-12": ("$108.7k", (0,  6), "center", "bottom", "point"),
    "2026-01": ("$279",    (0, -4), "center", "top",    "axis"),
    "2026-02": ("$1.4k",   (0, -4), "center", "top",    "axis"),
    "2026-03": ("$326",    (0, -4), "center", "top",    "axis"),
    "2026-04": ("$363",    (0, -4), "center", "top",    "axis"),
    "2026-05": ("$18.5k",  (5,  4), "left",   "bottom", "point"),
    "2026-06": ("$94",     (0, -4), "center", "top",    "axis"),
    "2026-07": ("$39",     (0, -4), "center", "top",    "axis"),
    "2026-08": ("$10",     (0, -4), "center", "top",    "axis"),
}


def fig_x402():
    """x402 settlement count against value settled, by month.

    Count is a monthly total, so bars; value is a level compared across months,
    so a line. The value axis is linear on purpose: December 2025 really is
    three orders of magnitude above every other month, and the prose explains
    why (a single day of self-cycling transfers). A log axis would flatten the
    one gap the figure exists to show.
    """
    rows = json.loads((ROOT / "data/processed/x402_monthly.json").read_text())
    months = [r["month"] for r in rows]
    x = np.arange(len(rows))

    fig, ax1 = plt.subplots(figsize=(COL, 2.7))
    ax1.bar(x, [r["settlements"] for r in rows], 0.6, color=MIST, alpha=0.75,
            edgecolor="white", linewidth=0.8, zorder=2)
    ax1.set_ylabel("Settlements")
    ax1.set_ylim(0, 300000)
    ax1.yaxis.set_major_formatter(FuncFormatter(lambda v, p: f"{v/1e3:.0f}k"))

    ax2 = ax1.twinx()
    ax2.plot(x, [r["usd"] for r in rows], color=CORAL, lw=1.4, marker="o",
             ms=3.6, zorder=4)
    ax2.set_ylim(0, max(r["usd"] for r in rows) * 1.22)
    ax2.set_ylabel("Value settled (USD)")
    ax2.yaxis.set_major_formatter(FuncFormatter(
        lambda v, p: f"${v/1e3:.0f}k" if v >= 1e3 else f"${v:,.0f}"))
    # Every month is labelled, and the placement is by hand: at linear scale
    # eight of the ten collapse onto the axis, and no single rule puts all ten
    # somewhere legible. "point" hangs the label on the marker, "axis" drops it
    # into a row beneath the baseline, clear of both the line and the bars.
    for i, r in enumerate(rows):
        text, (dx, dy), ha, va, anchor = X402_VALUE_LABELS[r["month"]]
        ax2.annotate(text, (i, r["usd"] if anchor == "point" else 0),
                     xytext=(dx, dy), textcoords="offset points",
                     ha=ha, va=va, fontsize=6.0, color=CORAL,
                     path_effects=HALO if anchor == "point" else None)

    # Drawn on ax2 (in ax1's coordinates) so the value line cannot cover them:
    # the twin axes is painted on top whatever z-order the labels are given.
    ctop = ax1.get_ylim()[1]
    for i, r in enumerate(rows):
        n = r["settlements"]
        ax2.annotate(f"{n/1e3:.0f}k" if n >= 1000 else f"{n}",
                     (i, n / ctop), xycoords=(ax1.transData, ax1.transAxes),
                     xytext=(0, 2.5), textcoords="offset points", ha="center",
                     va="bottom", fontsize=6.2, path_effects=HALO)
    ax1.set_xticks(x)
    ax1.set_xticklabels(months, rotation=45, ha="right")
    ax1.legend(handles=[
        Patch(facecolor=MIST, alpha=0.75, label="Settlements"),
        Line2D([], [], color=CORAL, lw=1.4, marker="o", ms=3.6,
               label="Value settled"),
    ], loc="upper right", frameon=True, framealpha=0.95, borderpad=0.4)
    fig.tight_layout(pad=0.35)
    save(fig, "x402_monthly.pdf")


def fig_erc8004():
    """Registrations against registrants, per chain, on log-log axes.

    The claim is that chains fall into two regimes by registrations-per-address,
    and a ratio is a slope. Iso-ratio guides make each chain's regime readable
    directly off the plot; paired bars only let the reader compare heights.
    """
    rows = json.loads((ROOT / "data/processed/erc8004_chains.json").read_text())

    # Hand-placed so the labels do not collide; the clusters are tight.
    NUDGE = {"avalanche": (-8, 2, "right"), "abstract": (-9, 0, "right"),
             "arbitrum": (8, 0, "left"), "optimism": (-6, -3, "right"),
             "polygon": (7, -3, "left"), "gnosis": (8, 0, "left"),
             "celo": (-7, 0, "right"), "bnb": (-2, -14, "center"),
             "base": (0, 9, "center"), "megaeth": (0, 8, "center"),
             "ethereum": (9, 0, "left"),
             "monad": (0, 8, "center")}

    fig, ax = plt.subplots(figsize=(COL, 2.9))
    xmax, ymax = 8e5, 3e6
    for ratio, note in [(1, "1 per address"), (10, "10x"), (40, "40x")]:
        ax.plot([10, xmax], [10 * ratio, xmax * ratio], color=GREY, lw=0.6,
                ls=":", zorder=1)
        # Label each guide where it leaves the axes, whichever edge that is.
        ex, ey = min(xmax, ymax / ratio), min(ymax, xmax * ratio)
        ax.annotate(note, (ex, ey), xytext=(-4, -4),
                    textcoords="offset points", ha="right", va="top",
                    fontsize=6.0, color=GREY, path_effects=HALO)

    for r in rows:
        name = r["chain"].replace("_c", "")
        n, k = r["registrants"], r["registrations"]
        sybil = k / n > 10
        ax.scatter(n, k, s=np.sqrt(k) * 0.9,
                   color=CORAL if sybil else INK, alpha=0.75, linewidths=0,
                   zorder=3)
        dx, dy, ha = NUDGE.get(name, (0, 7, "center"))
        ax.annotate(name, (n, k), xytext=(dx, dy), textcoords="offset points",
                    ha=ha, va="center", fontsize=6.2,
                    color=CORAL if sybil else INK, path_effects=HALO, zorder=4)

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(15, 8e5)
    ax.set_ylim(250, 3e6)
    ax.set_xlabel("Distinct registrant addresses (log)")
    ax.set_ylabel("Identity registrations (log)")
    ax.grid(color="#ececec", lw=0.6, zorder=0)
    ax.set_axisbelow(True)
    ax.legend(handles=[
        Line2D([], [], marker="o", ls="none", color=INK, ms=5, alpha=0.75,
               label="$\\leq$10 agents per address"),
        Line2D([], [], marker="o", ls="none", color=CORAL, ms=5, alpha=0.75,
               label="$>$10 agents per address"),
    ], loc="lower right", frameon=True, framealpha=0.95, borderpad=0.4)
    fig.tight_layout(pad=0.35)
    save(fig, "erc8004_chains.pdf")
    for r in sorted(rows, key=lambda r: -r["registrations"] / r["registrants"]):
        print(f"  {r['chain']:12s} {r['registrations']/r['registrants']:7.1f} "
              f"per address")


def fig_trend():
    r"""The master figure: how many tokens are live, and what they are worth.

    Counts are a per-month total, so bars; capitalization is a level tracked
    over time, so a line. Two constraints shape the figure. The demo API key
    caps price history at 365 days, so the window starts in September 2025. And
    historical category membership is not retrievable, so the tracked set is
    fixed at the coins in the current listing: the rising count is tokens that
    came on stream inside the window, not the whole population.
    """
    series = json.loads((ROOT / "data/raw/cg_series.json").read_text())
    ids = {r["id"] for r in stats.cls()}
    tracked = {c: v for c, v in series.items() if c in ids}
    cutoff = stats.pop()["date"][:7]

    # The series was pulled after the T2 cutoff (the free window is 365 days
    # back from the pull date), so it is truncated to the cutoff: no figure in
    # the paper may show data the stated snapshot does not cover.
    months = [m for m in sorted({m for v in tracked.values() for m in v})
              if m <= cutoff]
    counts = [sum(1 for v in tracked.values() if (v.get(m) or 0) > 0)
              for m in months]
    eco = [sum(v.get(m) or 0 for v in tracked.values()) for m in months]

    def smooth(y):
        """Centred three-month mean; the endpoints keep their own value."""
        return [y[0]] + [sum(y[i - 1:i + 2]) / 3 for i in
                         range(1, len(y) - 1)] + [y[-1]]

    fig, ax1 = plt.subplots(figsize=(COL, 2.85))
    x = np.arange(len(months))
    ax1.bar(x, counts, 0.62, color=MIST, edgecolor="white", linewidth=0.7,
            zorder=2)
    ax1.set_ylabel(f"Tokens listed (of {len(tracked)})")
    ax1.set_ylim(0, max(counts) * 1.75)
    ax1.set_xticks(x)
    ax1.set_xticklabels([m if m.endswith("-01") or i == 0 else m[5:]
                         for i, m in enumerate(months)],
                        rotation=45, ha="right")

    ax2 = ax1.twinx()
    ax2.plot(x, np.asarray(eco) / 1e9, color=INK, lw=0.7, alpha=0.3, zorder=3)
    ax2.plot(x, np.asarray(smooth(eco)) / 1e9, color=INK, lw=1.8, zorder=4)
    # Anchored to the right-hand tail, where the curve has fallen and the bars
    # have not yet risen: the only part of the panel both series leave empty.
    ax2.annotate("aggregate market cap", (len(months) - 1, eco[-1] / 1e9),
                 xytext=(-2, 22), textcoords="offset points", ha="right",
                 fontsize=6.5, color=INK, path_effects=HALO)
    ax2.set_ylabel("Market capitalization (USD)")
    ax2.set_ylim(0, max(eco) / 1e9 * 1.22)
    ax2.yaxis.set_major_formatter(FuncFormatter(lambda v, p: f"${v:.0f}B"))

    fig.tight_layout(pad=0.35)
    save(fig, "mcap_trend.pdf")
    print(f"  n={len(tracked)}  {months[0]}->{months[-1]}: {counts[0]}->{counts[-1]} listed, "
          f"${eco[0]/1e9:.2f}B->${eco[-1]/1e9:.2f}B")


if __name__ == "__main__":
    figs = [fig_marketcap, fig_networks, fig_lorenz,
            fig_panel_retention, fig_x402, fig_erc8004]
    if (ROOT / "data/raw/cg_series.json").exists():
        figs.insert(0, fig_trend)
    for f in figs:
        print(f.__name__)
        f()
