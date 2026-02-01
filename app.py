
# app.py
# App de Priorização de Monitoramento e Manutenção
# Plotly Dash

import base64, io
from datetime import datetime
import pandas as pd
from dash import Dash, dcc, html, Input, Output, State, dash_table
from dash.exceptions import PreventUpdate


def parse_contents(contents, filename):
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    if filename.endswith('.csv'):
        return pd.read_csv(io.StringIO(decoded.decode('utf-8')))
    return pd.read_excel(io.BytesIO(decoded))


def concat_values(series):
    vals = series.dropna().astype(str).unique()
    return " | ".join(vals) if len(vals) > 0 else ""


def days_diff(date_str):
    if pd.isna(date_str) or str(date_str).strip() == "":
        return None
    try:
        return (datetime.today() - pd.to_datetime(date_str, dayfirst=True)).days
    except Exception:
        return None


app = Dash(__name__)
app.title = "Priorização de Monitoramento"


def upload_box(label, upload_id):
    return html.Div([
        html.Div(label, style={"fontWeight": "bold"}),
        dcc.Upload(
            id=upload_id,
            children=html.Div("Clique ou arraste o arquivo"),
            style={
                "border": "2px dashed #999",
                "padding": "12px",
                "textAlign": "center",
                "cursor": "pointer"
            }
        ),
        html.Div(id=f"status-{upload_id}")
    ])


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
        html.Div([
            html.Label("Linha de corte para alarmes (última análise há)"),
            dcc.Input(id='dias-alarmes', type='number', style={"width": "100%"})
        ]),
        html.Div([
            html.Label("Linha de corte para insights (última análise há)"),
            dcc.Input(id='dias-insights', type='number', style={"width": "100%"})
        ]),
        html.Div([
            html.Label("Linha de corte para notas vencidas (nota vencida há)"),
            dcc.Input(id='dias-notas', type='number', style={"width": "100%"})
        ])
    ], style={"display": "flex", "gap": "30px"}),

    html.Hr(),

    dcc.Store(id='df-base'),
    dcc.Store(id='df-final'),

    html.H4("Impacto por analista"),
    dash_table.DataTable(
        id='tabela-analista',
        page_size=5,
        style_table={'width': '40%'}
    ),

    html.Hr(),

    html.H4("Lista final"),
    dash_table.DataTable(
        id='tabela-final',
        filter_action="native",
        sort_action="native",
        page_action="none",
        style_table={
            'height': '500px',
            'overflowY': 'auto'
        }
    ),

    html.Br(),
    html.Button("Download Excel", id="btn-download"),
    dcc.Download(id="download-excel")
])


@app.callback(
    Output('status-upload-base', 'children'),
    Output('status-upload-mosaic', 'children'),
    Output('status-upload-notas', 'children'),
    Output('status-upload-ordem-notas', 'children'),
    Output('status-upload-ordem-planos', 'children'),
    Output('status-upload-insights', 'children'),
    Input('upload-base', 'filename'),
    Input('upload-mosaic', 'filename'),
    Input('upload-notas', 'filename'),
    Input('upload-ordem-notas', 'filename'),
    Input('upload-ordem-planos', 'filename'),
    Input('upload-insights', 'filename'),
)
def mostrar_status(f1, f2, f3, f4, f5, f6):
    def status(f):
        if f:
            return html.Div(f"✔ {f}", style={"color": "green", "fontWeight": "bold"})
        return html.Div("❌ Não enviado", style={"color": "red"})
    return status(f1), status(f2), status(f3), status(f4), status(f5), status(f6)


