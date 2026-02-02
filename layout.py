# layout.py
# Layout da aplicação

from dash import dcc, html, dash_table

# ======================================================
# VALORES PADRÃO DOS PARÂMETROS (dias)
# ======================================================
DEFAULT_DIAS_ALARMES = 7
DEFAULT_DIAS_INSIGHTS = 30
DEFAULT_DIAS_NOTAS = 0


def upload_box(label: str, upload_id: str, subtitle: str = ""):
    """Componente reutilizável de upload com status."""
    return html.Div([
        html.Div(label, style={
            "fontWeight": "bold",
            "fontSize": "16px",
            "marginBottom": "5px",
        }),
        html.Div(subtitle, style={
            "fontSize": "11px",
            "color": "#666",
            "marginBottom": "8px",
        }) if subtitle else None,
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

    html.H1("PRIORIZAÇÃO DE ANÁLISE", style={"textAlign": "center", "marginBottom": "30px"}),

    # --- uploads ---
    html.H4("UPLOADS OBRIGATÓRIOS"),
    html.Div([
        upload_box(
            "BASE.XLSX",
            "upload-base",
            "MÁQUINA | SUBCONJUNTO | SPOT ID | SPOT NAME | ANALISTA RESPONSÁVEL"
        ),
        upload_box(
            "MOSAIC REPORT.CSV",
            "upload-mosaic",
        ),
        upload_box(
            "NOTAS M4.XLSX",
            "upload-notas",
            "Local de instalação | Ordem | Nota | Descrição | Início desejado | Conclusão desejada | Executado por | Status usuário"
        ),
        upload_box(
            "ORDENS DAS NOTAS.XLSX",
            "upload-ordem-notas",
            "Tipo de ordem | Local de instalação | Data-base do início | Texto breve | Ordem | Denominação do loc.instalação | Grupo planej. | Nota | Status do sistema"
        ),
        upload_box(
            "ORDENS DOS PLANOS AV.XLSX",
            "upload-ordem-planos",
            "Tipo de ordem | Local de instalação | Data-base do início | Texto breve | Ordem | Denominação do loc.instalação | Grupo planej. | Nota | Status do sistema | Status usuário"
        ),
        upload_box(
            "INSIGHTS.XLSX",
            "upload-insights",
        ),
    ], style={
        "display": "grid",
        "gridTemplateColumns": "repeat(3, 1fr)",
        "gap": "15px",
    }),

    html.Hr(),

    # --- parâmetros com valores padrão ---
    html.H4("PARÂMETROS (DIAS)"),
    html.Div([
        html.Div([
            html.Label("LINHA DE CORTE PARA ALARMES (ÚLTIMA ANÁLISE HÁ)"),
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
            html.Label("LINHA DE CORTE PARA INSIGHTS (ÚLTIMA ANÁLISE HÁ)"),
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
            html.Label("LINHA DE CORTE PARA NOTAS VENCIDAS (NOTA VENCIDA HÁ)"),
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
        html.Label("FILTRO DE ALARME", style={"fontWeight": "bold"}),
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
    html.H4("IMPACTO POR ANALISTA"),
    dash_table.DataTable(
        id="tabela-analista",
        page_size=5,
        style_table={"width": "40%"},
    ),

    html.Hr(),

    # --- tabela principal ---
    html.H4("LISTA FINAL"),
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
], style={
    "backgroundColor": "#f5f5f5",
    "padding": "30px",
    "minHeight": "100vh",
})
