"""
apresentacao.py – Fundamentação científica e storytelling de dados do Capiba Calcula.

Gera um painel PNG multi-página com 7 gráficos organizados em narrativa científica:
  1. Ranking de emissão CO₂ direto (g/km) por combustível — contexto base PBE/INMETRO
  2. Emissão direta vs. desperdício oculto (stacked) — impacto da fila e arrancada
  3. Consumo em marcha lenta (l/h) por tipo — base CETESB
  4. Fator de emissão do combustível (kg CO₂e/l) — base GHG Protocol Brasil
  5. Pegada total sem tag: breakdown por origem (idle + accel + paper + driving)
  6. Ciclo de vida: emissão por fase (ANFAVEA / BCG)
  7. Projeção de CO₂ evitado acumulado (km vs. emissão) — ICCT / MOVER

Uso em Gradio:
    from apresentacao import get_references, build_charts
"""

import io
import textwrap
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.patheffects as pe
from matplotlib.gridspec import GridSpec
import numpy as np
import pandas as pd

matplotlib.use("Agg")   # backend sem display (servidores / Gradio)

# ──────────────────────────────────────────────────────────────────────────────
# PALETA CAPIBA  (verde escuro primário + destaques âmbar / coral)
# ──────────────────────────────────────────────────────────────────────────────
C = {
    "bg":       "#0F1F14",   # fundo escuro
    "panel":    "#162417",   # card / axes
    "border":   "#2A3D2E",   # linhas leves
    "text":     "#E8F5E9",   # texto principal
    "muted":    "#7DAF85",   # texto secundário
    "green0":   "#4CAF50",   # destaque principal
    "green1":   "#2E7D32",   # verde médio
    "green2":   "#1B5E20",   # verde fundo
    "amber":    "#FFB300",   # acento âmbar
    "coral":    "#EF5350",   # acento alerta
    "ice":      "#80DEEA",   # BEV / elétrico
    "gray":     "#455A64",   # neutro
}

# Combustíveis → cor canônica
FUEL_COLORS = {
    "gasolina": "#EF5350",
    "flex":     "#FF8A65",
    "etanol":   "#A5D6A7",
    "gnv":      "#80DEEA",
    "diesel":   "#B0BEC5",
    "hev":      "#66BB6A",
    "mhev":     "#26A69A",
    "phev":     "#42A5F5",
    "bev":      "#00E5FF",
}

FUEL_LABELS = {
    "gasolina": "Gasolina",
    "flex":     "Flex",
    "etanol":   "Etanol",
    "gnv":      "GNV",
    "diesel":   "Diesel",
    "hev":      "HEV",
    "mhev":     "MHEV",
    "phev":     "PHEV",
    "bev":      "BEV",
}

# Fatores GHG Protocol Brasil (kg CO₂e / l)
GHG_FACTORS = {
    "diesel":   2.603,
    "gasolina": 2.212,
    "flex":     2.212,
    "hev":      2.212,
    "mhev":     2.212,
    "phev":     0.945,
    "gnv":      1.457,
    "etanol":   1.457,
    "bev":      0.125,
}

# Ciclo de vida ANFAVEA/BCG (kg CO₂e / 100 km, médias ilustrativas)
LCA_PHASES = {
    "Fabricação": {"gasolina": 12.0, "flex": 11.8, "bev": 18.5, "phev": 16.0},
    "Combustível (poço-roda)": {"gasolina": 18.5, "flex": 8.2, "bev": 3.1, "phev": 7.4},
    "Operação": {"gasolina": 14.0, "flex": 11.0, "bev": 1.1, "phev": 4.2},
    "Fim de vida": {"gasolina": 1.5, "flex": 1.5, "bev": 2.8, "phev": 2.1},
}

LCA_ORDER = ["Fabricação", "Combustível (poço-roda)", "Operação", "Fim de vida"]


# ──────────────────────────────────────────────────────────────────────────────
# UTILIDADES
# ──────────────────────────────────────────────────────────────────────────────

