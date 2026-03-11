# callbacks.py
# Callbacks da aplicação

import pandas as pd
from dash import dcc, html, Input, Output, State, ALL
from dash.exceptions import PreventUpdate

from helpers import parse_contents, concat_values, days_diff, days_since_last_sync, resolver_status_ordem, clean_insights, gerar_badge_input


def register_callbacks(app):
    """Registra todos os callbacks no objeto Dash."""

    # ======================================================
    # CONTROLE DO MODAL DE UPLOADS
    # ======================================================

    @app.callback(
        Output("modal-uploads", "style"),
        Output("modal-overlay", "style"),
        Input("btn-abrir-uploads", "n_clicks"),
        Input("btn-fechar-modal", "n_clicks"),
        Input("btn-processar-uploads", "n_clicks"),
        prevent_initial_call=True,
    )
    def toggle_modal(n_abrir, n_fechar, n_processar):
        from dash import ctx
        
        # Estilos padrão
        modal_oculto = {"display": "none"}
        modal_visivel = {"display": "block"}
        overlay_oculto = {"display": "none"}
        overlay_visivel = {
            "display": "block",
            "position": "fixed",
            "top": "0",
            "left": "0",
            "width": "100%",
            "height": "100%",
            "backgroundColor": "rgba(0, 0, 0, 0.5)",
            "zIndex": "1000",
        }
        
        # Verificar qual botão foi clicado
        if ctx.triggered_id == "btn-abrir-uploads":
            return modal_visivel, overlay_visivel
        else:  # btn-fechar-modal ou btn-processar-uploads
            return modal_oculto, overlay_oculto

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

        # Mapear analysisStatus e processar para labels legíveis
        def processar_analysis_status(status_str):
            if pd.isna(status_str) or str(status_str).strip() in ["", "-"]:
                return "NUNCA ANALISADO"
            status_lower = str(status_str).lower().strip()
            if status_lower == "a1":
                return "ALERTA"
            elif status_lower == "a2":
                return "INTERVENÇÃO"
            elif status_lower == "no-alert":
                return "NORMAL"
            else:
                return status_str  # Mantém original se não reconhecer
        
        base["STATUS DA ÚLTIMA ANÁLISE"] = base["SPOT ID"].map(
            mosaic.groupby("spotId")["analysisStatus"].apply(concat_values)
        ).apply(processar_analysis_status)

        # Mapear data da última coleta (spotLastSync) e formatar
        def formatar_data_coleta(data_str):
            if pd.isna(data_str) or str(data_str).strip() in ["", "-"]:
                return ""
            try:
                dt = pd.to_datetime(data_str, errors="coerce", utc=True)
                if pd.isna(dt):
                    return ""
                return dt.strftime("%d/%m/%Y %H:%M")
            except:
                return ""
        
        base["DATA DA ÚLTIMA COLETA"] = base["SPOT ID"].map(
            mosaic.groupby("spotId")["spotLastSync"].apply(concat_values)
        ).apply(formatar_data_coleta)

        base["INSIGHTS"] = base["MÁQUINA"].isin(insights_clean).map(
            lambda x: "SIM" if x else "NÃO"
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
        base["STATUS DO SISTEMA DA ORDEM M4"] = resolver_status_ordem(base, ordem_notas)

        base["NÚMERO DA ORDEM DO PLANO AV"] = base["MÁQUINA"].map(
            ordem_planos.groupby("Local de instalação")["Ordem"].apply(concat_values)
        )

        base["STATUS DO SISTEMA DA ORDEM DO PLANO AV"] = base["MÁQUINA"].map(
            ordem_planos.groupby("Local de instalação")["Status do sistema"].apply(concat_values)
        )

        # Criar coluna de link do spot com formato markdown clicável
        from datetime import datetime, timedelta
        hoje = datetime.now()
        data_fim = hoje.strftime("%Y-%m-%dT%H:%M:%S-03:00")
        data_inicio = (hoje - timedelta(days=7)).strftime("%Y-%m-%dT00:00:00-03:00")
        
        base["LINK DO SPOT"] = base["SPOT ID"].apply(
            lambda spot_id: f"[🔗 Abrir](https://dyp.dynamox.solutions/654a51b9314e921d5e082ee3/spot-viewer/{spot_id}/{data_inicio}/{data_fim}?tab=telemetry)"
        )

        # Renomear e reorganizar colunas
        base = base.rename(columns={
            "SPOT NAME": "SPOTNAME",
        })

        # Remover SPOT ID da visualização (mas manter temporariamente para criar link)
        # Reordenar colunas conforme solicitado
        colunas_ordem = [
            "MÁQUINA",
            "SUBCONJUNTO", 
            "SPOTNAME",
            "ANALISTA RESPONSÁVEL",
            "STATUS DO PONTO DE MONITORAMENTO",
            "DATA DA ÚLTIMA ANÁLISE",
            "STATUS DA ÚLTIMA ANÁLISE",
            "INSIGHTS",
            "NOTA M4",
            "ORDEM DA NOTA M4",
            "DATA DE CONCLUSÃO DESEJADA DA NOTA M4",
            "STATUS DO SISTEMA DA ORDEM M4",
            "NÚMERO DA ORDEM DO PLANO AV",
            "STATUS DO SISTEMA DA ORDEM DO PLANO AV",
            "DATA DA ÚLTIMA COLETA",
            "LINK DO SPOT",
        ]
        
        # Reordenar e manter só as colunas necessárias (sem SPOTID_TEMP para exibição)
        base = base[colunas_ordem]

        return base.to_dict("records")

    # ======================================================
    # GERAR FILTROS DINÂMICOS POR ANALISTA
    # ======================================================

    @app.callback(
        Output("filtros-analistas-container", "children"),
        Output("filtros-por-analista", "data"),
        Input("df-base", "data"),
    )
    def gerar_filtros_analistas(data):
        if not data:
            return html.Div("⚠️ Aguardando upload dos arquivos para gerar filtros...", 
                          style={"color": "#666", "fontStyle": "italic", "padding": "10px"}), {}

        df = pd.DataFrame(data)
        
        # Verificar se tem a coluna necessária
        if "ANALISTA RESPONSÁVEL" not in df.columns:
            return html.Div("❌ Erro: Coluna 'ANALISTA RESPONSÁVEL' não encontrada na base", 
                          style={"color": "red", "padding": "10px"}), {}
        
        analistas = sorted(df["ANALISTA RESPONSÁVEL"].dropna().unique())
        
        if len(analistas) == 0:
            return html.Div("⚠️ Nenhum analista encontrado na base", 
                          style={"color": "orange", "padding": "10px"}), {}

        from layout import DEFAULT_DIAS_ALARMES, DEFAULT_DIAS_INSIGHTS, DEFAULT_DIAS_NOTAS

        # Inicializar filtros padrão para todos os analistas
        filtros_default = {
            analista: {
                "alarmes": ["A1", "A2"],
                "dias_alarmes": DEFAULT_DIAS_ALARMES,
                "dias_insights": DEFAULT_DIAS_INSIGHTS,
                "dias_notas": DEFAULT_DIAS_NOTAS,
            }
            for analista in analistas
        }

        # Criar controles para cada analista
        children = []
        for analista in analistas:
            children.append(
                html.Div([
                    # Nome do analista
                    html.Div(
                        f"{analista}:",
                        style={
                            "fontWeight": "bold",
                            "minWidth": "120px",
                            "display": "flex",
                            "alignItems": "center",
                        }
                    ),
                    
                    # Checkboxes A1/A2
                    html.Div([
                        dcc.Checklist(
                            id={"type": "filtro-alarme-analista", "analista": analista},
                            options=[
                                {"label": " A1", "value": "A1"},
                                {"label": " A2", "value": "A2"},
                            ],
                            value=["A1", "A2"],
                            inline=True,
                        ),
                    ], style={"minWidth": "100px"}),
                    
                    # Input dias alarmes
                    html.Div([
                        html.Label("Alarmes:", style={"fontSize": "11px", "marginRight": "5px"}),
                        dcc.Input(
                            id={"type": "dias-alarmes-analista", "analista": analista},
                            type="number",
                            value=DEFAULT_DIAS_ALARMES,
                            min=0,
                            debounce=True,
                            style={"width": "60px"},
                        ),
                    ], style={"display": "flex", "alignItems": "center", "gap": "5px"}),
                    
                    # Input dias insights
                    html.Div([
                        html.Label("Insights:", style={"fontSize": "11px", "marginRight": "5px"}),
                        dcc.Input(
                            id={"type": "dias-insights-analista", "analista": analista},
                            type="number",
                            value=DEFAULT_DIAS_INSIGHTS,
                            min=0,
                            debounce=True,
                            style={"width": "60px"},
                        ),
                    ], style={"display": "flex", "alignItems": "center", "gap": "5px"}),
                    
                    # Input dias notas
                    html.Div([
                        html.Label("Notas:", style={"fontSize": "11px", "marginRight": "5px"}),
                        dcc.Input(
                            id={"type": "dias-notas-analista", "analista": analista},
                            type="number",
                            value=DEFAULT_DIAS_NOTAS,
                            min=0,
                            debounce=True,
                            style={"width": "60px"},
                        ),
                    ], style={"display": "flex", "alignItems": "center", "gap": "5px"}),
                    
                ], style={
                    "display": "flex",
                    "gap": "15px",
                    "marginBottom": "12px",
                    "alignItems": "center",
                    "padding": "10px",
                    "backgroundColor": "white",
                    "borderRadius": "5px",
                    "border": "1px solid #e0e0e0",
                })
            )

        container = html.Div(children, style={
            "border": "2px solid #ddd",
            "padding": "15px",
            "borderRadius": "5px",
            "backgroundColor": "#fafafa",
            "marginBottom": "15px",
        })

        return container, filtros_default

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
        Input("dias-coleta-atualizada", "value"),
        Input({"type": "filtro-alarme-analista", "analista": ALL}, "value"),
        Input({"type": "dias-alarmes-analista", "analista": ALL}, "value"),
        Input({"type": "dias-insights-analista", "analista": ALL}, "value"),
        Input({"type": "dias-notas-analista", "analista": ALL}, "value"),
        State({"type": "filtro-alarme-analista", "analista": ALL}, "id"),
    )
    def aplicar_regras(data,
                       dias_coleta,
                       filtros_alarme_values, 
                       dias_alarmes_values,
                       dias_insights_values,
                       dias_notas_values,
                       filtros_ids):
        # Se não há dados ainda (uploads incompletos), bloqueia normalmente.
        if not data:
            raise PreventUpdate

        df = pd.DataFrame(data)
        
        # Usar valor padrão se dias_coleta for None
        if dias_coleta is None:
            dias_coleta = 7

        # Criar dicionários de configurações por analista
        config_por_analista = {}
        
        from layout import DEFAULT_DIAS_ALARMES, DEFAULT_DIAS_INSIGHTS, DEFAULT_DIAS_NOTAS
        
        if filtros_ids and filtros_alarme_values:
            for i, filtro_id in enumerate(filtros_ids):
                analista = filtro_id["analista"]
                config_por_analista[analista] = {
                    "filtro_alarme": filtros_alarme_values[i] if filtros_alarme_values[i] else [],
                    "dias_alarmes": dias_alarmes_values[i] if dias_alarmes_values[i] is not None else DEFAULT_DIAS_ALARMES,
                    "dias_insights": dias_insights_values[i] if dias_insights_values[i] is not None else DEFAULT_DIAS_INSIGHTS,
                    "dias_notas": dias_notas_values[i] if dias_notas_values[i] is not None else DEFAULT_DIAS_NOTAS,
                }

        dias_col = df["DATA DA ÚLTIMA ANÁLISE"].apply(days_diff)

        # Criar dicionários para armazenar condições por índice
        condicoes_por_index = {idx: {"cond1": False, "cond2": False, "cond3": False, "cond4": False, "dias_alarm": None, "dias_nota": None} 
                               for idx in df.index}

        # Aplicar regras POR ANALISTA
        todas_maquinas_qualificadas = set()
        
        for analista in df["ANALISTA RESPONSÁVEL"].dropna().unique():
            df_analista = df[df["ANALISTA RESPONSÁVEL"] == analista]
            
            # Pegar configurações específicas deste analista
            config = config_por_analista.get(analista, {
                "filtro_alarme": ["A1", "A2"],
                "dias_alarmes": DEFAULT_DIAS_ALARMES,
                "dias_insights": DEFAULT_DIAS_INSIGHTS,
                "dias_notas": DEFAULT_DIAS_NOTAS,
            })
            
            filtro_alarme_analista = config["filtro_alarme"]
            dias_alarm = config["dias_alarmes"]
            dias_insight = config["dias_insights"]
            dias_nota = config["dias_notas"]
            
            # Cond1: alarmes com análise antiga ou ausente (com filtro específico do analista)
            if filtro_alarme_analista:
                padrao_alarme = "|".join(filtro_alarme_analista)
                cond1 = (
                    df_analista["STATUS DO PONTO DE MONITORAMENTO"].str.contains(padrao_alarme, case=False, na=False)
                    & (df_analista.index.map(lambda idx: dias_col[idx]).isna() | (df_analista.index.map(lambda idx: dias_col[idx]) > dias_alarm))
                )
            else:
                cond1 = pd.Series(False, index=df_analista.index)

            # Cond2: insights com análise antiga ou ausente
            cond2 = (
                (df_analista["INSIGHTS"] == "SIM")
                & (df_analista.index.map(lambda idx: dias_col[idx]).isna() | (df_analista.index.map(lambda idx: dias_col[idx]) > dias_insight))
            )

            # Cond3: notas M4 com conclusão vencida
            dias_nota_col = df_analista["DATA DE CONCLUSÃO DESEJADA DA NOTA M4"].apply(days_diff)
            cond3 = (
                df_analista["NOTA M4"].notna()
                & (dias_nota_col.notna())
                & (dias_nota_col > dias_nota)
            )

            # Cond4: ordens com status de confirmação pendente
            cond4 = df_analista["STATUS DO SISTEMA DA ORDEM M4"].str.contains(
                r"\bCONF\b", case=False, na=False, regex=True
            )

            # Armazenar condições para cada índice deste analista
            for idx in df_analista.index:
                condicoes_por_index[idx]["cond1"] = cond1.loc[idx]
                condicoes_por_index[idx]["cond2"] = cond2.loc[idx]
                condicoes_por_index[idx]["cond3"] = cond3.loc[idx]
                condicoes_por_index[idx]["cond4"] = cond4.loc[idx]
                condicoes_por_index[idx]["dias_alarm"] = dias_col.loc[idx]
                condicoes_por_index[idx]["dias_nota"] = dias_nota_col.loc[idx]

            # Identificar máquinas qualificadas deste analista
            pontos_qualificados = cond1 | cond2 | cond3 | cond4
            maquinas_qualificadas = df_analista[pontos_qualificados]["MÁQUINA"].unique()
            todas_maquinas_qualificadas.update(maquinas_qualificadas)
        
        # FILTRO GLOBAL: Remover máquinas onde TODOS os spots têm coleta defasada
        # Calcular dias desde última coleta para cada ponto
        df["DIAS_DESDE_COLETA"] = df["DATA DA ÚLTIMA COLETA"].apply(days_since_last_sync)
        
        # Para cada máquina qualificada, verificar se pelo menos 1 spot tem coleta atualizada
        maquinas_com_coleta_ok = set()
        for maquina in todas_maquinas_qualificadas:
            pontos_maquina = df[df["MÁQUINA"] == maquina]
            dias_coleta_maquina = pontos_maquina["DIAS_DESDE_COLETA"]
            
            # Se pelo menos 1 spot tem coleta atualizada (ou valor None), a máquina passa
            tem_coleta_atualizada = (dias_coleta_maquina.isna()) | (dias_coleta_maquina <= dias_coleta)
            
            if tem_coleta_atualizada.any():
                maquinas_com_coleta_ok.add(maquina)
        
        # Trazer TODOS os pontos das máquinas que passaram no filtro de coleta
        df_final = df[df["MÁQUINA"].isin(maquinas_com_coleta_ok)].sort_values(
            by=["ANALISTA RESPONSÁVEL", "MÁQUINA", "SPOTNAME"]
        )

        # Gerar coluna INPUT com badges para cada ponto
        try:
            df_final["INPUT"] = df_final.apply(
                lambda row: gerar_badge_input(
                    row,
                    condicoes_por_index.get(row.name, {}).get("dias_alarm"),
                    condicoes_por_index.get(row.name, {}).get("dias_nota"),
                    condicoes_por_index.get(row.name, {}).get("cond1", False),
                    condicoes_por_index.get(row.name, {}).get("cond2", False),
                    condicoes_por_index.get(row.name, {}).get("cond3", False),
                    condicoes_por_index.get(row.name, {}).get("cond4", False)
                ),
                axis=1
            )
        except Exception as e:
            # Se falhar, criar coluna vazia para não quebrar
            print(f"Erro ao gerar INPUT: {e}")
            df_final["INPUT"] = "[Erro ao gerar badges]"

        # Remover INSIGHTS e DIAS_DESDE_COLETA antes de exibir
        colunas_remover = ["INSIGHTS", "DIAS_DESDE_COLETA"]
        
        # Definir ordem desejada das colunas
        ordem_desejada = [
            "MÁQUINA",
            "SUBCONJUNTO",
            "SPOTNAME",
            "ANALISTA RESPONSÁVEL",
            "INPUT",
            "LINK DO SPOT",
            "STATUS DO PONTO DE MONITORAMENTO",
            "DATA DA ÚLTIMA ANÁLISE",
            "STATUS DA ÚLTIMA ANÁLISE",
            "NOTA M4",
            "ORDEM DA NOTA M4",
            "DATA DE CONCLUSÃO DESEJADA DA NOTA M4",
            "STATUS DO SISTEMA DA ORDEM M4",
            "NÚMERO DA ORDEM DO PLANO AV",
            "STATUS DO SISTEMA DA ORDEM DO PLANO AV",
            "DATA DA ÚLTIMA COLETA",
        ]
        
        # Pegar apenas as colunas que existem e não devem ser removidas
        colunas_final_ordem = [c for c in ordem_desejada if c in df_final.columns and c not in colunas_remover]
        
        df_final_exibir = df_final[colunas_final_ordem]

        resumo = (
            df_final_exibir
            .groupby("ANALISTA RESPONSÁVEL")
            .size()
            .reset_index(name="QUANTIDADE DE PONTOS")
        )

        cols_final = [
            {"name": c, "id": c, "presentation": "markdown"} if c == "LINK DO SPOT" 
            else {"name": c, "id": c} 
            for c in df_final_exibir.columns
        ]
        cols_resumo = [{"name": c, "id": c} for c in resumo.columns]

        return (
            df_final_exibir.to_dict("records"),
            cols_final,
            resumo.to_dict("records"),
            cols_resumo,
            df_final.to_dict("records"),  # Mantém SPOTID_TEMP no store para possível uso futuro
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
