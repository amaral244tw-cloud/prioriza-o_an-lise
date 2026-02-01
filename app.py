import base64
import io
from datetime import datetime
import pandas as pd

from dash import Dash, dcc, html, Input, Output, State, dash_table
from dash.exceptions import PreventUpdate


# ======================================================
# FUNÇÕES AUXILIARES
# ======================================================

def parse_contents(contents, filename):
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)

    if filename.endswith(".csv"):
        return pd.read_csv(io.StringIO(decoded.decode("utf-8")))
    return pd.read_excel(io.BytesIO(decoded))


def concat_values(series):
    vals = series.dropna().astype(str).unique()
    return " | ".join(vals) if len(vals) else ""


def days_diff(date_str):
    if pd.isna(date_str) or str(date_str).strip() == "":
        return None

    data = pd.to_datetime(
        date_str,
        format="%d/%m/%Y",
        errors="coerce"
    )

    if pd.isna(data):
        return None

    return (datetime.today() - data).days


# ======================================================
# APP
# ======================================================

app = Dash(__name__)
app.title = "Priorização de Monitoramento"


def upload_box(label, upload_id):
    return html.Div([
        html.B(label),
        dcc.Upload(
            id=upload_id,
            children=html.Div("Clique ou arraste o arquivo"),
            style={
                "border": "2px dashed #999",
                "padding": "12px",
                "textAlign": "center"
            }
        ),
        html.Div(id=f"status-{upload_id}")
    ])


# ======================================================
# LAYOUT
# ======================================================

app.layout = html.Div([

    html.H2("App de Priorização de Monitoramento e Manutenção"),

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
        "gap": "15px"
    }),

    html.Hr(),

    html.H4("Parâmetros (dias)"),
    html.Div([
        dcc.Input(id="dias-alarmes", type="number", placeholder="Alarmes"),
        dcc.Input(id="dias-insights", type="number", placeholder="Insights"),
        dcc.Input(id="dias-notas", type="number", placeholder="Notas vencidas"),
    ], style={"display": "flex", "gap": "20px"}),

    html.Br(),
    html.Button("PROCESSAR DADOS", id="btn-processar", style={
        "backgroundColor": "#2ecc71",
        "color": "white",
        "padding": "10px",
        "fontWeight": "bold"
    }),

    html.Hr(),

    dcc.Store(id="store-base"),
    dcc.Store(id="store-mosaic"),
    dcc.Store(id="store-notas"),
    dcc.Store(id="store-ordem-notas"),
    dcc.Store(id="store-ordem-planos"),
    dcc.Store(id="store-insights"),
    dcc.Store(id="store-final"),

    html.H4("Impacto por analista"),
    dash_table.DataTable(id="tabela-analista"),

    html.Hr(),

    html.H4("Lista final"),
    dash_table.DataTable(
        id="tabela-final",
        page_action="none",
        filter_action="native",
        sort_action="native",
        style_table={"height": "500px", "overflowY": "auto"}
    ),

    html.Br(),
    html.Button("Download Excel", id="btn-download"),
    dcc.Download(id="download-excel")
])


# ======================================================
# CALLBACKS DE UPLOAD (UM POR ARQUIVO)
# ======================================================

def upload_callback(upload_id, store_id):
    @app.callback(
        Output(store_id, "data"),
        Output(f"status-{upload_id}", "children"),
        Input(upload_id, "contents"),
        State(upload_id, "filename"),
        prevent_initial_call=True
    )
    def _callback(contents, filename):
        df = parse_contents(contents, filename)
        return (
            df.to_dict("records"),
            html.Div(f"✔ {filename}", style={"color": "green"})
        )


upload_callback("upload-base", "store-base")
upload_callback("upload-mosaic", "store-mosaic")
upload_callback("upload-notas", "store-notas")
upload_callback("upload-ordem-notas", "store-ordem-notas")
upload_callback("upload-ordem-planos", "store-ordem-planos")
upload_callback("upload-insights", "store-insights")


# ======================================================
# PROCESSAMENTO PRINCIPAL
# ======================================================

@app.callback(
    Output("tabela-final", "data"),
    Output("tabela-final", "columns"),
    Output("tabela-analista", "data"),
    Output("tabela-analista", "columns"),
    Output("store-final", "data"),
    Input("btn-processar", "n_clicks"),
    State("store-base", "data"),
    State("store-mosaic", "data"),
    State("store-notas", "data"),
    State("store-ordem-notas", "data"),
    State("store-ordem-planos", "data"),
    State("store-insights", "data"),
    State("dias-alarmes", "value"),
    State("dias-insights", "value"),
    State("dias-notas", "value"),
    prevent_initial_call=True
)
def processar(n, base, mosaic, notas, ordem_notas, ordem_planos, insights,
              dias_alarm, dias_insight, dias_nota):

    if not all([base, mosaic, notas, ordem_notas, ordem_planos, insights]):
        raise PreventUpdate

    base = pd.DataFrame(base)
    mosaic = pd.DataFrame(mosaic)
    notas = pd.DataFrame(notas)
    ordem_notas = pd.DataFrame(ordem_notas)
    ordem_planos = pd.DataFrame(ordem_planos)
    insights = pd.DataFrame(insights)

    mosaic["DATA_FMT"] = pd.to_datetime(
        mosaic["analysisCreatedAt"], errors="coerce"
    ).dt.strftime("%d/%m/%Y")

    base["STATUS DO PONTO DE MONITORAMENTO"] = base["SPOT ID"].map(
        mosaic.groupby("spotId")["status"].apply(concat_values)
    )

    base["DATA DA ÚLTIMA ANÁLISE"] = base["SPOT ID"].map(
        mosaic.groupby("spotId")["DATA_FMT"].apply(concat_values)
    )

    base["INSIGHTS"] = base["MÁQUINA"].isin(insights.iloc[:, 0]).map(
        lambda x: "SIM" if x else ""
    )

    cond1 = base["STATUS DO PONTO DE MONITORAMENTO"].str.contains("A1|A2", na=False)
    cond2 = base["INSIGHTS"] == "SIM"

    df_final = base[cond1 | cond2]

    resumo = (
        df_final
        .groupby("ANALISTA RESPONSÁVEL")
        .size()
        .reset_index(name="QUANTIDADE DE PONTOS")
    )

    return (
        df_final.to_dict("records"),
        [{"name": c, "id": c} for c in df_final.columns],
        resumo.to_dict("records"),
        [{"name": c, "id": c} for c in resumo.columns],
        df_final.to_dict("records")
    )


# ======================================================
# DOWNLOAD
# ======================================================

@app.callback(
    Output("download-excel", "data"),
    Input("btn-download", "n_clicks"),
    State("store-final", "data"),
    prevent_initial_call=True
)
def download_excel(n, data):
    df = pd.DataFrame(data)
    return dcc.send_data_frame(
        df.to_excel,
        "LISTA_FINAL_PRIORIZADA.xlsx",
        index=False
    )


# ======================================================
# RUN
# ======================================================

if __name__ == "__main__":
    app.run_server(debug=False)