def _style_ax(ax, title: str, xlabel: str = "", ylabel: str = "",
              source: str = "") -> None:
    """Aplica estilo Capiba em um eixo."""
    ax.set_facecolor(C["panel"])
    ax.tick_params(colors=C["muted"], labelsize=8)
    for spine in ax.spines.values():
        spine.set_edgecolor(C["border"])
    ax.set_title(title, color=C["text"], fontsize=10, fontweight="bold",
                 pad=8, loc="left")
    if xlabel:
        ax.set_xlabel(xlabel, color=C["muted"], fontsize=8)
    if ylabel:
        ax.set_ylabel(ylabel, color=C["muted"], fontsize=8)
    ax.xaxis.label.set_color(C["muted"])
    ax.yaxis.label.set_color(C["muted"])
    ax.grid(axis="y", color=C["border"], linewidth=0.5, linestyle="--", alpha=0.7)
    ax.grid(axis="x", visible=False)
    if source:
        ax.annotate(f"Fonte: {source}", xy=(1, -0.16), xycoords="axes fraction",
                    ha="right", fontsize=6.5, color=C["muted"], style="italic")


def _bar_value_labels(ax, bars, fmt="{:.0f}", color=None, yoffset=2):
    for bar in bars:
        h = bar.get_height()
        if h > 0:
            ax.text(bar.get_x() + bar.get_width() / 2, h + yoffset,
                    fmt.format(h), ha="center", va="bottom",
                    fontsize=7.5, color=color or C["text"], fontweight="bold")


def _section_title(fig, y: float, number: str, title: str, subtitle: str = ""):
    fig.text(0.015, y, number, fontsize=28, color=C["green0"],
             fontweight="bold", alpha=0.3, va="top")
    fig.text(0.055, y, title, fontsize=12, color=C["text"],
             fontweight="bold", va="top")
    if subtitle:
        fig.text(0.055, y - 0.025, subtitle, fontsize=8.5,
                 color=C["muted"], va="top", style="italic")


# ──────────────────────────────────────────────────────────────────────────────
# DADOS EXTRAÍDOS PELO ETL (importados ou recriados para isolamento de plots)
# ──────────────────────────────────────────────────────────────────────────────

def _load_etl_data() -> pd.DataFrame:
    """Tenta importar do pipeline; se falhar usa cópia local (para preview standalone)."""
    try:
        from pipeline.extract import extract_vehicle_emission_factors
        return extract_vehicle_emission_factors()
    except ImportError:
        csv = """categoria,combustivel,co2_g_km,consumo_marcha_lenta_l_h,adicional_aceleracao_ml
passeio,gasolina,140.0,0.8,40.0
passeio,etanol,0.0,1.1,55.0
passeio,flex,110.0,0.95,45.0
passeio,gnv,95.0,0.7,35.0
passeio,phev,42.0,0.2,10.0
passeio,hev,78.0,0.45,22.0
passeio,mhev,93.0,0.7,32.0
suv,gasolina,185.0,1.2,60.0
suv,flex,145.0,1.35,65.0
suv,diesel,160.0,1.1,50.0
suv,phev,58.0,0.3,15.0
suv,hev,108.0,0.6,28.0
suv,mhev,124.0,0.9,48.0
pesado,diesel,770.0,2.5,180.0
pesado,gnv,550.0,1.8,130.0
passeio,bev,11.2,0.05,5.0
suv,bev,15.1,0.08,8.0"""
        return pd.read_csv(io.StringIO(csv))


# ──────────────────────────────────────────────────────────────────────────────
# GRÁFICOS INDIVIDUAIS
# ──────────────────────────────────────────────────────────────────────────────

def _plot_co2_ranking(ax, df: pd.DataFrame):
    """Gráfico 1 — Ranking emissão direta g/km, ordenado, por categoria × combustível."""
    df_pass = df[df["categoria"] == "passeio"].copy().sort_values("co2_g_km", ascending=True)
    fuels   = df_pass["combustivel"].tolist()
    values  = df_pass["co2_g_km"].tolist()
    colors  = [FUEL_COLORS.get(f, C["gray"]) for f in fuels]
    labels  = [FUEL_LABELS.get(f, f.upper()) for f in fuels]

    bars = ax.barh(labels, values, color=colors, height=0.65,
                   edgecolor=C["bg"], linewidth=0.5)

    # Linha de referência MOVER 2025: meta 117 g/km
    ax.axvline(117, color=C["amber"], linewidth=1.2, linestyle="--", alpha=0.9)
    ax.text(118, len(labels) - 0.4, "Meta MOVER\n117 g/km", color=C["amber"],
            fontsize=7, va="top")

    for bar, val in zip(bars, values):
        label = f"{val:.0f}" if val > 0 else "0 (elétrico)"
        ax.text(val + 3, bar.get_y() + bar.get_height() / 2, label,
                va="center", fontsize=7.5, color=C["text"], fontweight="bold")

    ax.set_xlim(0, 220)
    _style_ax(ax,
              "Emissão direta de CO₂ — Veículos de Passeio",
              "g CO₂ / km",
              source="INMETRO/PBE Veicular + ICCT/MOVER 2024-2025")


