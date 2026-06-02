import io
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image, HRFlowable, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_CENTER, TA_LEFT

# ── Paleta verde Capiba Calcula ──────────────────────────────────────
GREEN_DARK  = "#1B5E20"
GREEN_MED   = "#2E7D32"
GREEN_LIGHT = "#66BB6A"
GREEN_PALE  = "#E8F5E9"
GREY_TEXT   = "#424242"
ACCENT_BLUE = "#0288D1"


# ════════════════════════════════════════════════════════════════════
#  GRÁFICOS
# ════════════════════════════════════════════════════════════════════

def _make_bar_chart(summary_data: dict) -> io.BytesIO:
    """Barras: emissões sem tag × com tag."""
    fig, ax = plt.subplots(figsize=(6, 3.2))
    fig.patch.set_facecolor("white")

    labels  = ["Sem uso de Tag", "Com uso de Tag"]
    valores = [summary_data["sem_tag_kg"], summary_data["com_tag_kg"]]
    bar_colors = [GREEN_LIGHT, GREEN_DARK]

    bars = ax.bar(labels, valores, color=bar_colors, width=0.45,
                  edgecolor="white", linewidth=0.8)
    for bar, val in zip(bars, valores):
        ax.text(bar.get_x() + bar.get_width() / 2,
                bar.get_height() + max(valores) * 0.02,
                f"{val:,.2f} kg", ha="center", va="bottom",
                fontsize=9, color=GREY_TEXT, fontweight="bold")

    ax.set_ylabel("kg CO2e", fontsize=9, color=GREY_TEXT)
    ax.set_title("Emissoes de CO2e: Comparativo", fontsize=11,
                 color=GREEN_DARK, fontweight="bold", pad=10)
    ax.set_ylim(0, max(valores) * 1.20)
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(colors=GREY_TEXT, labelsize=9)
    ax.yaxis.grid(True, linestyle="--", alpha=0.4)
    ax.set_axisbelow(True)

    buf = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf


def _make_donut_chart(summary_data: dict) -> io.BytesIO:
    """Rosca: composição das emissões evitadas."""
    detalhes = summary_data["detalhes"]
    labels  = ["Marcha lenta\npoupada", "Aceleracao\nevitada", "Tickets de\npapel"]
    valores = [detalhes["marcha_lenta_kg"],
               detalhes["aceleracao_kg"],
               detalhes["ticket_papel_kg"]]
    paleta  = [GREEN_MED, GREEN_LIGHT, ACCENT_BLUE]

    fig, ax = plt.subplots(figsize=(4.5, 3.2))
    fig.patch.set_facecolor("white")

    wedges, _, autotexts = ax.pie(
        valores, labels=None, autopct="%1.1f%%", colors=paleta,
        startangle=90,
        wedgeprops=dict(width=0.55, edgecolor="white", linewidth=1.5),
        pctdistance=0.75,
    )
    for at in autotexts:
        at.set_fontsize(8)
        at.set_color("white")
        at.set_fontweight("bold")

    ax.legend(wedges, labels, loc="lower center",
              bbox_to_anchor=(0.5, -0.18), ncol=3,
              fontsize=7.5, frameon=False)
    ax.set_title("Composicao das Emissoes Evitadas", fontsize=11,
                 color=GREEN_DARK, fontweight="bold", pad=8)

    buf = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf


