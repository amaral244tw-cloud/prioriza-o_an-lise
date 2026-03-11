# layout.py
# Layout da aplicação

from dash import dcc, html, dash_table

# ======================================================
# VALORES PADRÃO DOS PARÂMETROS (dias)
# ======================================================
DEFAULT_DIAS_ALARMES = 15
DEFAULT_DIAS_INSIGHTS = 7
DEFAULT_DIAS_NOTAS = 15


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

    # --- botão para abrir modal de uploads ---
    html.Button(
        "📁 Upload de Arquivos",
        id="btn-abrir-uploads",
        n_clicks=0,
        style={
            "fontSize": "16px",
            "padding": "12px 30px",
            "backgroundColor": "#1976d2",
            "color": "white",
            "border": "none",
            "borderRadius": "5px",
            "cursor": "pointer",
            "fontWeight": "bold",
            "marginBottom": "20px",
        }
    ),

    # --- modal de uploads (inicialmente oculto) ---
    html.Div(
        id="modal-uploads",
        style={"display": "none"},
        children=[
            html.Div([
                # Header do modal
                html.Div([
                    html.H3("📁 Upload de Arquivos", style={"margin": "0"}),
                    html.Button(
                        "✕",
                        id="btn-fechar-modal",
                        n_clicks=0,
                        style={
                            "position": "absolute",
                            "top": "15px",
                            "right": "15px",
                            "border": "none",
                            "background": "transparent",
                            "fontSize": "24px",
                            "cursor": "pointer",
                            "color": "#666",
                        }
                    ),
                ], style={
                    "position": "relative",
                    "padding": "20px",
                    "borderBottom": "1px solid #ddd",
                    "backgroundColor": "#f8f9fa",
                }),

                # Conteúdo do modal com os uploads
                html.Div([
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
                            "Local de instalação | Ordem | Nota | Conclusão desejada"
                        ),
                        upload_box(
                            "ORDENS DAS NOTAS.XLSX",
                            "upload-ordem-notas",
                            "Ordem | Status do sistema"
                        ),
                        upload_box(
                            "ORDENS DOS PLANOS AV.XLSX",
                            "upload-ordem-planos",
                            "Local de instalação | Ordem | Status do sistema"
                        ),
                        upload_box(
                            "INSIGHTS.XLSX",
                            "upload-insights",
                            "Lista de máquinas (primeira coluna)"
                        ),
                    ], style={
                        "display": "grid",
                        "gridTemplateColumns": "repeat(2, 1fr)",
                        "gap": "15px",
                    }),

                    # Botão processar
                    html.Div([
                        html.Button(
                            "✓ Processar Dados",
                            id="btn-processar-uploads",
                            n_clicks=0,
                            style={
                                "fontSize": "16px",
                                "padding": "12px 40px",
                                "backgroundColor": "#4caf50",
                                "color": "white",
                                "border": "none",
                                "borderRadius": "5px",
                                "cursor": "pointer",
                                "fontWeight": "bold",
                                "marginTop": "20px",
                            }
                        ),
                    ], style={"textAlign": "center"}),

                ], style={"padding": "20px"}),

            ], style={
                "position": "fixed",
                "top": "50%",
                "left": "50%",
                "transform": "translate(-50%, -50%)",
                "backgroundColor": "white",
                "borderRadius": "10px",
                "boxShadow": "0 4px 20px rgba(0,0,0,0.3)",
                "zIndex": "1001",
                "maxWidth": "900px",
                "width": "90%",
                "maxHeight": "90vh",
                "overflowY": "auto",
            })
        ]
    ),

    # Overlay escuro de fundo
    html.Div(
        id="modal-overlay",
        style={
            "display": "none",
            "position": "fixed",
            "top": "0",
            "left": "0",
            "width": "100%",
            "height": "100%",
            "backgroundColor": "rgba(0, 0, 0, 0.5)",
            "zIndex": "1000",
        },
        children=[],
    ),

    html.Hr(),

    # --- filtro global de coleta atualizada ---
    html.H4("FILTRO GLOBAL"),
    html.Div([
        html.Label("LINHA DE CORTE PARA COLETA ATUALIZADA (ÚLTIMA COLETA HÁ DIAS)"),
        html.Div("Máquinas onde TODOS os spots têm coleta defasada serão removidas da lista final.", 
                 style={"fontSize": "12px", "color": "#666", "marginBottom": "8px"}),
        dcc.Input(
            id="dias-coleta-atualizada",
            type="number",
            value=7,
            min=0,
            debounce=True,
            style={"width": "100px"},
        ),
    ], style={"marginBottom": "15px"}),

    html.Hr(),

    # --- stores internos ---
    dcc.Store(id="df-base"),
    dcc.Store(id="df-final"),
    dcc.Store(id="filtros-por-analista", data={}),  # Store para filtros individuais
    
    # Loading indicator
    dcc.Loading(
        id="loading-processamento",
        type="circle",
        fullscreen=True,
        children=html.Div(id="loading-output")
    ),

    # --- tabela resumo ---
    html.H4("IMPACTO POR ANALISTA"),
    
    # Container para filtros dinâmicos por analista
    html.Div(
        id="filtros-analistas-container",
        children=html.Div(
            "⚠️ Aguardando upload dos arquivos para gerar filtros por analista...",
            style={"color": "#666", "fontStyle": "italic", "padding": "10px"}
        ),
        style={"marginBottom": "20px"}
    ),
    
    dash_table.DataTable(
        id="tabela-analista",
        page_size=10,
        style_table={"width": "500px"},
        style_data_conditional=[
            {
                'if': {
                    'filter_query': '{QUANTIDADE DE PONTOS} >= 400',
                    'column_id': 'QUANTIDADE DE PONTOS'
                },
                'backgroundColor': '#ff4444',
                'color': 'white',
                'fontWeight': 'bold'
            },
            {
                'if': {
                    'filter_query': '{QUANTIDADE DE PONTOS} >= 300 && {QUANTIDADE DE PONTOS} < 400',
                    'column_id': 'QUANTIDADE DE PONTOS'
                },
                'backgroundColor': '#ffeb3b',
                'color': 'black',
                'fontWeight': 'bold'
            },
            {
                'if': {
                    'filter_query': '{QUANTIDADE DE PONTOS} < 300',
                    'column_id': 'QUANTIDADE DE PONTOS'
                },
                'backgroundColor': '#4caf50',
                'color': 'white',
                'fontWeight': 'bold'
            },
        ],
        style_cell={
            'textAlign': 'left'
        },
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
        style_cell={
            'textAlign': 'left',
            'padding': '8px',
        },
        style_data_conditional=[
            # STATUS DO PONTO DE MONITORAMENTO
            {
                'if': {
                    'filter_query': '{STATUS DO PONTO DE MONITORAMENTO} is blank || {STATUS DO PONTO DE MONITORAMENTO} = ""',
                    'column_id': 'STATUS DO PONTO DE MONITORAMENTO'
                },
                'backgroundColor': '#e0e0e0',
                'color': '#666'
            },
            {
                'if': {
                    'filter_query': '{STATUS DO PONTO DE MONITORAMENTO} contains "no-alert"',
                    'column_id': 'STATUS DO PONTO DE MONITORAMENTO'
                },
                'backgroundColor': '#4caf50',
                'color': 'white',
                'fontWeight': 'bold'
            },
            {
                'if': {
                    'filter_query': '{STATUS DO PONTO DE MONITORAMENTO} contains "a1" || {STATUS DO PONTO DE MONITORAMENTO} contains "A1"',
                    'column_id': 'STATUS DO PONTO DE MONITORAMENTO'
                },
                'backgroundColor': '#ffeb3b',
                'color': 'black',
                'fontWeight': 'bold'
            },
            {
                'if': {
                    'filter_query': '{STATUS DO PONTO DE MONITORAMENTO} contains "a2" || {STATUS DO PONTO DE MONITORAMENTO} contains "A2"',
                    'column_id': 'STATUS DO PONTO DE MONITORAMENTO'
                },
                'backgroundColor': '#ff4444',
                'color': 'white',
                'fontWeight': 'bold'
            },
            
            # STATUS DA ÚLTIMA ANÁLISE
            {
                'if': {
                    'filter_query': '{STATUS DA ÚLTIMA ANÁLISE} = "NUNCA ANALISADO"',
                    'column_id': 'STATUS DA ÚLTIMA ANÁLISE'
                },
                'backgroundColor': '#e0e0e0',
                'color': '#666'
            },
            {
                'if': {
                    'filter_query': '{STATUS DA ÚLTIMA ANÁLISE} = "NORMAL"',
                    'column_id': 'STATUS DA ÚLTIMA ANÁLISE'
                },
                'backgroundColor': '#4caf50',
                'color': 'white',
                'fontWeight': 'bold'
            },
            {
                'if': {
                    'filter_query': '{STATUS DA ÚLTIMA ANÁLISE} = "ALERTA"',
                    'column_id': 'STATUS DA ÚLTIMA ANÁLISE'
                },
                'backgroundColor': '#ffeb3b',
                'color': 'black',
                'fontWeight': 'bold'
            },
            {
                'if': {
                    'filter_query': '{STATUS DA ÚLTIMA ANÁLISE} = "INTERVENÇÃO"',
                    'column_id': 'STATUS DA ÚLTIMA ANÁLISE'
                },
                'backgroundColor': '#ff4444',
                'color': 'white',
                'fontWeight': 'bold'
            },
        ],
    ),

    html.Br(),
    html.Button("Download Excel", id="btn-download"),
    dcc.Download(id="download-excel"),
], style={
    "backgroundColor": "#f5f5f5",
    "padding": "30px",
    "minHeight": "100vh",
})
