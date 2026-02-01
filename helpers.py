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
    Aceita DD/MM/YYYY e DD.MM.YYYY automaticamente.
    Datas inválidas ou vazias retornam None.
    """
    if pd.isna(date_str) or str(date_str).strip() == "":
        return None

    # Normaliza ponto para barra antes de parsear
    normalized = str(date_str).strip().replace(".", "/")

    data = pd.to_datetime(normalized, format="%d/%m/%Y", errors="coerce")
    if pd.isna(data):
        return None

    return (datetime.today() - data).days


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