def _make_km_efficiency_chart(summary_data: dict) -> io.BytesIO:
    """Linha dupla: impacto ambiental × quilometragem percorrida."""
    km_base  = summary_data.get("km_percorridos", 120)
    sem_base = summary_data["sem_tag_kg"]
    com_base = summary_data["com_tag_kg"]

    ratio_sem = sem_base / km_base if km_base else 0
    ratio_com = com_base / km_base if km_base else 0

    km_range = np.linspace(km_base * 0.2, km_base * 2.5, 60)
    ems_sem  = km_range * ratio_sem
    ems_com  = km_range * ratio_com

    fig, ax = plt.subplots(figsize=(9, 3.8))
    fig.patch.set_facecolor("white")

    ax.fill_between(km_range, ems_sem, ems_com,
                    alpha=0.18, color=GREEN_MED, label="_nolegend_")
    ax.plot(km_range, ems_sem, color=GREEN_LIGHT, linewidth=2.2, label="Sem Tag")
    ax.plot(km_range, ems_com, color=GREEN_DARK,  linewidth=2.2, label="Com Tag")

    ax.axvline(km_base, color=ACCENT_BLUE, linestyle="--", linewidth=1.2, alpha=0.7)
    ax.scatter([km_base], [sem_base], color=GREEN_LIGHT, s=60, zorder=5)
    ax.scatter([km_base], [com_base], color=GREEN_DARK,  s=60, zorder=5)
    ax.text(km_base + km_base * 0.03,
            (sem_base + com_base) / 2,
            f"Viagem atual\n{km_base:.0f} km",
            fontsize=8, color=ACCENT_BLUE, va="center")

    mid_km  = km_base * 1.6
    mid_eco = (mid_km * ratio_sem + mid_km * ratio_com) / 2
    economia_pct = ((ratio_sem - ratio_com) / ratio_sem * 100) if ratio_sem else 0
    ax.annotate(f"Economia media\n~{economia_pct:.1f}% de CO2e",
                xy=(mid_km, mid_eco),
                fontsize=8, color=GREEN_MED, ha="center",
                bbox=dict(boxstyle="round,pad=0.3",
                          fc=GREEN_PALE, ec=GREEN_MED, lw=0.8))

    ax.set_xlabel("Quilometros Percorridos (km)", fontsize=9, color=GREY_TEXT)
    ax.set_ylabel("Emissoes (kg CO2e)",            fontsize=9, color=GREY_TEXT)
    ax.set_title("Impacto Ambiental x Quilometragem Percorrida",
                 fontsize=11, color=GREEN_DARK, fontweight="bold", pad=10)
    ax.legend(fontsize=9, frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(colors=GREY_TEXT, labelsize=8)
    ax.yaxis.grid(True, linestyle="--", alpha=0.35)
    ax.set_axisbelow(True)

    buf = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf


def _make_gauge_chart(pct_reducao: float) -> io.BytesIO:
    """Gauge semicircular: % de redução de emissões."""
    fig, ax = plt.subplots(figsize=(4, 2.4),
                           subplot_kw=dict(aspect="equal"))
    fig.patch.set_facecolor("white")
    ax.set_xlim(-1.3, 1.3)
    ax.set_ylim(-0.15, 1.25)
    ax.axis("off")

    theta_bg = np.linspace(np.pi, 0, 200)
    ax.fill_between(np.cos(theta_bg), np.sin(theta_bg),
                    0.6 * np.sin(theta_bg), color="#E0E0E0", zorder=1)

    frac = min(pct_reducao / 100, 1.0)
    theta_fg = np.linspace(np.pi, np.pi * (1 - frac), 200)
    ax.fill_between(np.cos(theta_fg), np.sin(theta_fg),
                    0.6 * np.sin(theta_fg), color=GREEN_MED, zorder=2)

    ax.text(0, 0.28, f"{pct_reducao:.1f}%",
            ha="center", va="center",
            fontsize=20, color=GREEN_DARK, fontweight="bold", zorder=3)
    ax.text(0, 0.08, "reducao de emissoes",
            ha="center", va="center",
            fontsize=8, color=GREY_TEXT, zorder=3)
    ax.set_title("Indice de Eficiencia Verde", fontsize=11,
                 color=GREEN_DARK, fontweight="bold")

    buf = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf


def _make_fleet_bar_chart(vehicles_results: list[dict]) -> io.BytesIO:
    """
    Barras horizontais comparando emissões evitadas por veículo da frota.
    Recebe lista de dicts com chaves 'nome', 'evitado_kg'.
    """
    nomes   = [v["nome"] for v in vehicles_results]
    valores = [v["evitado_kg"] for v in vehicles_results]

    fig, ax = plt.subplots(figsize=(9, max(3, len(nomes) * 0.7 + 1.2)))
    fig.patch.set_facecolor("white")

    y_pos = range(len(nomes))
    bars = ax.barh(list(y_pos), valores, color=GREEN_MED,
                   edgecolor="white", linewidth=0.8, height=0.55)
    for bar, val in zip(bars, valores):
        ax.text(bar.get_width() + max(valores) * 0.01,
                bar.get_y() + bar.get_height() / 2,
                f"{val:,.3f} kg", va="center", fontsize=8.5,
                color=GREY_TEXT, fontweight="bold")

    ax.set_yticks(list(y_pos))
    ax.set_yticklabels(nomes, fontsize=9, color=GREY_TEXT)
    ax.set_xlabel("kg CO2e Evitado", fontsize=9, color=GREY_TEXT)
    ax.set_title("CO2e Evitado por Veículo da Frota", fontsize=11,
                 color=GREEN_DARK, fontweight="bold", pad=10)
    ax.set_xlim(0, max(valores) * 1.20)
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(colors=GREY_TEXT, labelsize=9)
    ax.xaxis.grid(True, linestyle="--", alpha=0.4)
    ax.set_axisbelow(True)

    buf = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf


# ════════════════════════════════════════════════════════════════════
#  HELPERS DE ESTILO
# ════════════════════════════════════════════════════════════════════

def _styles():
    base = getSampleStyleSheet()

    def st(name, **kw):
        return ParagraphStyle(name, parent=base["Normal"], **kw)

    return dict(
        title  = st("Title",  fontSize=20, textColor=colors.HexColor(GREEN_DARK),
                    spaceAfter=10, fontName="Helvetica-Bold", alignment=TA_CENTER),
        sub    = st("Sub",    fontSize=9,  textColor=colors.HexColor(GREY_TEXT),
                    spaceBefore=4, spaceAfter=14, alignment=TA_CENTER),
        h2     = st("H2",     fontSize=13, textColor=colors.HexColor(GREEN_MED),
                    spaceBefore=14, spaceAfter=6, fontName="Helvetica-Bold"),
        body   = st("Body",   fontSize=9,  textColor=colors.HexColor(GREY_TEXT),
                    leading=14, spaceAfter=6),
        badge  = st("Badge",  fontSize=14, textColor=colors.HexColor(GREEN_DARK),
                    alignment=TA_CENTER, fontName="Helvetica-Bold", spaceAfter=4),
        th     = st("TH",     fontSize=9,  textColor=colors.HexColor(GREEN_DARK),
                    fontName="Helvetica-Bold", alignment=TA_CENTER),
        td     = st("TD",     fontSize=9,  textColor=colors.HexColor(GREY_TEXT),
                    alignment=TA_LEFT),
        td_r   = st("TD_R",   fontSize=9,  textColor=colors.HexColor(GREY_TEXT),
                    alignment=TA_CENTER),
        footer = st("Footer", fontSize=7.5,
                    textColor=colors.HexColor("#9E9E9E"), alignment=TA_CENTER),
    )


def _hr(W, thick=0.5, after=8):
    return HRFlowable(width=W, thickness=thick,
                      color=colors.HexColor(GREEN_LIGHT), spaceAfter=after)


def _table_style_detail():
    return TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), colors.HexColor(GREEN_PALE)),
        ("BACKGROUND",    (0, 4), (-1, 4), colors.HexColor("#C8E6C9")),
        ("GRID",          (0, 0), (-1, -1), 0.4, colors.HexColor(GREEN_LIGHT)),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1),
         [colors.white, colors.HexColor("#F9FBF9")]),
        ("TOPPADDING",    (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
    ])