@app.callback(
    Output('df-base', 'data'),
    Input('upload-base', 'contents'),
    Input('upload-mosaic', 'contents'),
    Input('upload-notas', 'contents'),
    Input('upload-ordem-notas', 'contents'),
    Input('upload-ordem-planos', 'contents'),
    Input('upload-insights', 'contents'),
    State('upload-base', 'filename'),
    State('upload-mosaic', 'filename'),
    State('upload-notas', 'filename'),
    State('upload-ordem-notas', 'filename'),
    State('upload-ordem-planos', 'filename'),
    State('upload-insights', 'filename'),
)
def processar_base(c_base, c_mosaic, c_notas, c_ordem_notas, c_ordem_planos, c_insights,
                   f_base, f_mosaic, f_notas, f_ordem_notas, f_ordem_planos, f_insights):

    if not all([c_base, c_mosaic, c_notas, c_ordem_notas, c_ordem_planos, c_insights]):
        raise PreventUpdate

    base = parse_contents(c_base, f_base)
    mosaic = parse_contents(c_mosaic, f_mosaic)
    notas = parse_contents(c_notas, f_notas)
    ordem_notas = parse_contents(c_ordem_notas, f_ordem_notas)
    ordem_planos = parse_contents(c_ordem_planos, f_ordem_planos)
    insights = parse_contents(c_insights, f_insights)

    notas["ORDEM_NORM"] = notas["Ordem"].astype(str).str.replace(r"\.0$", "", regex=True)
    ordem_notas["Ordem"] = ordem_notas["Ordem"].astype(str)

    mosaic["DATA_ANALISE_FMT"] = pd.to_datetime(
        mosaic["analysisCreatedAt"], errors="coerce"
    ).dt.strftime("%d/%m/%Y")

    base["STATUS DO PONTO DE MONITORAMENTO"] = base["SPOT ID"].map(
        mosaic.groupby("spotId")["status"].apply(concat_values)
    )

    base["DATA DA ÚLTIMA ANÁLISE"] = base["SPOT ID"].map(
        mosaic.groupby("spotId")["DATA_ANALISE_FMT"].apply(concat_values)
    )

    base["INSIGHTS"] = base["MÁQUINA"].isin(insights.iloc[:, 0]).map(lambda x: "SIM" if x else "")

    base["NOTA M4"] = base["SUBCONJUNTO"].map(
        notas.groupby("Local de instalação")["Nota"].apply(concat_values)
    )

    base["ORDEM DA NOTA M4"] = base["SUBCONJUNTO"].map(
        notas.groupby("Local de instalação")["ORDEM_NORM"].apply(concat_values)
    )

    base["DATA DE CONCLUSÃO DESEJADA DA NOTA M4"] = base["SUBCONJUNTO"].map(
        notas.groupby("Local de instalação")["Conclusão desejada"].apply(concat_values)
    )

    base["STATUS DO SISTEMA DA ORDEM"] = (
        base["ORDEM DA NOTA M4"]
        .dropna()
        .str.split(" \| ")
        .explode()
        .to_frame("Ordem")
        .merge(ordem_notas[["Ordem", "Status do sistema"]], on="Ordem", how="left")
        .groupby(level=0)["Status do sistema"]
        .apply(concat_values)
    )

    base["NÚMERO DA ORDEM DO PLANO AV"] = base["MÁQUINA"].map(
        ordem_planos.groupby("Local de instalação")["Ordem"].apply(concat_values)
    )

    base["STATUS DO SISTEMA DA ORDEM DO PLANO AV"] = base["MÁQUINA"].map(
        ordem_planos.groupby("Local de instalação")["Status do sistema"].apply(concat_values)
    )

    base = base.rename(columns={
        "SPOT ID": "SPOTID",
        "SPOT NAME": "SPOTNAME",
        "ANALISTA": "ANALISTA RESPONSÁVEL"
    })

    return base.to_dict("records")


@app.callback(
    Output('tabela-final', 'data'),
    Output('tabela-final', 'columns'),
    Output('tabela-analista', 'data'),
    Output('tabela-analista', 'columns'),
    Output('df-final', 'data'),
    Input('df-base', 'data'),
    Input('dias-alarmes', 'value'),
    Input('dias-insights', 'value'),
    Input('dias-notas', 'value')
)
def aplicar_regras(data, dias_alarm, dias_insight, dias_nota):
    if not data:
        raise PreventUpdate

    df = pd.DataFrame(data)

    cond1 = (
        df["STATUS DO PONTO DE MONITORAMENTO"].str.contains("A1|A2", case=False, na=False)
        & (
            df["DATA DA ÚLTIMA ANÁLISE"].isna()
            | (df["DATA DA ÚLTIMA ANÁLISE"].apply(days_diff) > dias_alarm)
        )
    )

    cond2 = (
        (df["INSIGHTS"] == "SIM")
        & (
            df["DATA DA ÚLTIMA ANÁLISE"].isna()
            | (df["DATA DA ÚLTIMA ANÁLISE"].apply(days_diff) > dias_insight)
        )
    )

    cond3 = (
        df["NOTA M4"].notna()
        & (df["DATA DE CONCLUSÃO DESEJADA DA NOTA M4"].apply(days_diff) > dias_nota)
    )

    cond4 = df["STATUS DO SISTEMA DA ORDEM"].str.contains("LIB CONF|ENT CONF", case=False, na=False)

    df_final = df[cond1 | cond2 | cond3 | cond4]

    df_final = df_final.sort_values(
        by=["ANALISTA RESPONSÁVEL", "MÁQUINA", "SPOTNAME"]
    )

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


@app.callback(
    Output("download-excel", "data"),
    Input("btn-download", "n_clicks"),
    State("df-final", "data"),
    prevent_initial_call=True
)
def download_excel(n, data):
    if not data:
        raise PreventUpdate
    df = pd.DataFrame(data)
    return dcc.send_data_frame(df.to_excel, "LISTA_FINAL_PRIORIZADA.xlsx", index=False)


if __name__ == "__main__":
    app.run_server(debug=True)
