import gradio as gr
import pandas as pd

from pipeline.extract import extract_vehicle_emission_factors
from pipeline.transform import calculate_emissions
from pipeline.load import storage
from utilitarios.pdf_generator import generate_pdf_report, generate_fleet_pdf_report
from apresentacao import get_references, build_charts

# ── Cache de simulações ───────────────────────────────────────────────────────
latest_vehicle_result: dict = {}           # última simulação de veículo individual
latest_fleet_results:  list[dict] = []     # resultados consolidados da frota atual

# ── Constantes ────────────────────────────────────────────────────────────────
FUEL_OPTIONS = ["Gasolina", "Etanol", "Flex", "Diesel",
                "GNV", "BEV", "PHEV", "HEV", "MHEV"]

PLACEHOLDER_VEH = "— nenhum veículo cadastrado ainda —"
PLACEHOLDER_FLT = "— nenhuma frota criada ainda —"


# ════════════════════════════════════════════════════════════════════════════════
#  ABA 1 – CADASTRO
# ════════════════════════════════════════════════════════════════════════════════

def process_registration(name, category, fuel):
    """Cadastra um veículo e devolve: msg, tabela, lista atualizada p/ simulador,
    lista de checkboxes p/ criação de frota."""
    if not name.strip():
        return ("Por favor, indique um nome válido para o veículo/frota.",
                storage.get_fleet(),
                gr.update(choices=[PLACEHOLDER_VEH], value=PLACEHOLDER_VEH),
                gr.update(choices=[]))

    msg = storage.register_vehicle(name, category.lower(), fuel.lower())
    choices = storage.get_vehicle_names()

    return (
        msg,
        storage.get_fleet(),
        gr.update(choices=choices, value=choices[0] if choices else PLACEHOLDER_VEH),
        gr.update(choices=choices, value=[]),
    )


def create_fleet(selected_vehicles: list[str], fleet_name: str):
    """Cria uma frota a partir de uma lista de nomes de exibição."""
    if not selected_vehicles:
        return "Selecione ao menos um veículo para a frota.", storage.get_fleet()

    ids = []
    for disp in selected_vehicles:
        v = storage.get_vehicle_by_display(disp)
        if v:
            ids.append(v["id"])

    msg = storage.create_fleet(fleet_name, ids)

    fleet_choices = storage.get_fleet_names()
    return (
        msg,
        storage.get_fleet(),
        gr.update(choices=fleet_choices,
                  value=fleet_choices[0] if fleet_choices else PLACEHOLDER_FLT),
    )


# ════════════════════════════════════════════════════════════════════════════════
#  ABA 2 – SIMULADOR
# ════════════════════════════════════════════════════════════════════════════════

def _compute_emissions_for_vehicle(v_data: dict, km_val: float,
                                   tolls: int, parking: int) -> dict:
    """Executa cálculo ETL e devolve dict de resultado enriquecido."""
    df_factors = extract_vehicle_emission_factors()
    match = df_factors[
        (df_factors['categoria']   == v_data['categoria']) &
        (df_factors['combustivel'] == v_data['combustivel'])
    ]
    if match.empty:
        match = df_factors[
            df_factors['categoria'] == v_data['categoria']
        ].iloc[0:1]

    factor_row = match.iloc[0].to_dict()
    res = calculate_emissions(factor_row, km_val, tolls, parking)
    res['km_percorridos'] = km_val
    res['vehicle_name']   = v_data['nome']
    return res


def _badge_for(saved_kg: float) -> str:
    if saved_kg < 15.0:
        return "Bronze 🥉 (Iniciante na Mobilidade Verde)"
    elif saved_kg < 50.0:
        return "Prata 🥈 (Defensor da Sustentabilidade Urbana)"
    else:
        return "Ouro 🥇 (Herói de Baixo Carbono - Elegível para Isenções)"


