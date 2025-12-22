from pathlib import Path

import pandas as pd
from loguru import logger

from config.settings import load_config
from src.exceptions import ConfigError, DatabaseError, DateFormatError
from src.processing import perform_crossing, prepare_dataframes_for_crossing
from src.utils_db import get_db_connection, get_upc_data


def main():
    """
    Orquesta el proceso de cruce de retroactivos.
    1. Carga la configuración.
    2. Limpia los resultados anteriores.
    3. Carga los datos del archivo Excel.
    4. Obtiene los datos de la base de datos.
    5. Prepara y cruza los datos.
    6. Guarda los resultados.
    """
    # 1. Cargar configuración
    config_path = Path("config/config.yaml")
    config = load_config(config_path)
    proc_config = config["processing"]
    logger.info("Configuración cargada correctamente.")

    # 2. Limpiar resultados anteriores
    output_encontrados = Path(proc_config["output"])
    logger.info("Archivos de resultados anteriores eliminados.")

    # 3. Cargar datos del Excel
    df_retro_excel = pd.read_excel(
        proc_config["excel_path"],
        sheet_name=proc_config["excel_sheet_name"],
        dtype="str",
    )
    df_retro_excel["num factura"] = df_retro_excel["num factura"].str.strip()
    facturas_unicas = df_retro_excel["num factura"].unique().tolist()
    logger.info(f"Cargado el archivo Excel: {df_retro_excel.shape[0]} filas.")

    # 4. Obtener datos de la base de datos
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

    # 5. Preparar y cruzar DataFrames
    df_retro_excel, df_upc = prepare_dataframes_for_crossing(
        df_retro_excel,
        df_upc,
        format_date_excel=proc_config["format_date_excel"],
        format_date_db=proc_config["format_date_db"],
        format_date_crossing=proc_config["format_date_crossing"],
    )
    logger.info("DataFrames preparados para el cruce.")

    df_final = perform_crossing(df_retro_excel, df_upc)
    logger.info(f"Marcacion finalizada {df_final['encontrado_upc'].value_counts()}")

    # 6. Guardar resultados
    df_final.to_csv(output_encontrados, sep="|", index=False)
    logger.info(f"Resultados guardados en '{proc_config['output']}'.")


if __name__ == "__main__":
    try:
        main()
        logger.info("Proceso completado exitosamente.")
    except (DatabaseError, ConfigError, DateFormatError) as e:
        logger.critical(f"El proceso ha fallado debido a un error crítico: {e}")
    except Exception as e:
        logger.exception(f"Ha ocurrido un error inesperado no controlado: {e}")