# ════════════════════════════════════════════════════════════════════
#  SEÇÕES REUTILIZÁVEIS
# ════════════════════════════════════════════════════════════════════

def _section_kpis(story, summary_data, W, s):
    evitado = summary_data["evitado_kg"]
    pct     = (evitado / summary_data["sem_tag_kg"] * 100
               if summary_data["sem_tag_kg"] else 0)
    km      = summary_data.get("km_percorridos", 0)

    def _kpi(val_str, label, txt_color):
        return Paragraph(
            f"<b>{val_str}</b><br/><font size='8'>{label}</font>",
            ParagraphStyle("K", parent=s["title"], fontSize=13,
                           alignment=TA_CENTER,
                           textColor=colors.HexColor(txt_color)))

    kpi_data = [[
        _kpi(f"{summary_data['sem_tag_kg']:,.2f} kg", "Emissões sem Tag",    GREEN_DARK),
        _kpi(f"{summary_data['com_tag_kg']:,.2f} kg",  "Emissões com Tag",    ACCENT_BLUE),
        _kpi(f"{evitado:,.2f} kg",                     "CO2e Evitado",        "#FFFFFF"),
        _kpi(f"{km:,.1f} km",                          "Distância Percorrida", GREEN_DARK),
    ]]
    kpi_t = Table(kpi_data, colWidths=[W / 4] * 4)
    kpi_t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (1, 0), colors.HexColor(GREEN_PALE)),
        ("BACKGROUND",    (2, 0), (2, 0), colors.HexColor(GREEN_MED)),
        ("BACKGROUND",    (3, 0), (3, 0), colors.HexColor(GREEN_PALE)),
        ("BOX",           (0, 0), (-1, -1), 0.5, colors.HexColor(GREEN_LIGHT)),
        ("INNERGRID",     (0, 0), (-1, -1), 0.5, colors.HexColor(GREEN_LIGHT)),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
    ]))
    story.append(kpi_t)
    story.append(Spacer(1, 18))
    return pct


