"""
Módulo para el procesamiento y transformación de datos para el cruce de retroactivos.
"""

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from loguru import logger
from unidecode import unidecode

from src.exceptions import DateFormatError, SourceReadError


def load_retro_data(
    file_path: Path | str,
    sheet_name: str | list[str] | None = None,
    excluded_sheets: list[str] | None = None,
    engine: str | None = None,
) -> pd.DataFrame:
    """
    Carga el archivo Excel/XLSB de retroactividad.
    Si sheet_name es None o 'ALL', lee todas las hojas excepto las especificadas en excluded_sheets.

    Args:
        file_path: Ruta al archivo Excel/XLSB.
        sheet_name: Nombre específico de hoja, lista de hojas, o None/'ALL' para leer todas.
        excluded_sheets: Lista de nombres de hojas a excluir al leer todas las hojas.
        engine: Motor de lectura (ej: 'calamine', 'pyxlsb', 'openpyxl'). Si es None y el archivo
                es .xlsb, usa 'calamine' por defecto.

    Returns:
        pd.DataFrame con los datos consolidados en formato string.
    """
    path = Path(file_path)
    if not path.is_file():
        raise SourceReadError(f"El archivo no existe: {path}")

    # Determinar motor de lectura si no fue especificado
    if engine is None and path.suffix.lower() == ".xlsb":
        engine = "calamine"

    # Si se especificó una hoja concreta que no sea 'ALL' o vacía
    if sheet_name and isinstance(sheet_name, str) and sheet_name.strip().upper() != "ALL":
        logger.info(f"Cargando hoja única '{sheet_name}' desde {path.name}...")
        try:
            return pd.read_excel(path, sheet_name=sheet_name, dtype=str, engine=engine)
        except Exception as e:
            raise SourceReadError(f"Error al leer hoja '{sheet_name}' en {path}: {e}") from e

    # Modo lectura de múltiples hojas
    logger.info(f"Inspeccionando hojas del archivo {path.name} usando motor '{engine}'...")
    try:
        excel_file = pd.ExcelFile(path, engine=engine)
        all_sheet_names = excel_file.sheet_names
    except Exception as e:
        raise SourceReadError(f"Error al abrir el archivo Excel {path}: {e}") from e

    # Normalizar lista de exclusiones para comparación insensible a mayúsculas/acentos
    excluded_normalized = []
    if excluded_sheets:
        excluded_normalized = [unidecode(str(s).lower().strip()) for s in excluded_sheets]

    sheets_to_read = []
    for sheet in all_sheet_names:
        sheet_norm = unidecode(sheet.lower().strip())
        is_excluded = sheet_norm in excluded_normalized or any(
            exc in sheet_norm for exc in ["resumen", "salas", "materiales"] if excluded_sheets
        )
        if is_excluded:
            logger.info(f"Omitiendo hoja excluida: '{sheet}'")
        else:
            sheets_to_read.append(sheet)

    if not sheets_to_read:
        raise SourceReadError(f"No se encontraron hojas para procesar en el archivo {path}.")

    logger.info(f"Hojas a procesar ({len(sheets_to_read)}): {sheets_to_read}")

    dataframes = []
    for s in sheets_to_read:
        try:
            df_sheet = pd.read_excel(excel_file, sheet_name=s, dtype=str)
            df_sheet["hoja_origen"] = s
            logger.info(f"Hoja '{s}' cargada con éxito: {len(df_sheet):,} filas.")
            dataframes.append(df_sheet)
        except Exception as e:
            logger.error(f"Error al procesar la hoja '{s}': {e}")
            raise SourceReadError(f"Fallo al leer la hoja '{s}' en {path}: {e}") from e

    df_consolidated = pd.concat(dataframes, ignore_index=True)
    logger.info(f"Total de registros consolidados: {len(df_consolidated):,} filas.")
    return df_consolidated