def _plot_hidden_footprint(ax, df: pd.DataFrame):
    """Gráfico 2 — Emissão direta vs. desperdício oculto sem tag (stacked bar)."""
    cats = ["Passeio\nFlex", "SUV\nFlex", "SUV\nDiesel", "Pesado\nDiesel"]
    rows = [
        df[(df.categoria == "passeio") & (df.combustivel == "flex")].iloc[0],
        df[(df.categoria == "suv")    & (df.combustivel == "flex")].iloc[0],
        df[(df.categoria == "suv")    & (df.combustivel == "diesel")].iloc[0],
        df[(df.categoria == "pesado") & (df.combustivel == "diesel")].iloc[0],
    ]

    km, tolls, parkings = 100, 3, 2
    direct, idle, accel, paper = [], [], [], []

    for r in rows:
        ef = GHG_FACTORS.get(r["combustivel"], 1.5)
        d  = (km * r["co2_g_km"]) / 1000
        ih = ((tolls * 3 + parkings * 2) / 60) * r["consumo_marcha_lenta_l_h"] * ef
        ac = ((tolls + parkings) * r["adicional_aceleracao_ml"] / 1000) * ef
        pp = parkings * 0.015
        direct.append(d);  idle.append(ih);  accel.append(ac);  paper.append(pp)

    x    = np.arange(len(cats))
    w    = 0.55
    b1   = ax.bar(x, direct, w, label="Rodagem direta",   color=C["green1"],  edgecolor=C["bg"])
    b2   = ax.bar(x, idle,   w, label="Marcha lenta",     color=C["amber"],   bottom=direct, edgecolor=C["bg"])
    b3   = ax.bar(x, accel,  w, label="Arrancadas",       color=C["coral"],
                  bottom=[d + i for d, i in zip(direct, idle)], edgecolor=C["bg"])
    b4   = ax.bar(x, paper,  w, label="Ticket papel",     color=C["gray"],
                  bottom=[d + i + a for d, i, a in zip(direct, idle, accel)], edgecolor=C["bg"])

    ax.set_xticks(x); ax.set_xticklabels(cats, fontsize=8, color=C["text"])
    ax.legend(fontsize=7, framealpha=0, labelcolor=C["muted"],
              loc="upper left", ncol=2)
    _style_ax(ax,
              "Pegada oculta: CO₂ com tag vs. sem tag (100 km)",
              "kg CO₂e",
              source="CETESB + GHG Protocol Brasil")


def _plot_idle_consumption(ax, df: pd.DataFrame):
    """Gráfico 3 — Consumo em marcha lenta por combustível (passeio)."""
    df_p = df[df["categoria"] == "passeio"].sort_values("consumo_marcha_lenta_l_h")
    fuels  = df_p["combustivel"].tolist()
    vals   = df_p["consumo_marcha_lenta_l_h"].tolist()
    colors = [FUEL_COLORS.get(f, C["gray"]) for f in fuels]
    labels = [FUEL_LABELS.get(f, f.upper()) for f in fuels]

    bars = ax.bar(labels, vals, color=colors, width=0.6, edgecolor=C["bg"])
    _bar_value_labels(ax, bars, fmt="{:.2f}", yoffset=0.002)
    ax.set_ylim(0, max(vals) * 1.35)
    _style_ax(ax,
              "Consumo em marcha lenta por motorização",
              "", "Litros / hora",
              source="CETESB – Emissão Veicular")


