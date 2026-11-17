"""
viz_config.py
--------------
Centralised project configuration: paths, business constants
and, above all, the visual style module reused across ALL project
phases to guarantee graphical consistency in the report.


Usage:
    from viz_config import apply_style, PALETTE, get_categorical_palette
    apply_style()
"""

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns

# ---------------------------------------------------------------------------
# PROJECT PATHS
# ---------------------------------------------------------------------------
DATA_DIR = "data"
OUTPUT_DIR = "output"
FIGURES_DIR = f"{OUTPUT_DIR}/figures"

# ---------------------------------------------------------------------------
# PROJECT COLOUR PALETTE
# ---------------------------------------------------------------------------
# Concept: navy blue / teal as main colours (associated with location,
# trust, accessibility -- consistent with a geomarketing project).
# Red/orange is reserved EXCLUSIVELY as a real alert colour (critical
# nulls, high cannibalization) so it keeps its warning meaning and does
# not compete visually with the rest.
PALETTE = {
    "primary":       "#1B4B6B",  # navy blue -- high-standing score / main focus
    "primary_light": "#4C7A9E",
    "secondary":     "#3E8E7E",  # teal -- price
    "accent":        "#2E7D5B",  # green -- accessibility / competition
    "accent_light":  "#7FB69A",
    "neutral_dark":  "#2B2B2B",  # text / axes
    "neutral_mid":   "#8C8C8C",  # gridlines, secondary elements
    "neutral_light": "#F2F5F4",  # background
    "alert":         "#C1440ED2",  # warnings, high cannibalization (exclusive use)
    "noise":         "#C9C6C0",  # clustering noise points (DBSCAN label = -1)
}

# Qualitative palette for clusters (up to 9 distinguishable clusters + noise separately)
CLUSTER_QUALITATIVE = [
    "#1B4B6B", "#3E8E7E", "#5B8C5A", "#2E5C8A", "#6BA292",
    "#3E6B8A", "#4F7942", "#1F6E8C", "#7FA8A0",
]

# Sequential colormap for continuous variables (price, density, score)
SEQUENTIAL_CMAP = "crest"       # seaborn: light blue -> navy blue, good perceptual ordering
DIVERGING_CMAP = "BrBG"         # for opportunity (low/high); avoids red, preserves semantics


def get_categorical_palette(n: int):
    """Return n distinguishable colours for categorical variables (e.g. clusters)."""
    if n <= len(CLUSTER_QUALITATIVE):
        return CLUSTER_QUALITATIVE[:n]
    return sns.color_palette("husl", n).as_hex()


def apply_style():
    """
    Apply the project's visual style to matplotlib/seaborn.
    Call once at the start of each script/notebook, before plotting.
    """
    sns.set_theme(style="whitegrid", palette=CLUSTER_QUALITATIVE)

    plt.rcParams.update({
        # Typography
        "font.family": "sans-serif",
        "font.size": 11,
        "axes.titlesize": 14,
        "axes.titleweight": "bold",
        "axes.labelsize": 11.5,
        "axes.labelweight": "medium",
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
        "legend.fontsize": 10,
        "legend.title_fontsize": 10.5,
        "figure.titlesize": 15,
        "figure.titleweight": "bold",

        # Base colours
        "axes.edgecolor": PALETTE["neutral_mid"],
        "axes.labelcolor": PALETTE["neutral_dark"],
        "text.color": PALETTE["neutral_dark"],
        "xtick.color": PALETTE["neutral_dark"],
        "ytick.color": PALETTE["neutral_dark"],

        # Clean grid: horizontal only, subtle, behind the data
        "axes.grid": True,
        "axes.grid.axis": "y",
        "grid.color": "#E3E0DA",
        "grid.linewidth": 0.8,
        "axes.axisbelow": True,

        # Remove superfluous spines (less visual "noise")
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.spines.left": False,

        # Figure
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "figure.dpi": 110,
        "savefig.dpi": 160,
        "savefig.bbox": "tight",
    })


def style_axis(ax, title=None, xlabel=None, ylabel=None,
                thousands_x=False, thousands_y=False, legend_title=None):
    """
    Apply consistent formatting to an axis: title, well-structured labels,
    thousands separator where applicable, and legend cleanup.
    Avoids repeating this boilerplate in every chart.
    """
    if title:
        ax.set_title(title, pad=14, loc="left")
    if xlabel:
        ax.set_xlabel(xlabel, labelpad=8)
    if ylabel:
        ax.set_ylabel(ylabel, labelpad=8)
    if thousands_x:
        ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))
    if thousands_y:
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))
    if legend_title is not None and ax.get_legend() is not None:
        ax.legend(title=legend_title, frameon=False, loc="best")
    return ax
