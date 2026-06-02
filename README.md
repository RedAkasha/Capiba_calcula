# 🌿 Capiba Calcula

**Calculadora de pegada de carbono veicular com interface web, gamificação e relatórios PDF.**

Desenvolvida para o **Desafio Edenred**, a aplicação quantifica as emissões de CO₂e evitadas pelo uso de tag de pedágio e estacionamento — eliminando filas, picos de aceleração e tickets de papel — com base em metodologias oficiais do GHG Protocol Brasil, INMETRO/PBE Veicular e CETESB.

---

## 📋 Funcionalidades

| Módulo | O que faz |
|---|---|
| **Painel de Cadastro** | Registra veículos (nome, categoria, motorização) e os agrupa em frotas nomeadas |
| **Simulador de Emissões** | Calcula CO₂e evitado para um veículo cadastrado ou para toda uma frota; aceita km, pedágios e estacionamentos como entrada |
| **Gamificação** | Atribui medalha Bronze / Prata / Ouro com base no total de emissões evitadas |
| **Relatório PDF** | Exporta relatório individual (por veículo) ou consolidado (por frota) com gráficos, KPIs e tabelas detalhadas |
| **Fundamentação Científica** | Exibe referências e renderiza gráficos ETL comparando fatores de emissão por categoria e combustível |

---

## 🗂️ Estrutura do Repositório

```
capiba_calcula/
│
├── app.py                        # Ponto de entrada — interface Gradio
├── apresentacao.py               # Referências científicas e gráficos ETL
├── requirements.txt              # Dependências do projeto
├── .gitignore
├── README.md
│
├── pipeline/                     # Camada ETL
│   ├── __init__.py
│   ├── extract.py                # Fatores de emissão (INMETRO/PBE + CETESB)
│   ├── transform.py              # Cálculo comparativo de CO₂e (com/sem tag)
│   └── load.py                   # Armazenamento em memória de veículos e frotas
│
└── utilitarios/
    ├── __init__.py
    └── pdf_generator.py          # Geração de PDFs individuais e de frota
```

---

## ⚙️ Instalação e Execução

### Pré-requisitos

- Python **3.10** ou superior (testado com 3.12)
- `pip` atualizado

### 1. Clone o repositório

```bash
git clone https://github.com/seu-usuario/capiba-calcula.git
cd capiba-calcula
```

### 2. Crie e ative um ambiente virtual (recomendado)

```bash
python -m venv .venv

# Linux / macOS
source .venv/bin/activate

# Windows
.venv\Scripts\activate
```

### 3. Instale as dependências

```bash
pip install -r requirements.txt
```

### 4. Execute a aplicação

```bash
python app.py
```

A interface estará disponível em `http://localhost:7860` no navegador.

---

## 🔬 Metodologia de Cálculo

O simulador compara dois cenários para o mesmo percurso:

### Cenário **sem** tag
Além das emissões diretas de rodagem, são contabilizadas três fontes de desperdício:

1. **Marcha lenta em fila** — tempo parado estimado em 3 min/pedágio e 2 min/estacionamento, multiplicado pelo consumo específico em marcha lenta (l/h) e pelo fator de emissão do combustível.
2. **Pico de aceleração** — consumo adicional (ml) de cada arrancada após parada, multiplicado pelo fator de emissão.
3. **Ticket de papel** — 0,015 kg CO₂e por ticket emitido (ciclo de vida do papel).

### Cenário **com** tag
Apenas as emissões diretas de rodagem: `distância (km) × fator de emissão (g CO₂/km) ÷ 1.000`.

### Fatores de emissão de combustível utilizados

| Combustível | Fator (kg CO₂e / l) | Fonte |
|---|---|---|
| Diesel | 2,603 | GHG Protocol Brasil |
| Gasolina / Flex / HEV / MHEV | 2,212 | GHG Protocol Brasil |
| PHEV | 0,945 | Média ponderada elétrico/gasolina |
| GNV / Etanol | 1,457 | GHG Protocol Brasil |
| BEV | 0,125 | Fator de emissão da rede elétrica brasileira |

---

## 🏅 Sistema de Gamificação

| Medalha | CO₂e evitado (por veículo) | Benefício |
|---|---|---|
| 🥉 Bronze | < 15 kg | Iniciante na Mobilidade Verde |
| 🥈 Prata | 15 – 50 kg | Defensor da Sustentabilidade Urbana |
| 🥇 Ouro | > 50 kg | Herói de Baixo Carbono — elegível para isenções |

---

## 📄 Relatório PDF

Ao clicar em **PDF – Veículo Selecionado** ou **PDF – Frota Selecionada**, é gerado um relatório executivo contendo:

- **KPIs em destaque** — emissões sem tag, com tag, CO₂e evitado e quilômetros percorridos
- **Gráfico de linha** — impacto ambiental × quilometragem projetada
- **Gráfico de barras** — comparativo de emissões
- **Gráfico de rosca** — composição das emissões evitadas (marcha lenta, aceleração, papel)
- **Gauge de eficiência verde** — percentual de redução atingido
- **Tabela detalhada** — métricas individuais em kg CO₂e
- *(somente no relatório de frota)* tabela comparativa por veículo com totalizador
- **Perfil ecológico** — medalha de gamificação

---

## 📚 Referências Científicas

- [INMETRO – Programa Brasileiro de Etiquetagem Veicular (PBE)](https://www.gov.br/inmetro/pt-br/assuntos/regulamentacao/avaliacao-da-conformidade/programa-brasileiro-de-etiquetagem/tabelas-de-eficiencia-energetica/veiculos-automotivos-pbe-veicular)
- [CETESB – Emissão Veicular: Publicações e Relatórios](https://www.cetesb.sp.gov.br/cetesb/qualidade_ambiental/emissao_veicular/publicacoes_e_relatorios)
- [Programa Brasileiro GHG Protocol – FGV EAESP](https://eaesp.fgv.br/centros/centro-estudos-sustentabilidade/projetos/programa-brasileiro-ghg-protocol)
- [ANFAVEA & BCG – Caminhos da Descarbonização: pegada de carbono no ciclo de vida do veículo](https://web-assets.bcg.com/30/97/e8e78976425983c13e92de4af084/caminhos-descarbonizacao-setor-automotivo-brasil.pdf)
- [ICCT – Emissões de CO₂ dos carros de passeio (Programa MOVER: Maio 2024 – Junho 2025)](https://theicct.org/emissoes-de-co2-dos-carros-de-passeio-segundo-parametros-oficiais-do-programa-mover-maio-2024-junho-2025/)

---

## 🤝 Contribuição

1. Faça um fork do projeto
2. Crie uma branch para sua feature: `git checkout -b feature/minha-feature`
3. Faça commit das alterações: `git commit -m 'feat: descrição da feature'`
4. Envie para o repositório remoto: `git push origin feature/minha-feature`
5. Abra um Pull Request

---

## 📝 Licença

Distribuído sob a licença MIT. Consulte o arquivo `LICENSE` para mais detalhes.