def _plot_ghg_factors(ax):
    """Gráfico 4 — Fator de emissão do combustível (kg CO₂e/l) — GHG Protocol."""
    fuels  = list(GHG_FACTORS.keys())
    vals   = list(GHG_FACTORS.values())
    colors = [FUEL_COLORS.get(f, C["gray"]) for f in fuels]
    labels = [FUEL_LABELS.get(f, f.upper()) for f in fuels]
    sorted_pairs = sorted(zip(vals, labels, colors), reverse=True)
    vals, labels, colors = zip(*sorted_pairs)

    bars = ax.barh(labels, vals, color=colors, height=0.6, edgecolor=C["bg"])
    for bar, val in zip(bars, vals):
        ax.text(val + 0.03, bar.get_y() + bar.get_height() / 2,
                f"{val:.3f}", va="center", fontsize=7.5,
                color=C["text"], fontweight="bold")

    ax.set_xlim(0, 3.1)
    _style_ax(ax,
              "Fator de emissão do combustível",
              "kg CO₂e / litro",
              source="Programa Brasileiro GHG Protocol – FGV EAESP")


def _plot_lca(ax):
    """Gráfico 5 — Ciclo de vida: emissão por fase (ANFAVEA/BCG)."""
    vehicles   = ["Gasolina", "Flex", "BEV", "PHEV"]
    v_keys     = ["gasolina", "flex", "bev", "phev"]
    v_colors   = [FUEL_COLORS[k] for k in v_keys]
    x          = np.arange(len(LCA_ORDER))
    n          = len(vehicles)
    w          = 0.18
    offsets    = np.linspace(-(n - 1) / 2, (n - 1) / 2, n) * w

    for i, (veh, key, col) in enumerate(zip(vehicles, v_keys, v_colors)):
        vals = [LCA_PHASES[phase][key] for phase in LCA_ORDER]
        bars = ax.bar(x + offsets[i], vals, w, label=veh, color=col,
                      edgecolor=C["bg"], linewidth=0.4, alpha=0.92)

    short_phases = ["Fabricação", "Poço → Roda", "Operação", "Fim de vida"]
    ax.set_xticks(x)
    ax.set_xticklabels(short_phases, fontsize=8, color=C["text"])
    ax.legend(fontsize=7.5, framealpha=0, labelcolor=C["muted"], ncol=2)
    _style_ax(ax,
              "Ciclo de vida completo (LCA) por fase",
              "", "kg CO₂e / 100 km",
              source="ANFAVEA & BCG – Caminhos da Descarbonização")


def _plot_avoided_projection(ax):
    """Gráfico 6 — Projeção de CO₂ evitado acumulado ao longo da quilometragem."""
    kms = np.linspace(0, 50_000, 500)

    scenarios = [
        ("Passeio Gasolina", 140.0, 0.8, 40.0, "gasolina", C["coral"]),
        ("SUV Flex",         145.0, 1.35, 65.0, "flex",    C["amber"]),
        ("Passeio HEV",       78.0, 0.45, 22.0, "hev",     C["green0"]),
        ("Passeio BEV",       11.2, 0.05,  5.0, "bev",     C["ice"]),
    ]
    tolls, parkings = 2, 1   # por 100 km
    km_per_event = 100

    for label, co2, idle, accel_ml, fuel, color in scenarios:
        ef = GHG_FACTORS[fuel]
        # por km: direto + marcha lenta + arrancada + papel
        avoided_per_km = (
            (co2 / 1000) +                              # emissão direta que seria gerada
            ((tolls * 3 + parkings * 2) / 60) * idle * ef / km_per_event +
            ((tolls + parkings) * accel_ml / 1000) * ef / km_per_event +
            parkings * 0.015 / km_per_event
        ) - (co2 / 1000)                                # subtrai o que ocorre COM tag

        # Pegada oculta acumulada (o que a tag poupa)
        hidden_per_km = (
            ((tolls * 3 + parkings * 2) / 60) * idle * ef / km_per_event +
            ((tolls + parkings) * accel_ml / 1000) * ef / km_per_event +
            parkings * 0.015 / km_per_event
        )
        accumulated = kms * hidden_per_km
        ax.plot(kms / 1000, accumulated, color=color, linewidth=1.8,
                label=label, alpha=0.9)

    ax.axhline(50, color=C["amber"], linewidth=0.8, linestyle=":",  alpha=0.7)
    ax.text(0.5, 51, "Limiar Ouro: 50 kg", color=C["amber"], fontsize=7)
    ax.axhline(15, color=C["gray"],  linewidth=0.8, linestyle=":",  alpha=0.7)
    ax.text(0.5, 16, "Limiar Prata: 15 kg", color=C["gray"], fontsize=7)

    ax.legend(fontsize=7.5, framealpha=0, labelcolor=C["muted"])
    ax.set_xlim(0, 50)
    _style_ax(ax,
              "Projeção de CO₂ evitado acumulado pela tag",
              "km percorridos (× 1.000)", "kg CO₂e evitado",
              source="ICCT – Programa MOVER: Maio 2024 – Junho 2025")


