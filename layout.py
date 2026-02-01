# layout.py
# Layout da aplicação

from dash import dcc, html, dash_table

# ======================================================
# VALORES PADRÃO DOS PARÂMETROS (dias)
# ======================================================
DEFAULT_DIAS_ALARMES = 7
DEFAULT_DIAS_INSIGHTS = 30
DEFAULT_DIAS_NOTAS = 0


def upload_box(label: str, upload_id: str):
    """Componente reutilizável de upload com status."""
    return html.Div([
        html.Div(label, style={"fontWeight": "bold"}),
        dcc.Upload(
            id=upload_id,
            children=html.Div("Clique ou arraste o arquivo"),
            style={
                "border": "2px dashed #999",
                "padding": "12px",
                "textAlign": "center",
                "cursor": "pointer",
            },
        ),
        html.Div(id=f"status-{upload_id}"),
    ])


layout = html.Div([

    html.H2("App de Priorização de Monitoramento e Manutenção"),

    # --- uploads ---
    html.H4("Uploads obrigatórios"),
    html.Div([
        upload_box("BASE", "upload-base"),
        upload_box("MOSAIC REPORT", "upload-mosaic"),
        upload_box("NOTAS M4", "upload-notas"),
        upload_box("ORDENS DAS NOTAS", "upload-ordem-notas"),
        upload_box("ORDENS DOS PLANOS AV", "upload-ordem-planos"),
        upload_box("INSIGHTS", "upload-insights"),
    ], style={
        "display": "grid",
        "gridTemplateColumns": "repeat(3, 1fr)",
        "gap": "15px",
    }),

    html.Hr(),

    # --- parâmetros com valores padrão ---
    html.H4("Parâmetros (dias)"),
    html.Div([
        html.Div([
            html.Label("Linha de corte para alarmes (última análise há)"),
            dcc.Input(
                id="dias-alarmes",
                type="number",
                value=DEFAULT_DIAS_ALARMES,
                min=0,
                debounce=True,
                style={"width": "100%"},
            ),
        ]),
        html.Div([
            html.Label("Linha de corte para insights (última análise há)"),
            dcc.Input(
                id="dias-insights",
                type="number",
                value=DEFAULT_DIAS_INSIGHTS,
                min=0,
                debounce=True,
                style={"width": "100%"},
            ),
        ]),
        html.Div([
            html.Label("Linha de corte para notas vencidas (nota vencida há)"),
            dcc.Input(
                id="dias-notas",
                type="number",
                value=DEFAULT_DIAS_NOTAS,
                min=0,
                debounce=True,
                style={"width": "100%"},
            ),
        ]),
    ], style={"display": "flex", "gap": "30px"}),

    html.Br(),

    # --- filtro de alarme ---
    html.Div([
        html.Label("Filtro de alarme", style={"fontWeight": "bold"}),
        dcc.Checklist(
            id="filtro-alarme",
            options=[
                {"label": " A1", "value": "A1"},
                {"label": " A2", "value": "A2"},
            ],
            value=["A1", "A2"],  # ambos selecionados por padrão
            inline=True,
        ),
    ]),

    html.Hr(),

    # --- stores internos ---
    dcc.Store(id="df-base"),
    dcc.Store(id="df-final"),

    # --- tabela resumo ---
    html.H4("Impacto por analista"),
    dash_table.DataTable(
        id="tabela-analista",
        page_size=5,
        style_table={"width": "40%"},
    ),

    html.Hr(),

    # --- tabela principal ---
    html.H4("Lista final"),
    dash_table.DataTable(
        id="tabela-final",
        filter_action="native",
        sort_action="native",
        page_action="none",
        style_table={
            "height": "500px",
            "overflowY": "auto",
        },
    ),

    html.Br(),
    html.Button("Download Excel", id="btn-download"),
    dcc.Download(id="download-excel"),
])