def _section_charts(story, summary_data, W, s):
    evitado = summary_data["evitado_kg"]
    pct     = (evitado / summary_data["sem_tag_kg"] * 100
               if summary_data["sem_tag_kg"] else 0)

    # Gráfico de km × emissões
    story.append(Paragraph("Impacto Ambiental × Quilometragem Percorrida", s["h2"]))
    story.append(_hr(W))
    story.append(Paragraph(
        "O gráfico abaixo projeta como as emissões evitadas escalam "
        "proporcionalmente com a distância percorrida. A região sombreada "
        "representa a economia acumulada de CO2e em cada quilômetro adicional.",
        s["body"]))
    buf_km = _make_km_efficiency_chart(summary_data)
    story.append(Image(buf_km, width=W, height=6.5 * cm))
    story.append(Spacer(1, 16))

    # Barras + Rosca lado a lado
    story.append(Paragraph("Análise Visual das Emissões", s["h2"]))
    story.append(_hr(W))

    buf_bar   = _make_bar_chart(summary_data)
    buf_donut = _make_donut_chart(summary_data)
    buf_gauge = _make_gauge_chart(pct)

    chart_row = Table(
        [[Image(buf_bar,   width=10 * cm, height=5.5 * cm),
          Image(buf_donut, width=8 * cm,  height=5.5 * cm)]],
        colWidths=[10.5 * cm, 8.5 * cm])
    chart_row.setStyle(TableStyle([
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
        ("LEFTPADDING",   (0, 0), (-1, -1), 0),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
    ]))
    story.append(chart_row)
    story.append(Spacer(1, 10))

    gauge_row = Table([[Image(buf_gauge, width=7.5 * cm, height=4.8 * cm)]],
                      colWidths=[W])
    gauge_row.setStyle(TableStyle([
        ("ALIGN",  (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(gauge_row)
    story.append(Spacer(1, 18))


def _section_detail_table(story, summary_data, W, s):
    km = summary_data.get("km_percorridos", 0)
    rows = [
        [Paragraph("Métrica Analisada", s["th"]),
         Paragraph("Valor",             s["th"])],
        [Paragraph("Quilômetros percorridos no período",              s["td"]),
         Paragraph(f"{km:,.1f} km",                                   s["td_r"])],
        [Paragraph("Emissões estimadas <b>sem</b> o uso de Tag",      s["td"]),
         Paragraph(f"{summary_data['sem_tag_kg']:,.3f} kg CO2e",      s["td_r"])],
        [Paragraph("Emissões ocorridas <b>com</b> o uso de Tag",      s["td"]),
         Paragraph(f"{summary_data['com_tag_kg']:,.3f} kg CO2e",      s["td_r"])],
        [Paragraph("<b>Total de gases de efeito estufa evitados</b>", s["td"]),
         Paragraph(f"<b>{summary_data['evitado_kg']:,.3f} kg CO2e</b>", s["td_r"])],
        [Paragraph("Microeficiência: marcha lenta poupada",            s["td"]),
         Paragraph(f"{summary_data['detalhes']['marcha_lenta_kg']:,.3f} kg CO2e", s["td_r"])],
        [Paragraph("Microeficiência: picos de aceleração evitados",   s["td"]),
         Paragraph(f"{summary_data['detalhes']['aceleracao_kg']:,.3f} kg CO2e",   s["td_r"])],
        [Paragraph("Resíduos de papel mitigados (tickets)",            s["td"]),
         Paragraph(f"{summary_data['detalhes']['ticket_papel_kg']:,.3f} kg CO2e", s["td_r"])],
    ]
    t = Table(rows, colWidths=[W * 0.68, W * 0.32])
    t.setStyle(_table_style_detail())
    story.append(Paragraph("Detalhamento das Métricas (kg CO2e)", s["h2"]))
    story.append(_hr(W))
    story.append(t)
    story.append(Spacer(1, 20))


def _section_badge(story, badge_text, W, s):
    badge_table = Table(
        [[Paragraph(badge_text, s["badge"])]], colWidths=[W])
    badge_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), colors.HexColor(GREEN_PALE)),
        ("BOX",           (0, 0), (-1, -1), 1.2, colors.HexColor(GREEN_MED)),
        ("TOPPADDING",    (0, 0), (-1, -1), 14),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
    ]))
    story.append(KeepTogether([
        Paragraph("Perfil Ecológico", s["h2"]),
        _hr(W),
        badge_table,
    ]))


