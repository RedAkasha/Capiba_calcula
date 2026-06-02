import matplotlib.pyplot as plt
import seaborn as sns
from pipeline.extract import extract_vehicle_emission_factors


def get_references():
    return """
    REFERÊNCIAS CIENTÍFICAS E METODOLÓGICAS:
    * INMETRO - Dados dos veículos leves aprovados no Programa Brasileiro de Etiquetagem (PBE)

    https://www.gov.br/inmetro/pt-br/assuntos/regulamentacao/avaliacao-da-conformidade/programa-brasileiro-de-etiquetagem/tabelas-de-eficiencia-energetica/veiculos-automotivos-pbe-veicular

    * Companhia Ambiental do Estado de São Paulo (CETESB) - Emissão Veicular

    https://www.cetesb.sp.gov.br/cetesb/qualidade_ambiental/emissao_veicular/publicacoes_e_relatorios

    * Programa Brasileiro GHG Protocol

    https://eaesp.fgv.br/centros/centro-estudos-sustentabilidade/projetos/programa-brasileiro-ghg-protocol

    * ANFAVEA e BCG - Caminhos da Descarbonização: pegada de carbono no ciclo de vida do veículo

    https://web-assets.bcg.com/30/97/e8e78976425983c13e92de4af084/caminhos-descarbonizacao-setor-automotivo-brasil.pdf

    * ICCT - Emissões de CO2 dos carros de passeio (Programa MOVER: Maio 2024 – Junho 2025)

    https://theicct.org/emissoes-de-co2-dos-carros-de-passeio-segundo-parametros-oficiais-do-programa-mover-maio-2024-junho-2025/
    """


def build_charts():
    """Gera gráficos científicos baseados nos dados coletados do processo de ETL."""
    df = extract_vehicle_emission_factors()
    sns.set_theme(style="whitegrid")

    fig, ax = plt.subplots(1, 2, figsize=(14, 6))

    sns.barplot(data=df, x="categoria", y="co2_g_km",
                hue="combustivel", ax=ax[0], palette="Greens_r")
    ax[0].set_title("Fatores de Emissão de CO2 por Classe e Combustível")
    ax[0].set_ylabel("Emissão Direta (g CO2 / km)")
    ax[0].set_xlabel("Categoria Corporativa")

    sns.scatterplot(data=df, x="consumo_marcha_lenta_l_h",
                    y="adicional_aceleracao_ml",
                    hue="categoria", s=100, ax=ax[1])
    ax[1].set_title("Pegada Oculta: Consumo na Fila vs Pico de Arrancada")
    ax[1].set_xlabel("Marcha Lenta (Litros / Hora)")
    ax[1].set_ylabel("Consumo Adicional por Arrancada (ml)")

    plt.tight_layout()
    chart_path = "analise_cientifica_emissoes.png"
    plt.savefig(chart_path)
    plt.close()
    return chart_path
