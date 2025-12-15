"""
Módulo para el procesamiento y transformación de datos para el cruce de retroactivos.
"""

import numpy as np
import pandas as pd

from exceptions import DateFormatError


def prepare_dataframes_for_crossing(
    df_retro_excel: pd.DataFrame,
    df_upc_db: pd.DataFrame,
    format_date_excel: str,
    format_date_db: str,
    format_date_crossing: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Prepara los dos DataFrames para el cruce, convirtiendo fechas y creando llaves.

    Args:
        df_retro_excel: DataFrame del archivo de retroactividad de la clínica.
        df_upc_db: DataFrame de la base de datos (tbl_suf_process).

    Returns:
        Una tupla con los dos DataFrames procesados.
    """
    # Implementación de la preparación del DataFrame de Excel
    try:
        df_retro_excel["fec cargo"] = pd.to_datetime(
            df_retro_excel["fec cargo"].str.slice(0, 10),
            format=format_date_excel,
            errors="raise",  # Coerce errors to NaT
        ).dt.strftime(format_date_crossing)
    except ValueError as e:
        raise DateFormatError(
            "Error al convertir la fecha en el DataFrame de Excel"
        ) from e

    df_retro_excel["llave_retroactivo"] = (
        df_retro_excel["num factura"].str.strip().fillna("")
        + df_retro_excel["tip doc"].str.strip().fillna("")
        + df_retro_excel["num doc"].str.strip().fillna("")
        + df_retro_excel["Codigo Cups"].str.strip().fillna("")
        + df_retro_excel["fec cargo"].str.strip().fillna("")
    )

    # Implementación de la preparación del DataFrame de la BD
    try:
        df_upc_db["f_prestacion"] = pd.to_datetime(
            df_upc_db["f_prestacion"], format=format_date_db, errors="raise"
        ).dt.strftime(format_date_crossing)
    except ValueError as e:
        raise DateFormatError(
            "Error al convertir la fecha en el DataFrame de la BD"
        ) from e

    df_upc_db["llave_upc"] = (
        df_upc_db["no_factura"].str.strip().fillna("")
        + df_upc_db["tipo_id"].str.strip().fillna("")
        + df_upc_db["no_id"].str.strip().fillna("")
        + df_upc_db["cups"].str.strip().fillna("")
        + df_upc_db["f_prestacion"].str.strip().fillna("")
    )

    return df_retro_excel, df_upc_db


def perform_crossing(
    df_retro_excel: pd.DataFrame, df_upc_db: pd.DataFrame
) -> pd.DataFrame:
    """
    Realiza el cruce entre los dos DataFrames usando las llaves precalculadas.

    Args:
        df_retro_excel: DataFrame del excel con su 'llave_retroactivo'.
        df_upc_db: DataFrame de la BD con su 'llave_upc'.

    Returns:
        Una tupla con (df_encontrados, df_no_encontrados).
    """
    condicion = df_retro_excel["llave_retroactivo"].isin(df_upc_db["llave_upc"])

    df_retro_excel["encontrado_upc"] = np.where(condicion, "SI", "NO")

    return df_retro_excel