def _footer(story, W, s):
    story.append(Spacer(1, 20))
    story.append(HRFlowable(width=W, thickness=0.5,
                             color=colors.HexColor(GREEN_LIGHT), spaceAfter=6))
    story.append(Paragraph(
        "Relatório gerado automaticamente pela plataforma Capiba Calcula · "
        "GHG Protocol Brasil · Desafio Edenred",
        s["footer"]))


# ════════════════════════════════════════════════════════════════════
#  RELATÓRIO DE VEÍCULO INDIVIDUAL
# ════════════════════════════════════════════════════════════════════

def generate_pdf_report(summary_data: dict,
                        filename: str = "Relatorio_Veiculo.pdf") -> str:
    """
    Gera relatório PDF para um único veículo/simulação.
    summary_data deve conter:
        sem_tag_kg, com_tag_kg, evitado_kg, badge,
        km_percorridos (opcional),
        detalhes: { marcha_lenta_kg, aceleracao_kg, ticket_papel_kg }
        vehicle_name (opcional)
    """
    doc = SimpleDocTemplate(
        filename, pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=2 * cm, bottomMargin=2 * cm,
    )
    W = A4[0] - 4 * cm
    story = []
    s = _styles()

    vehicle_name = summary_data.get("vehicle_name", "Veículo")

    # Cabeçalho
    story.append(Paragraph("Capiba Calcula", s["title"]))
    story.append(Paragraph(
        f"Relatório de Sustentabilidade – {vehicle_name}<br/>"
        "<font size='8'>Métricas computadas sob diretrizes do GHG Protocol Brasil "
        "e Desafio Edenred</font>", s["sub"]))
    story.append(_hr(W, thick=2, after=14))

    # KPIs
    _section_kpis(story, summary_data, W, s)

    # Gráficos
    _section_charts(story, summary_data, W, s)

    # Tabela detalhada
    _section_detail_table(story, summary_data, W, s)

    # Badge ecológico
    _section_badge(story, summary_data.get("badge", ""), W, s)

    # Rodapé
    _footer(story, W, s)

    doc.build(story)
    return filename


# ════════════════════════════════════════════════════════════════════
#  RELATÓRIO DE FROTA
# ════════════════════════════════════════════════════════════════════