def normalize_retro_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Estandariza los nombres de las columnas clave del archivo de retroactivos.
    """
    column_mapping = {
        "num factura": "num_factura",
        "tip doc": "tip_doc",
        "num doc": "num_doc",
        "Codigo Cups": "cod_insumo_servicio",
        "codigo cups": "cod_insumo_servicio",
        "cups": "cod_insumo_servicio",
        "fec cargo": "fec_cargo",
    }
    return df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})


def prepare_dataframes_for_crossing(
    df_retro_excel: pd.DataFrame,
    df_upc_db: pd.DataFrame,
    format_date_excel: str,
    format_date_db: str,
    format_date_crossing: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Prepara los dos DataFrames para el cruce, convirtiendo fechas y creando llaves compuestas.

    Args:
        df_retro_excel: DataFrame del archivo de retroactividad de la clínica.
        df_upc_db: DataFrame de la base de datos (tbl_suf_process).
        format_date_excel: Formato original de fecha en el Excel.
        format_date_db: Formato original de fecha en la BD.
        format_date_crossing: Formato de fecha estandarizado para la llave de cruce.

    Returns:
        Una tupla con los dos DataFrames procesados.
    """
    df_retro_excel = normalize_retro_columns(df_retro_excel)

    # Validar presencia de columnas obligatorias en df_retro_excel
    required_cols_excel = ["num_factura", "tip_doc", "num_doc", "cod_insumo_servicio", "fec_cargo"]
    missing_cols = [c for c in required_cols_excel if c not in df_retro_excel.columns]
    if missing_cols:
        raise DateFormatError(f"Faltan columnas requeridas en el archivo de retroactivos: {missing_cols}")

    # Manejo de fechas en df_retro_excel
    df_retro_excel["fec_cargo_norm"] = ""
    mask_excel = (
        df_retro_excel["fec_cargo"].notna()
        & ~df_retro_excel["fec_cargo"].isin(["nan", "NaT", "<NA>", "None", ""])
    )
    if mask_excel.any():
        try:
            dates_series = df_retro_excel.loc[mask_excel, "fec_cargo"].astype(str).str.slice(0, 10)
            df_retro_excel.loc[mask_excel, "fec_cargo_norm"] = pd.to_datetime(
                dates_series,
                format=format_date_excel,
                errors="raise",
            ).dt.strftime(format_date_crossing)
        except ValueError as e:
            raise DateFormatError("Error al convertir la fecha en el DataFrame de Excel") from e

    # Estandarizar valores nulos para la llave
    df_retro_excel["fec_cargo"] = df_retro_excel["fec_cargo_norm"]
    df_retro_excel["fec cargo"] = df_retro_excel["fec_cargo_norm"]
    num_factura = df_retro_excel["num_factura"].fillna("").astype(str).replace("nan", "").str.strip()
    tip_doc = df_retro_excel["tip_doc"].fillna("").astype(str).replace("nan", "").str.strip()
    num_doc = df_retro_excel["num_doc"].fillna("").astype(str).replace("nan", "").str.strip()
    cod_insumo = df_retro_excel["cod_insumo_servicio"].fillna("").astype(str).replace("nan", "").str.strip()
    fec_cargo = df_retro_excel["fec_cargo_norm"].fillna("").astype(str).str.strip()

    df_retro_excel["llave_retroactivo"] = num_factura + tip_doc + num_doc + cod_insumo + fec_cargo

    if not df_upc_db.empty:
        df_upc_db["f_prestacion_norm"] = ""
        mask_upc = (
            df_upc_db["f_prestacion"].notna()
            & ~df_upc_db["f_prestacion"].isin(["nan", "NaT", "<NA>", "None", ""])
        )
        if mask_upc.any():
            try:
                dates_series_upc = df_upc_db.loc[mask_upc, "f_prestacion"].astype(str).str.slice(0, 10)
                df_upc_db.loc[mask_upc, "f_prestacion_norm"] = pd.to_datetime(
                    dates_series_upc,
                    format=format_date_db,
                    errors="raise",
                ).dt.strftime(format_date_crossing)
            except ValueError as e:
                raise DateFormatError("Error al convertir la fecha en el DataFrame de la BD") from e

        df_upc_db["f_prestacion"] = df_upc_db["f_prestacion_norm"]
        no_factura = df_upc_db["no_factura"].fillna("").astype(str).replace("nan", "").str.strip()
        tipo_id = df_upc_db["tipo_id"].fillna("").astype(str).replace("nan", "").str.strip()
        no_id = df_upc_db["no_id"].fillna("").astype(str).replace("nan", "").str.strip()
        cups = df_upc_db["cups"].fillna("").astype(str).replace("nan", "").str.strip()
        f_prestacion = df_upc_db["f_prestacion_norm"].fillna("").astype(str).str.strip()

        df_upc_db["llave_upc"] = no_factura + tipo_id + no_id + cups + f_prestacion
    else:
        df_upc_db["llave_upc"] = pd.Series(dtype="str")

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
        DataFrame con la columna 'encontrado_upc' marcada como 'SI' o 'NO'.
    """
    if "llave_upc" in df_upc_db.columns and not df_upc_db.empty:
        condicion = df_retro_excel["llave_retroactivo"].isin(df_upc_db["llave_upc"])
        df_retro_excel["encontrado_upc"] = np.where(condicion, "SI", "NO")
    else:
        df_retro_excel["encontrado_upc"] = "NO"

    return df_retro_excel