def run_vehicle_simulation(selected_display: str,
                           category: str, fuel: str,
                           km_val: float, tolls: int, parking: int):
    """
    Simula emissões para um veículo.
    Se um veículo cadastrado estiver selecionado, usa seus dados;
    caso contrário usa os campos manuais (categoria + combustível).
    """
    global latest_vehicle_result

    # Decide se usa veículo cadastrado ou campos manuais
    v_data = storage.get_vehicle_by_display(selected_display or "")
    if v_data is None:
        # Fallback para campos manuais
        v_data = {
            "nome":       "Simulação Manual",
            "categoria":  category.lower(),
            "combustivel": fuel.lower(),
        }

    res = _compute_emissions_for_vehicle(v_data, km_val, tolls, parking)
    badge = _badge_for(res['evitado_kg'])
    res['badge'] = badge
    latest_vehicle_result = res

    output_html = f"""
    <div style='background-color:#F1F8E9;padding:15px;
                border-radius:8px;border-left:5px solid #4CAF50;'>
        <h3>📊 Resultado da Simulação – {res['vehicle_name']}</h3>
        <p><b>Pegada SEM Tag:</b> {res['sem_tag_kg']} kg de CO2e</p>
        <p><b>Pegada COM Tag:</b> {res['com_tag_kg']} kg de CO2e</p>
        <h4 style='color:#2E7D32;'>
            🌿 Total Evitado: {res['evitado_kg']} kg de CO2e
        </h4>
    </div>"""

    comparison_table = pd.DataFrame({
        "Origem do Impacto": [
            "Marcha Lenta (Fila)",
            "Picos de Arrancada",
            "Tickets de Papel",
        ],
        "Desperdício evitado": [
            f"{res['detalhes']['marcha_lenta_kg']} kg CO2",
            f"{res['detalhes']['aceleracao_kg']} kg CO2",
            f"{res['detalhes']['ticket_papel_kg']} kg CO2",
        ],
    })

    return output_html, comparison_table, badge


def run_fleet_simulation(selected_fleet: str,
                         km_val: float, tolls: int, parking: int):
    """Calcula e consolida emissões de todos os veículos de uma frota."""
    global latest_fleet_results

    vehicles = storage.get_vehicles_in_fleet(selected_fleet)
    if not vehicles:
        return ("<p style='color:red;'>Nenhum veículo nesta frota ou frota não encontrada.</p>",
                pd.DataFrame(), "—")

    results = []
    for v in vehicles:
        res = _compute_emissions_for_vehicle(v, km_val, tolls, parking)
        res['badge'] = _badge_for(res['evitado_kg'])
        results.append(res)

    latest_fleet_results = results

    total_sem  = sum(r['sem_tag_kg']  for r in results)
    total_com  = sum(r['com_tag_kg']  for r in results)
    total_evit = sum(r['evitado_kg']  for r in results)

    badge_frota = _badge_for(total_evit / max(len(results), 1))

    output_html = f"""
    <div style='background-color:#F1F8E9;padding:15px;
                border-radius:8px;border-left:5px solid #4CAF50;'>
        <h3>🚛 Resultado da Frota – {selected_fleet}
            ({len(results)} veículo(s))</h3>
        <p><b>Total Emissões SEM Tag:</b> {round(total_sem,3)} kg de CO2e</p>
        <p><b>Total Emissões COM Tag:</b> {round(total_com,3)} kg de CO2e</p>
        <h4 style='color:#2E7D32;'>
            🌿 Total Evitado pela Frota: {round(total_evit,3)} kg de CO2e
        </h4>
    </div>"""

    comparison_table = pd.DataFrame({
        "Veículo": [r['vehicle_name'] for r in results],
        "Sem Tag (kg)": [r['sem_tag_kg'] for r in results],
        "Com Tag (kg)": [r['com_tag_kg'] for r in results],
        "Evitado (kg)": [r['evitado_kg'] for r in results],
    })

    return output_html, comparison_table, badge_frota


# ════════════════════════════════════════════════════════════════════════════════
#  GERAÇÃO DE PDF
# ════════════════════════════════════════════════════════════════════════════════

def download_vehicle_pdf():
    global latest_vehicle_result
    if not latest_vehicle_result:
        return None
    name = latest_vehicle_result.get("vehicle_name", "veiculo").replace(" ", "_")
    filename = f"Relatorio_{name}.pdf"
    pdf_path = generate_pdf_report(latest_vehicle_result, filename=filename)
    return pdf_path


def download_fleet_pdf(selected_fleet: str):
    global latest_fleet_results
    if not latest_fleet_results:
        return None
    fleet_slug = selected_fleet.replace(" ", "_") if selected_fleet else "frota"
    filename = f"Relatorio_Frota_{fleet_slug}.pdf"
    pdf_path = generate_fleet_pdf_report(
        fleet_name=selected_fleet or "Frota",
        vehicles_results=latest_fleet_results,
        filename=filename,
    )
    return pdf_path


# ════════════════════════════════════════════════════════════════════════════════
#  INTERFACE GRADIO
# ════════════════════════════════════════════════════════════════════════════════

