# helpers.py
# Funções auxiliares compartilhadas

import base64
import io
from datetime import datetime

import pandas as pd


def parse_contents(contents: str, filename: str) -> pd.DataFrame:
    """Decodifica o conteúdo base64 de um upload e retorna um DataFrame."""
    _content_type, content_string = contents.split(",")
    decoded = base64.b64decode(content_string)

    if filename.endswith(".csv"):
        return pd.read_csv(io.StringIO(decoded.decode("utf-8")))
    return pd.read_excel(io.BytesIO(decoded))


def concat_values(series: pd.Series) -> str:
    """Concatena valores únicos não-nulos de uma Series com ' | '."""
    vals = series.dropna().astype(str).unique()
    return " | ".join(vals) if len(vals) > 0 else ""


def days_diff(date_str) -> "int | None":
    """
    Calcula diferença em dias entre hoje e uma data.
    Aceita DD/MM/YYYY, DD.MM.YYYY, YYYY-MM-DD ou Timestamp do pandas.
    Datas inválidas ou vazias retornam None.
    """
    if pd.isna(date_str) or str(date_str).strip() == "":
        return None

    # Se já é Timestamp do pandas, usar diretamente
    if isinstance(date_str, pd.Timestamp):
        return (datetime.today() - date_str.to_pydatetime().replace(tzinfo=None)).days

    date_str_clean = str(date_str).strip()
    
    # Tentar formato ISO primeiro (mais comum vindo do concat_values)
    if "-" in date_str_clean and len(date_str_clean) == 10:  # YYYY-MM-DD
        data = pd.to_datetime(date_str_clean, format="%Y-%m-%d", errors="coerce")
    # Tentar DD/MM/YYYY ou DD.MM.YYYY
    elif "/" in date_str_clean or "." in date_str_clean:
        normalized = date_str_clean.replace(".", "/")
        data = pd.to_datetime(normalized, format="%d/%m/%Y", errors="coerce")
    else:
        # Fallback genérico
        data = pd.to_datetime(date_str_clean, errors="coerce")
    
    if pd.isna(data):
        return None

    return (datetime.today() - data.to_pydatetime().replace(tzinfo=None)).days


def days_since_last_sync(datetime_str) -> "int | None":
    """
    Calcula diferença em dias entre hoje e um timestamp ISO.
    Aceita formatos como '2024-01-15T10:30:00.000Z' do spotLastSync.
    Valores inválidos, vazios ou "-" retornam None.
    """
    if pd.isna(datetime_str) or str(datetime_str).strip() in ["", "-"]:
        return None
    
    data = pd.to_datetime(datetime_str, errors="coerce", utc=True)
    if pd.isna(data):
        return None
    
    # Converter para timezone-aware para comparação
    hoje = pd.Timestamp.now(tz='UTC')
    return (hoje - data).days


def clean_insights(df: pd.DataFrame) -> pd.Series:
    """
    Retorna a coluna de insights limpa: remove linhas do tipo
    'See more (N)' que vêm como lixo da exportação.
    """
    col = df.iloc[:, 0].astype(str).str.strip()
    mask = ~col.str.contains(r"See\s*more", case=False, regex=True)
    return col[mask].reset_index(drop=True)


def resolver_status_ordem(base: pd.DataFrame, ordem_notas: pd.DataFrame) -> pd.Series:
    """
    Exploda a coluna 'ORDEM DA NOTA M4' (valores separados por ' | '),
    cruza com ordem_notas para obter o 'Status do sistema' e reagrupa
    pelo índice original da base.

    Usa reindex no final para garantir que todas as linhas da base
    estejam presentes no resultado, preenchendo com NaN onde não há
    match — evitando desalinhamento silencioso.
    """
    series = base["ORDEM DA NOTA M4"]

    # Apenas linhas que têm valor
    mask = series.notna() & (series.str.strip() != "")
    if not mask.any():
        return pd.Series("", index=base.index)

    exploded = (
        series[mask]
        .str.split(" | ")
        .explode()
        .str.strip()
        .to_frame("Ordem")
    )
    
    # Verificar se a coluna existe
    if "Status do sistema" not in ordem_notas.columns:
        print(f"ERRO: Coluna 'Status do sistema' não encontrada. Colunas disponíveis: {list(ordem_notas.columns)}")
        return pd.Series("", index=base.index)

    merged = exploded.merge(
        ordem_notas[["Ordem", "Status do sistema"]],
        on="Ordem",
        how="left",
    )

    resultado = (
        merged.groupby(level=0)["Status do sistema"]
        .apply(concat_values)
        .reindex(base.index, fill_value="")  # garante alinhamento com a base
    )

    return resultado


def gerar_badge_input(row, dias_col_val, dias_nota_val, cond1, cond2, cond3, cond4):
    """
    Gera badges para a coluna INPUT baseado nas regras que o ponto passou.
    Retorna string formatada com badges estilo [emoji texto].
    """
    badges = []
    
    # Cond1: Alarme A2 ou A1
    if cond1:
        status = str(row.get("STATUS DO PONTO DE MONITORAMENTO", "")).lower()
        dias = dias_col_val
        
        if "a2" in status:
            if pd.isna(dias):
                badges.append("[🔴 A2 - nunca analisado]")
            else:
                badges.append(f"[🔴 A2 há {int(dias)} dias sem análise]")
        elif "a1" in status:
            if pd.isna(dias):
                badges.append("[🟡 A1 - nunca analisado]")
            else:
                badges.append(f"[🟡 A1 há {int(dias)} dias sem análise]")
    
    # Cond2: Insights
    if cond2:
        badges.append("[💡 Insights]")
    
    # Cond3: Nota M4 vencida
    if cond3:
        dias_nota = dias_nota_val
        if not pd.isna(dias_nota):
            badges.append(f"[📝 Nota M4 vencida há {int(dias_nota)} dias]")
        else:
            badges.append("[📝 Nota M4 vencida]")
    
    # Cond4: Ordem M4 executada
    if cond4:
        badges.append("[✅ Ordem M4 executada]")
    
    # Se não passou em nenhuma regra, é ponto da mesma máquina
    if not badges:
        badges.append("[ℹ️ Mesma máquina]")
    
    return " ".join(badges)