def _plot_accel_scatter(ax, df: pd.DataFrame):
    """Gráfico 7 — Scatter: consumo marcha lenta × arrancada, por categoria."""
    cat_markers = {"passeio": "o", "suv": "s", "pesado": "^"}
    for _, row in df.iterrows():
        c   = FUEL_COLORS.get(row["combustivel"], C["gray"])
        m   = cat_markers.get(row["categoria"], "D")
        lbl = FUEL_LABELS.get(row["combustivel"], row["combustivel"].upper())
        ax.scatter(row["consumo_marcha_lenta_l_h"], row["adicional_aceleracao_ml"],
                   color=c, marker=m, s=70, alpha=0.85, edgecolors=C["bg"], linewidths=0.5)
        ax.annotate(lbl,
                    (row["consumo_marcha_lenta_l_h"], row["adicional_aceleracao_ml"]),
                    textcoords="offset points", xytext=(5, 3),
                    fontsize=6.5, color=C["muted"])

    # Legenda manual de forma
    handles = [
        mpatches.Patch(color="none"),
        plt.Line2D([0], [0], marker="o", color="w", markerfacecolor=C["muted"],
                   markersize=7, label="Passeio"),
        plt.Line2D([0], [0], marker="s", color="w", markerfacecolor=C["muted"],
                   markersize=7, label="SUV"),
        plt.Line2D([0], [0], marker="^", color="w", markerfacecolor=C["muted"],
                   markersize=7, label="Pesado"),
    ]
    ax.legend(handles=handles[1:], fontsize=7, framealpha=0,
              labelcolor=C["muted"], title="Categoria", title_fontsize=7)
    _style_ax(ax,
              "Pegada oculta: marcha lenta × arrancada",
              "Consumo em marcha lenta (l/h)",
              "Consumo extra na arrancada (ml)",
              source="CETESB – Emissão Veicular")


# ──────────────────────────────────────────────────────────────────────────────
# FIGURA PRINCIPAL
# ──────────────────────────────────────────────────────────────────────────────