with gr.Blocks() as demo:
    gr.Markdown("# 🌿 Capiba Calcula")

    # ── ABA 1: CADASTRO ──────────────────────────────────────────────────────
    with gr.Tab("🚗 Painel Integrado de Gestão e Cadastro"):
        gr.Markdown("### Cadastre seus veículos ou gerencie sua frota corporativa")

        with gr.Row():
            v_name = gr.Textbox(
                label="Identificação do Veículo / ID da Frota",
                placeholder="Ex: Carro Diretor ou Caminhão Distribuidor Recife")
            v_cat  = gr.Dropdown(["Passeio", "SUV", "Pesado"],
                                 label="Categoria", value="Passeio")
            v_fuel = gr.Dropdown(FUEL_OPTIONS,
                                 label="Motorização / Combustível Predominante",
                                 value="Flex")

        btn_reg     = gr.Button("Confirmar Cadastro do Veículo", variant="primary")
        out_msg     = gr.Textbox(label="Status do Sistema Operacional")
        fleet_table = gr.DataFrame(label="Base de Dados de Veículos Ativos")

        # ── Sub-seção: Criar Frota ──────────────────────────────────────────
        gr.Markdown("---")
        gr.Markdown("### 🔗 Criar Frota a Partir dos Veículos Cadastrados")
        gr.Markdown(
            "Selecione os veículos que farão parte da frota, "
            "dê um nome e clique em **Criar Frota**.")

        vehicles_checkboxes = gr.CheckboxGroup(
            choices=[], label="Selecionar Veículos para a Frota")
        fleet_name_input = gr.Textbox(
            label="Nomear Frota",
            placeholder="Ex: Frota Logística Recife")
        btn_create_fleet = gr.Button("Criar Frota", variant="secondary")
        out_fleet_msg    = gr.Textbox(label="Status da Criação de Frota")

        # Estado compartilhado: choices do seletor de veículo no simulador
        # (atualizado quando um veículo é cadastrado)
        _sim_vehicle_choices = gr.State([PLACEHOLDER_VEH])
        _sim_fleet_choices   = gr.State([PLACEHOLDER_FLT])

    # ── ABA 2: SIMULADOR ─────────────────────────────────────────────────────
    with gr.Tab("🔢 Simulador de Emissões e Impacto ESG"):

        with gr.Row():
            # ── Coluna de entrada ─────────────────────────────────────────
            with gr.Column():
                gr.Markdown("### Parâmetros de Utilização")

                with gr.Tab("🚘 Veículo Individual"):
                    sel_vehicle = gr.Dropdown(
                        choices=[PLACEHOLDER_VEH],
                        value=PLACEHOLDER_VEH,
                        label="Veículo Cadastrado (opcional – substitui campos abaixo)")
                    gr.Markdown(
                        "<small>Se nenhum veículo cadastrado for selecionado, "
                        "os campos abaixo serão usados para a simulação.</small>")
                    calc_cat  = gr.Dropdown(
                        ["Passeio", "SUV", "Pesado"],
                        label="Selecione o Modelo (fallback manual)",
                        value="Passeio")
                    calc_fuel = gr.Dropdown(
                        FUEL_OPTIONS,
                        label="Motorização (fallback manual)",
                        value="Flex")

                    input_km_v      = gr.Number(
                        label="Quilometragem Percorrida (km)", value=120)
                    input_tolls_v   = gr.Slider(
                        0, 50, step=1, label="Pedágios Atravessados", value=4)
                    input_parking_v = gr.Slider(
                        0, 50, step=1, label="Entradas em Estacionamentos Manuais",
                        value=2)
                    btn_calc_v = gr.Button(
                        "Calcular Impacto – Veículo", variant="primary")

                with gr.Tab("🚛 Frota"):
                    sel_fleet = gr.Dropdown(
                        choices=[PLACEHOLDER_FLT],
                        value=PLACEHOLDER_FLT,
                        label="Frota Cadastrada")
                    input_km_f      = gr.Number(
                        label="Quilometragem Média por Veículo (km)", value=120)
                    input_tolls_f   = gr.Slider(
                        0, 50, step=1, label="Pedágios Médios por Veículo", value=4)
                    input_parking_f = gr.Slider(
                        0, 50, step=1,
                        label="Estacionamentos Médios por Veículo", value=2)
                    btn_calc_f = gr.Button(
                        "Calcular Impacto – Frota", variant="primary")

            # ── Coluna de resultados ──────────────────────────────────────
            with gr.Column():
                gr.Markdown("### Resultados Operacionais")
                output_res   = gr.HTML(
                    value="<p style='color:gray;'>Insira os parâmetros e "
                          "clique em Calcular.</p>")
                output_grid  = gr.DataFrame(label="Detalhamento das Emissões Evitadas")

                gr.Markdown("### 🏅 Gamificação e Recompensas")
                output_badge = gr.Textbox(label="Nível Atual do Usuário / Frota")

                gr.Markdown("### 📄 Exportar Relatório PDF")
                with gr.Row():
                    btn_pdf_v = gr.Button(
                        "📥 PDF – Veículo Selecionado", variant="secondary")
                    btn_pdf_f = gr.Button(
                        "📥 PDF – Frota Selecionada", variant="secondary")
                pdf_file = gr.File(label="Download do Relatório (.pdf)")

        # Eventos – Veículo
        btn_calc_v.click(
            run_vehicle_simulation,
            inputs=[sel_vehicle, calc_cat, calc_fuel,
                    input_km_v, input_tolls_v, input_parking_v],
            outputs=[output_res, output_grid, output_badge])

        # Eventos – Frota
        btn_calc_f.click(
            run_fleet_simulation,
            inputs=[sel_fleet, input_km_f, input_tolls_f, input_parking_f],
            outputs=[output_res, output_grid, output_badge])

        # Eventos – PDF
        btn_pdf_v.click(download_vehicle_pdf, inputs=[], outputs=[pdf_file])
        btn_pdf_f.click(download_fleet_pdf, inputs=[sel_fleet], outputs=[pdf_file])

    # ── ABA 3: FUNDAMENTAÇÃO ────────────────────────────────────────────────
    with gr.Tab("📊 Fundamentação de Pesquisa e Gráficos"):

        gr.HTML("""
        <div style="
            background: linear-gradient(135deg, #0F1F14 0%, #162417 100%);
            border-radius: 12px; padding: 20px 24px; margin-bottom: 8px;
            border: 1px solid #2A3D2E;">
          <h2 style="color:#E8F5E9; margin:0 0 6px; font-size:17px;">
            🔬 Embasamento Científico e Storytelling de Dados
          </h2>
          <p style="color:#7DAF85; font-size:13px; margin:0; line-height:1.6;">
            Os fatores de emissão utilizados nesta calculadora são extraídos
            via <strong style="color:#4CAF50">pipeline ETL</strong> de cinco
            fontes oficiais brasileiras e internacionais. O painel abaixo
            apresenta <strong style="color:#4CAF50">7 gráficos interligados</strong>
            — do ranking de emissão direta à projeção de CO₂ evitado acumulado —
            que contextualizam cada parâmetro adotado no simulador.
          </p>
        </div>""")

        gr.HTML(get_references())

        gr.HTML("""
        <div style="
            background:#162417; border-radius:10px; padding:14px 20px;
            border:1px solid #2A3D2E; margin-top:10px;">
          <p style="color:#7DAF85; font-size:11px; letter-spacing:.08em;
                    text-transform:uppercase; margin:0 0 8px;">
            Painel científico · 7 visualizações
          </p>
          <div style="display:grid; grid-template-columns:1fr 1fr; gap:6px 20px;
                      font-size:12px; color:#A5D6A7;">
            <span>① Ranking de emissão direta CO₂ por combustível</span>
            <span>② Pegada oculta: fila + arrancada (stacked)</span>
            <span>③ Consumo em marcha lenta por motorização</span>
            <span>④ Fatores de emissão GHG Protocol por combustível</span>
            <span>⑤ Ciclo de vida completo LCA (ANFAVEA/BCG)</span>
            <span>⑥ Projeção de CO₂ evitado acumulado (MOVER/ICCT)</span>
            <span style="grid-column:span 2">
              ⑦ Correlação: marcha lenta × consumo de arrancada por categoria
            </span>
          </div>
        </div>""")

        with gr.Row():
            btn_chart = gr.Button(
                "📈 Renderizar Painel Científico Completo",
                variant="primary", scale=2)

        output_img = gr.Image(
            label="Painel de Storytelling — Fatores ETL e Análise de Emissões",
            buttons=["download"],
            height=780)

        gr.HTML("""
        <p style="color:#455A64; font-size:11px; text-align:center; margin-top:4px;">
          O painel é gerado sob demanda a partir dos dados extraídos pelo ETL interno.
          Use o botão de download (ícone ↓) para salvar em alta resolução.
        </p>""")

        btn_chart.click(build_charts, inputs=[], outputs=[output_img])

    # ════════════════════════════════════════════════════════════════════════
    #  EVENTOS QUE CRUZAM ABAS
    # ════════════════════════════════════════════════════════════════════════

    # Cadastrar veículo → atualiza tabela, dropdown do simulador e checkboxes
    btn_reg.click(
        process_registration,
        inputs=[v_name, v_cat, v_fuel],
        outputs=[out_msg, fleet_table, sel_vehicle, vehicles_checkboxes])

    # Criar frota → atualiza tabela, dropdown de frotas no simulador
    btn_create_fleet.click(
        create_fleet,
        inputs=[vehicles_checkboxes, fleet_name_input],
        outputs=[out_fleet_msg, fleet_table, sel_fleet])


if __name__ == "__main__":
    demo.launch(theme=gr.themes.Soft(primary_hue="green"))
