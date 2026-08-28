from pathlib import Path

from loguru import logger

from config.settings import load_config
from src.exceptions import (
    ConfigError,
    DatabaseError,
    DateFormatError,
    SourceReadError,
)
from src.log_config import setup_logging
from src.processing import (
    load_retro_data,
    perform_crossing,
    prepare_dataframes_for_crossing,
)
from src.utils_db import get_db_connection, get_upc_data


def main() -> None:
    """
    Orquesta el proceso de cruce de retroactivos:
    1. Inicializa el sistema de logs y carga configuración.
    2. Carga y consolida los datos del archivo Excel/XLSB (filtrando hojas excluidas).
    3. Obtiene los datos correspondientes de la base de datos Oracle.
    4. Prepara las llaves compuestas y efectúa el cruce.
    5. Exporta los resultados a CSV delimitados por pipe.
    """
    # 0. Configurar logging
    setup_logging()

    # 1. Cargar configuración
    config_path = Path("src/config/config.yaml")
    config = load_config(config_path)
    proc_config = config["processing"]
    logger.info("Configuración cargada correctamente.")

    # 2. Cargar datos del archivo Excel/XLSB
    excel_path = Path(proc_config["excel_path"])
    df_retro_excel = load_retro_data(
        file_path=excel_path,
        sheet_name=proc_config.get("excel_sheet_name"),
        excluded_sheets=proc_config.get("excluded_sheets"),
        engine=proc_config.get("excel_engine"),
    )

    # Identificar columna de factura y extraer facturas únicas
    factura_col = "num_factura" if "num_factura" in df_retro_excel.columns else "num factura"
    df_retro_excel[factura_col] = df_retro_excel[factura_col].astype(str).str.strip()
    facturas_unicas = [
        f for f in df_retro_excel[factura_col].unique().tolist()
        if f and f not in ("nan", "None", "<NA>")
    ]
    logger.info(
        f"Archivo cargado: {len(df_retro_excel):,} filas. "
        f"Total de facturas únicas: {len(facturas_unicas):,}."
    )

    # 3. Obtener datos de la base de datos Oracle
    base_query = proc_config["base_query"].format(
        prestador_id=proc_config["prestador_id"]
    )
    with get_db_connection() as conn:
        df_upc = get_upc_data(
            conn,
            base_query,
            facturas=facturas_unicas,
            batch_size=proc_config["db_batch_size"],
            chunk_size=proc_config["db_chunk_size"],
        )

    # 4. Preparar y cruzar DataFrames
    df_retro_excel, df_upc = prepare_dataframes_for_crossing(
        df_retro_excel,
        df_upc,
        format_date_excel=proc_config["format_date_excel"],
        format_date_db=proc_config["format_date_db"],
        format_date_crossing=proc_config["format_date_crossing"],
    )
    logger.info("DataFrames preparados para el cruce.")

    df_final = perform_crossing(df_retro_excel, df_upc)
    conteo_marcacion = df_final["encontrado_upc"].value_counts().to_dict()
    logger.info(f"Marcación finalizada: {conteo_marcacion}")

    # 5. Guardar resultados
    output_encontrados = Path(proc_config["output"])
    output_encontrados.parent.mkdir(parents=True, exist_ok=True)
    df_final.to_csv(output_encontrados, sep="|", index=False)
    logger.info(f"Resultados guardados en '{output_encontrados}'.")

    output_upc_path = Path(proc_config.get("output_upc_data", "outputs/upc_data.csv"))
    output_upc_path.parent.mkdir(parents=True, exist_ok=True)
    df_upc.to_csv(output_upc_path, sep="|", index=False)
    logger.info(f"Datos UPC guardados en '{output_upc_path}'.")


if __name__ == "__main__":
    try:
        main()
        logger.info("Proceso completado exitosamente.")
    except (DatabaseError, ConfigError, DateFormatError, SourceReadError) as e:
        logger.critical(f"El proceso ha fallado debido a un error crítico: {e}")
    except Exception as e:
        logger.exception(f"Ha ocurrido un error inesperado no controlado: {e}")

