# callbacks.py
# Callbacks da aplicação

import pandas as pd
from dash import dcc, html, Input, Output, State
from dash.exceptions import PreventUpdate

from helpers import parse_contents, concat_values, days_diff, resolver_status_ordem, clean_insights


def register_callbacks(app):
    """Registra todos os callbacks no objeto Dash."""

    # ======================================================
    # STATUS VISUAL DOS UPLOADS
    # ======================================================

    @app.callback(
        Output("status-upload-base", "children"),
        Output("status-upload-mosaic", "children"),
        Output("status-upload-notas", "children"),
        Output("status-upload-ordem-notas", "children"),
        Output("status-upload-ordem-planos", "children"),
        Output("status-upload-insights", "children"),
        Input("upload-base", "filename"),
        Input("upload-mosaic", "filename"),
        Input("upload-notas", "filename"),
        Input("upload-ordem-notas", "filename"),
        Input("upload-ordem-planos", "filename"),
        Input("upload-insights", "filename"),
    )
    def mostrar_status(f1, f2, f3, f4, f5, f6):
        def status(f):
            if f:
                return html.Div(f"✔ {f}", style={"color": "green", "fontWeight": "bold"})
            return html.Div("❌ Não enviado", style={"color": "red"})

        return status(f1), status(f2), status(f3), status(f4), status(f5), status(f6)

    # ======================================================
    # PROCESSAMENTO BASE
    # ======================================================

    @app.callback(
        Output("df-base", "data"),
        Input("upload-base", "contents"),
        Input("upload-mosaic", "contents"),
        Input("upload-notas", "contents"),
        Input("upload-ordem-notas", "contents"),
        Input("upload-ordem-planos", "contents"),
        Input("upload-insights", "contents"),
        State("upload-base", "filename"),
        State("upload-mosaic", "filename"),
        State("upload-notas", "filename"),
        State("upload-ordem-notas", "filename"),
        State("upload-ordem-planos", "filename"),
        State("upload-insights", "filename"),
    )
    def processar_base(
        c_base, c_mosaic, c_notas, c_ordem_notas, c_ordem_planos, c_insights,
        f_base, f_mosaic, f_notas, f_ordem_notas, f_ordem_planos, f_insights,
    ):
        if not all([c_base, c_mosaic, c_notas, c_ordem_notas, c_ordem_planos, c_insights]):
            raise PreventUpdate

        base = parse_contents(c_base, f_base)
        mosaic = parse_contents(c_mosaic, f_mosaic)
        notas = parse_contents(c_notas, f_notas)
        ordem_notas = parse_contents(c_ordem_notas, f_ordem_notas)
        ordem_planos = parse_contents(c_ordem_planos, f_ordem_planos)
        insights = parse_contents(c_insights, f_insights)

        # --- normalização ---
        notas["ORDEM_NORM"] = (
            notas["Ordem"].astype(str).str.replace(r"\.0$", "", regex=True)
        )
        ordem_notas["Ordem"] = ordem_notas["Ordem"].astype(str)

        mosaic["DATA_ANALISE_FMT"] = pd.to_datetime(
            mosaic["analysisCreatedAt"], errors="coerce"
        ).dt.strftime("%d/%m/%Y")

        # Limpa insights removendo lixo 'See more (N)'
        insights_clean = clean_insights(insights)

        # --- mapeamentos ---
        base["STATUS DO PONTO DE MONITORAMENTO"] = base["SPOT ID"].map(
            mosaic.groupby("spotId")["status"].apply(concat_values)
        )

        base["DATA DA ÚLTIMA ANÁLISE"] = base["SPOT ID"].map(
            mosaic.groupby("spotId")["DATA_ANALISE_FMT"].apply(concat_values)
        )

        base["INSIGHTS"] = base["MÁQUINA"].isin(insights_clean).map(
            lambda x: "SIM" if x else ""
        )

        base["NOTA M4"] = base["SUBCONJUNTO"].map(
            notas.groupby("Local de instalação")["Nota"].apply(concat_values)
        )

        base["ORDEM DA NOTA M4"] = base["SUBCONJUNTO"].map(
            notas.groupby("Local de instalação")["ORDEM_NORM"].apply(concat_values)
        )

        base["DATA DE CONCLUSÃO DESEJADA DA NOTA M4"] = base["SUBCONJUNTO"].map(
            notas.groupby("Local de instalação")["Conclusão desejada"].apply(concat_values)
        )

        # --- status da ordem: usa função dedicada com reindex seguro ---
        base["STATUS DO SISTEMA DA ORDEM"] = resolver_status_ordem(base, ordem_notas)

        base["NÚMERO DA ORDEM DO PLANO AV"] = base["MÁQUINA"].map(
            ordem_planos.groupby("Local de instalação")["Ordem"].apply(concat_values)
        )

        base["STATUS DO SISTEMA DA ORDEM DO PLANO AV"] = base["MÁQUINA"].map(
            ordem_planos.groupby("Local de instalação")["Status do sistema"].apply(concat_values)
        )

        base = base.rename(columns={
            "SPOT ID": "SPOTID",
            "SPOT NAME": "SPOTNAME",
        })

        return base.to_dict("records")

    # ======================================================
    # APLICAÇÃO DAS REGRAS
    # ======================================================

    @app.callback(
        Output("tabela-final", "data"),
        Output("tabela-final", "columns"),
        Output("tabela-analista", "data"),
        Output("tabela-analista", "columns"),
        Output("df-final", "data"),
        Input("df-base", "data"),
        Input("dias-alarmes", "value"),
        Input("dias-insights", "value"),
        Input("dias-notas", "value"),
    )
    def aplicar_regras(data, dias_alarm, dias_insight, dias_nota):
        # Se não há dados ainda (uploads incompletos), bloqueia normalmente.
        if not data:
            raise PreventUpdate

        # Se algum parâmetro é None (campo apagado durante digitação),
        # retorna tabelas vazias em vez de PreventUpdate.
        # Isso evita que o callback fique "travado" e não re-execute
        # quando o valor volta a ser preenchido.
        if any(v is None for v in [dias_alarm, dias_insight, dias_nota]):
            return [], [], [], [], []

        df = pd.DataFrame(data)

        dias_col = df["DATA DA ÚLTIMA ANÁLISE"].apply(days_diff)

        # Cond1: alarmes A1/A2 com análise antiga ou ausente
        cond1 = (
            df["STATUS DO PONTO DE MONITORAMENTO"].str.contains("A1|A2", case=False, na=False)
            & (dias_col.isna() | (dias_col > dias_alarm))
        )

        # Cond2: insights com análise antiga ou ausente
        cond2 = (
            (df["INSIGHTS"] == "SIM")
            & (dias_col.isna() | (dias_col > dias_insight))
        )

        # Cond3: notas M4 com conclusão vencida
        dias_nota_col = df["DATA DE CONCLUSÃO DESEJADA DA NOTA M4"].apply(days_diff)
        cond3 = (
            df["NOTA M4"].notna()
            & (dias_nota_col.notna())
            & (dias_nota_col > dias_nota)
        )

        # Cond4: ordens com status de confirmação pendente.
        # Os status do SAP têm o padrão "LIB  CONF ...", "ENTE CONF ...", "ENCE CONF ...".
        # Busca por 'CONF' como palavra inteira para cobrir todas as variantes.
        cond4 = df["STATUS DO SISTEMA DA ORDEM"].str.contains(
            r"\bCONF\b", case=False, na=False, regex=True
        )

        df_final = df[cond1 | cond2 | cond3 | cond4].sort_values(
            by=["ANALISTA RESPONSÁVEL", "MÁQUINA", "SPOTNAME"]
        )

        resumo = (
            df_final
            .groupby("ANALISTA RESPONSÁVEL")
            .size()
            .reset_index(name="QUANTIDADE DE PONTOS")
        )

        cols_final = [{"name": c, "id": c} for c in df_final.columns]
        cols_resumo = [{"name": c, "id": c} for c in resumo.columns]

        return (
            df_final.to_dict("records"),
            cols_final,
            resumo.to_dict("records"),
            cols_resumo,
            df_final.to_dict("records"),
        )

    # ======================================================
    # DOWNLOAD
    # ======================================================

    @app.callback(
        Output("download-excel", "data"),
        Input("btn-download", "n_clicks"),
        State("df-final", "data"),
        prevent_initial_call=True,
    )
    def download_excel(n, data):
        if not data:
            raise PreventUpdate

        df = pd.DataFrame(data)
        return dcc.send_data_frame(df.to_excel, "LISTA_FINAL_PRIORIZADA.xlsx", index=False)