def build_charts() -> str:
    """
    Monta o painel completo de storytelling científico.
    Retorna o caminho do PNG gerado.
    """
    df = _load_etl_data()

    # ── Layout: 4 linhas × 2 colunas (7 plots + 1 caixa de legenda)
    fig = plt.figure(figsize=(18, 26), facecolor=C["bg"])
    fig.subplots_adjust(left=0.06, right=0.97, top=0.955, bottom=0.03,
                        hspace=0.58, wspace=0.32)

    gs = GridSpec(4, 2, figure=fig)
    axes = [
        fig.add_subplot(gs[0, 0]),   # 1 – ranking CO₂
        fig.add_subplot(gs[0, 1]),   # 2 – stacked hidden footprint
        fig.add_subplot(gs[1, 0]),   # 3 – marcha lenta
        fig.add_subplot(gs[1, 1]),   # 4 – GHG factors
        fig.add_subplot(gs[2, 0]),   # 5 – LCA
        fig.add_subplot(gs[2, 1]),   # 6 – avoided projection
        fig.add_subplot(gs[3, :]),   # 7 – scatter (full width)
    ]

    # ── Cabeçalho do painel ───────────────────────────────────────────────────
    fig.text(0.5, 0.975, "Capiba Calcula — Painel Científico de Emissões Veiculares",
             ha="center", fontsize=16, fontweight="bold", color=C["text"])
    fig.text(0.5, 0.963,
             "Dados extraídos via ETL do PBE Veicular (INMETRO), CETESB, GHG Protocol Brasil, ANFAVEA/BCG e ICCT/MOVER",
             ha="center", fontsize=8.5, color=C["muted"], style="italic")

    # Linha divisória decorativa
    fig.add_artist(plt.Line2D([0.05, 0.95], [0.958, 0.958],
                              transform=fig.transFigure,
                              color=C["green1"], linewidth=0.8))

    # ── Renderiza cada gráfico ─────────────────────────────────────────────────
    _plot_co2_ranking(axes[0], df)
    _plot_hidden_footprint(axes[1], df)
    _plot_idle_consumption(axes[2], df)
    _plot_ghg_factors(axes[3])
    _plot_lca(axes[4])
    _plot_avoided_projection(axes[5])
    _plot_accel_scatter(axes[6], df)

    # ── Rótulos de seção (números grandes, semitransparentes) ─────────────────
    section_meta = [
        (0.965, "① Emissão direta", "PBE Veicular — base INMETRO + meta MOVER"),
        (0.720, "② Pegada oculta",  "Impacto da fila e das arrancadas — CETESB"),
        (0.490, "③ Ciclo de vida",  "LCA completo e projeção acumulada"),
        (0.245, "④ Correlação",     "Mapa de desperdício por tipo de motor"),
    ]
    for y, title, sub in section_meta:
        fig.text(0.005, y, "│", fontsize=22, color=C["green1"],
                 va="center", fontweight="bold")
        fig.text(0.018, y + 0.007, title, fontsize=10, color=C["text"],
                 fontweight="bold", va="center")
        fig.text(0.018, y - 0.007, sub, fontsize=7.5, color=C["muted"],
                 va="center", style="italic")

    # ── Rodapé com lista de referências ───────────────────────────────────────
    refs_text = (
        "REFERÊNCIAS: INMETRO – PBE Veicular  |  CETESB – Emissão Veicular  |  "
        "GHG Protocol Brasil (FGV EAESP)  |  ANFAVEA & BCG – Caminhos da Descarbonização  |  "
        "ICCT – Emissões CO₂ Programa MOVER (Mai 2024 – Jun 2025)"
    )
    fig.text(0.5, 0.013, refs_text, ha="center", fontsize=7,
             color=C["muted"], style="italic",
             bbox=dict(boxstyle="round,pad=0.3", facecolor=C["panel"],
                       edgecolor=C["border"], linewidth=0.6))

    out_path = "analise_cientifica_emissoes.png"
    fig.savefig(out_path, dpi=140, bbox_inches="tight",
                facecolor=C["bg"], edgecolor="none")
    plt.close(fig)
    return out_path


# ──────────────────────────────────────────────────────────────────────────────
# REFERÊNCIAS (usado pelo gr.HTML no Gradio)
# ──────────────────────────────────────────────────────────────────────────────