def generate_fleet_pdf_report(fleet_name: str,
                               vehicles_results: list[dict],
                               filename: str = "Relatorio_Frota.pdf") -> str:
    """
    Gera relatório PDF consolidado para uma frota.
    vehicles_results: lista de dicts com chaves iguais às de summary_data
                      mais 'nome' (nome do veículo).
    """
    if not vehicles_results:
        return None

    # Consolida os dados da frota
    total_sem   = sum(v["sem_tag_kg"]  for v in vehicles_results)
    total_com   = sum(v["com_tag_kg"]  for v in vehicles_results)
    total_evit  = sum(v["evitado_kg"]  for v in vehicles_results)
    total_km    = sum(v.get("km_percorridos", 0) for v in vehicles_results)

    total_idle    = sum(v["detalhes"]["marcha_lenta_kg"]  for v in vehicles_results)
    total_accel   = sum(v["detalhes"]["aceleracao_kg"]    for v in vehicles_results)
    total_tickets = sum(v["detalhes"]["ticket_papel_kg"]  for v in vehicles_results)

    # Badge da frota com base no total evitado
    if total_evit < 15.0 * len(vehicles_results):
        badge_frota = "Bronze 🥉 (Frota Iniciante na Mobilidade Verde)"
    elif total_evit < 50.0 * len(vehicles_results):
        badge_frota = "Prata 🥈 (Frota Defensora da Sustentabilidade Urbana)"
    else:
        badge_frota = "Ouro 🥇 (Frota Herói de Baixo Carbono – Elegível para Isenções)"

    fleet_summary = {
        "sem_tag_kg":    round(total_sem,  3),
        "com_tag_kg":    round(total_com,  3),
        "evitado_kg":    round(total_evit, 3),
        "km_percorridos": total_km,
        "badge":         badge_frota,
        "detalhes": {
            "marcha_lenta_kg":  round(total_idle,    3),
            "aceleracao_kg":    round(total_accel,   3),
            "ticket_papel_kg":  round(total_tickets, 3),
        },
    }

    doc = SimpleDocTemplate(
        filename, pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=2 * cm, bottomMargin=2 * cm,
    )
    W = A4[0] - 4 * cm
    story = []
    s = _styles()

    # ── Cabeçalho ──────────────────────────────────────────────────
    story.append(Paragraph("Capiba Calcula", s["title"]))
    story.append(Paragraph(
        f"Relatório de Frota – {fleet_name}<br/>"
        f"<font size='8'>{len(vehicles_results)} veículo(s) · "
        "GHG Protocol Brasil · Desafio Edenred</font>", s["sub"]))
    story.append(_hr(W, thick=2, after=14))

    # ── KPIs consolidados ──────────────────────────────────────────
    _section_kpis(story, fleet_summary, W, s)

    # ── Gráfico por veículo ────────────────────────────────────────
    story.append(Paragraph("CO2e Evitado por Veículo", s["h2"]))
    story.append(_hr(W))
    story.append(Paragraph(
        "O gráfico abaixo detalha a contribuição individual de cada "
        "veículo da frota para a redução total de emissões.", s["body"]))

    buf_fleet = _make_fleet_bar_chart(
        [{"nome": v.get("vehicle_name", f"V{i+1}"),
          "evitado_kg": v["evitado_kg"]}
         for i, v in enumerate(vehicles_results)])

    h_fleet = max(4 * cm, len(vehicles_results) * 1.1 * cm + 2 * cm)
    story.append(Image(buf_fleet, width=W, height=h_fleet))
    story.append(Spacer(1, 16))

    # ── Gráficos consolidados ──────────────────────────────────────
    _section_charts(story, fleet_summary, W, s)

    # ── Tabela consolidada ─────────────────────────────────────────
    _section_detail_table(story, fleet_summary, W, s)

    # ── Tabela por veículo ─────────────────────────────────────────
    story.append(Paragraph("Detalhamento por Veículo", s["h2"]))
    story.append(_hr(W))

    header = [
        Paragraph("Veículo",         s["th"]),
        Paragraph("Sem Tag (kg)",    s["th"]),
        Paragraph("Com Tag (kg)",    s["th"]),
        Paragraph("Evitado (kg)",    s["th"]),
        Paragraph("Quilômetros",     s["th"]),
    ]
    rows = [header]
    for i, v in enumerate(vehicles_results):
        bg_color = colors.white if i % 2 == 0 else colors.HexColor("#F9FBF9")
        rows.append([
            Paragraph(v.get("vehicle_name", f"V{i+1}"), s["td"]),
            Paragraph(f"{v['sem_tag_kg']:,.3f}",  s["td_r"]),
            Paragraph(f"{v['com_tag_kg']:,.3f}",  s["td_r"]),
            Paragraph(f"{v['evitado_kg']:,.3f}",  s["td_r"]),
            Paragraph(f"{v.get('km_percorridos', 0):,.1f}", s["td_r"]),
        ])

    # Linha de totais
    rows.append([
        Paragraph("<b>TOTAL DA FROTA</b>", s["th"]),
        Paragraph(f"<b>{total_sem:,.3f}</b>",  s["th"]),
        Paragraph(f"<b>{total_com:,.3f}</b>",  s["th"]),
        Paragraph(f"<b>{total_evit:,.3f}</b>", s["th"]),
        Paragraph(f"<b>{total_km:,.1f}</b>",   s["th"]),
    ])

    col_w = [W * 0.36, W * 0.16, W * 0.16, W * 0.16, W * 0.16]
    t = Table(rows, colWidths=col_w)
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0),    colors.HexColor(GREEN_PALE)),
        ("BACKGROUND",    (0, -1), (-1, -1),  colors.HexColor("#C8E6C9")),
        ("GRID",          (0, 0), (-1, -1),   0.4, colors.HexColor(GREEN_LIGHT)),
        ("ROWBACKGROUNDS",(0, 1), (-1, -2),
         [colors.white, colors.HexColor("#F9FBF9")]),
        ("TOPPADDING",    (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
    ]))
    story.append(t)
    story.append(Spacer(1, 20))

    # ── Badge da frota ─────────────────────────────────────────────
    _section_badge(story, badge_frota, W, s)

    # ── Rodapé ─────────────────────────────────────────────────────
    _footer(story, W, s)

    doc.build(story)
    return filename