def get_references() -> str:
    """Retorna bloco HTML rico com as referências científicas do projeto."""
    return """
<div style="
    background:#162417; border-radius:10px; padding:18px 22px;
    border:1px solid #2A3D2E; font-family:'Segoe UI',sans-serif;">

  <p style="color:#7DAF85; font-size:11px; letter-spacing:.1em;
            text-transform:uppercase; margin:0 0 10px;">
    Base metodológica · 5 fontes oficiais
  </p>

  <div style="display:flex; flex-direction:column; gap:10px;">

    <div style="border-left:3px solid #4CAF50; padding-left:12px;">
      <span style="background:#1B5E20; color:#A5D6A7; font-size:10px;
                   padding:2px 8px; border-radius:20px; font-weight:600;">
        INMETRO · Dados oficiais
      </span>
      <p style="color:#E8F5E9; font-size:13px; font-weight:600; margin:4px 0 2px;">
        Programa Brasileiro de Etiquetagem — PBE Veicular
      </p>
      <p style="color:#7DAF85; font-size:11.5px; margin:0 0 3px;">
        Tabelas de eficiência e emissão dos veículos leves certificados,
        incluindo consumo em marcha lenta e fator CO₂ g/km por modelo.
      </p>
      <a href="https://www.gov.br/inmetro/pt-br/assuntos/regulamentacao/avaliacao-da-conformidade/programa-brasileiro-de-etiquetagem/tabelas-de-eficiencia-energetica/veiculos-automotivos-pbe-veicular"
         style="color:#66BB6A; font-size:11px;" target="_blank">
        ↗ gov.br/inmetro · PBE Veicular
      </a>
    </div>

    <div style="border-left:3px solid #FFB300; padding-left:12px;">
      <span style="background:#3E2723; color:#FFCC80; font-size:10px;
                   padding:2px 8px; border-radius:20px; font-weight:600;">
        CETESB · Relatórios técnicos
      </span>
      <p style="color:#E8F5E9; font-size:13px; font-weight:600; margin:4px 0 2px;">
        Emissão Veicular — Publicações e Relatórios
      </p>
      <p style="color:#7DAF85; font-size:11.5px; margin:0 0 3px;">
        Inventário histórico de emissões em São Paulo: NOₓ, MP, CO e GEE,
        com dados de consumo em marcha lenta e ciclos urbanos reais.
      </p>
      <a href="https://www.cetesb.sp.gov.br/cetesb/qualidade_ambiental/emissao_veicular/publicacoes_e_relatorios"
         style="color:#66BB6A; font-size:11px;" target="_blank">
        ↗ cetesb.sp.gov.br · Emissão Veicular
      </a>
    </div>

    <div style="border-left:3px solid #42A5F5; padding-left:12px;">
      <span style="background:#0D47A1; color:#90CAF9; font-size:10px;
                   padding:2px 8px; border-radius:20px; font-weight:600;">
        FGV · GHG Protocol
      </span>
      <p style="color:#E8F5E9; font-size:13px; font-weight:600; margin:4px 0 2px;">
        Programa Brasileiro GHG Protocol
      </p>
      <p style="color:#7DAF85; font-size:11.5px; margin:0 0 3px;">
        Fatores de emissão por combustível (kg CO₂e/l) e metodologia de escopos
        1, 2 e 3 adotada nos cálculos do simulador.
      </p>
      <a href="https://eaesp.fgv.br/centros/centro-estudos-sustentabilidade/projetos/programa-brasileiro-ghg-protocol"
         style="color:#66BB6A; font-size:11px;" target="_blank">
        ↗ fgv.br · Programa GHG Protocol
      </a>
    </div>

    <div style="border-left:3px solid #EF5350; padding-left:12px;">
      <span style="background:#4E1616; color:#FFCDD2; font-size:10px;
                   padding:2px 8px; border-radius:20px; font-weight:600;">
        ANFAVEA & BCG · Análise setorial
      </span>
      <p style="color:#E8F5E9; font-size:13px; font-weight:600; margin:4px 0 2px;">
        Caminhos da Descarbonização: LCA do veículo brasileiro
      </p>
      <p style="color:#7DAF85; font-size:11.5px; margin:0 0 3px;">
        Estudo de ciclo de vida completo — da mineração ao descarte —
        incluindo fases de fabricação, uso e eletromobilidade no Brasil.
      </p>
      <a href="https://web-assets.bcg.com/30/97/e8e78976425983c13e92de4af084/caminhos-descarbonizacao-setor-automotivo-brasil.pdf"
         style="color:#66BB6A; font-size:11px;" target="_blank">
        ↗ bcg.com · Relatório PDF
      </a>
    </div>

    <div style="border-left:3px solid #80DEEA; padding-left:12px;">
      <span style="background:#004D40; color:#80CBC4; font-size:10px;
                   padding:2px 8px; border-radius:20px; font-weight:600;">
        ICCT · Política pública
      </span>
      <p style="color:#E8F5E9; font-size:13px; font-weight:600; margin:4px 0 2px;">
        Emissões de CO₂ — Programa MOVER (Mai 2024 – Jun 2025)
      </p>
      <p style="color:#7DAF85; font-size:11.5px; margin:0 0 3px;">
        Análise dos parâmetros regulatórios do MOVER com comparativo entre
        metas oficiais e desempenho real da frota nacional de veículos leves.
      </p>
      <a href="https://theicct.org/emissoes-de-co2-dos-carros-de-passeio-segundo-parametros-oficiais-do-programa-mover-maio-2024-junho-2025/"
         style="color:#66BB6A; font-size:11px;" target="_blank">
        ↗ theicct.org · Análise MOVER
      </a>
    </div>

  </div>
</div>
""".strip()
