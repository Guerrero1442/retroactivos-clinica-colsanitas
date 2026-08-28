# Retroactivos Clínica Colsanitas

Automatización y orquestación para el cruce, validación y conciliación de facturas por concepto de **Retroactivos** entre los registros suministrados en archivos Excel y los datos de suficiencia UPC almacenados en la base de datos Oracle (`tbl_suf_process_2026`).

---

## 📋 Tabla de Contenido
- [Descripción General](#-descripción-general)
- [Funcionalidades Principales](#-funcionalidades-principales)
- [Arquitectura del Proyecto](#-arquitectura-del-proyecto)
- [Requisitos Previos](#-requisitos-previos)
- [Instalación y Configuración](#-instalación-y-configuración)
  - [1. Clonar el repositorio y sincronizar dependencias](#1-clonar-el-repositorio-y-sincronizar-dependencias)
  - [2. Configurar variables de entorno (.env)](#2-configurar-variables-de-entorno-env)
  - [3. Ajustar configuración de negocio (config.yaml)](#3-ajustar-configuración-de-negocio-configyaml)
- [Ejecución](#-ejecución)
- [Pruebas Automatizadas](#-pruebas-automatizadas)
- [Manejo de Errores y Logs](#-manejo-de-errores-y-logs)

---

## 🔍 Descripción General

El proceso se encarga de:
1. Extraer los números de factura únicos desde un archivo Excel o XLSB de retroactividad (soporta lectura de múltiples hojas en paralelo excluyendo hojas resumen o no relevantes como `Retroactivo resumen 2026` y `Códigos Salas y Materiales`).
2. Consultar de forma eficiente y paginada (por lotes y chunks) los registros correspondientes en la base de datos Oracle (`tbl_suf_process_2026`).
3. Homogeneizar formatos de fechas y construir llaves de cruce compuestas.
4. Validar la existencia de cada registro en la base de datos UPC (`SI` / `NO`).
5. Exportar el resultado consolidado a archivos CSV delimitados por pipe (`|`).

---

## ⚡ Funcionalidades Principales

* **Carga Multi-Hoja de Alta Velocidad (.xlsb y .xlsx)**: Utiliza `python-calamine` (Rust) y `pyxlsb` para procesar archivos binarios pesados (más de 1.2M de registros) en segundos, consolidando automáticamente las hojas relevantes y descartando las hojas de resumen y catálogos configuradas.
* **Extracción Inteligente de Facturas**: Limpia espacios y extrae las facturas únicas para optimizar las consultas a la base de datos Oracle.
* **Consulta Paginada a Base de Datos (Oracle)**: 
  * Construcción dinámica de consultas con cláusula `IN` dividida en lotes (`db_batch_size`) para evitar límites de Oracle.
  * Extracción en bloques de memoria controlados (`db_chunk_size` con `fetch_data_in_chunks`).
* **Generación de Llaves de Cruce Compuestas**:
  * **Llave Excel**: `num_factura` + `tip_doc` + `num_doc` + `cod_insumo_servicio` + `fec_cargo` (formateada a `dd/mm/yyyy`).
  * **Llave BD UPC**: `no_factura` + `tipo_id` + `no_id` + `cups` + `f_prestacion` (formateada a `dd/mm/yyyy`).
* **Marcación de Conciliación**: Genera la columna `encontrado_upc` indicando con `SI` o `NO` si el servicio reportado en el Excel coincide con los registros de la base de datos.
* **Salida de Datos**: Exporta el DataFrame cruzado y el consolidado de datos UPC a archivos CSV delimitados por pipe (`|`).
* **Logging Estructurado y Rotación**: Registro detallado con `loguru` en consola y archivo local con rotación automática (`10 MB`) y retención de logs (`7 días`).

---

## 🏗️ Arquitectura del Proyecto

```text
retroactivos-clinica-colsanitas/
├── config/
│   └── settings.py          # Validación de variables de entorno con Pydantic Settings
├── inputs/                  # Archivos de entrada (.xlsb / .xlsx)
├── logs/                    # Logs de ejecución generados por Loguru
├── outputs/                 # Archivos CSV generados con los resultados del cruce
├── src/
│   ├── config/
│   │   ├── config.yaml      # Parámetros de negocio, queries y rutas
│   │   └── settings.py      # Mapeo y carga de configuración
│   ├── exceptions.py        # Jerarquía de excepciones personalizadas
│   ├── log_config.py        # Configuración del logger
│   ├── processing.py        # Carga multiseheet, limpieza, fechas, llaves y cruce
│   └── utils_db.py          # Conexión Oracle (SQLAlchemy + oracledb) y consultas por chunks
├── tests/                   # Pruebas unitarias con Pytest
│   ├── test_config.py
│   ├── test_processing.py
│   └── test_utils_db.py
├── .env.example             # Plantilla de variables de entorno
├── main.py                  # Script principal y orquestador del proceso
├── pyproject.toml           # Dependencias y configuración del proyecto
└── README.md                # Documentación del proyecto
```

---

## 📦 Requisitos Previos

* **Python:** `>= 3.14` (o Python `3.10+`)
* **Gestor de paquetes:** [`uv`](https://github.com/astral-sh/uv) (recomendado) o `pip`
* Acceso de red a la base de datos Oracle correspondiente.

---

## 🚀 Instalación y Configuración

### 1. Clonar el repositorio y sincronizar dependencias

Con `uv` instalado, ejecuta en la raíz del proyecto:

```bash
# Sincronizar el entorno virtual con todas las dependencias (incluyendo python-calamine y pyxlsb)
uv sync

# Instalar el proyecto en modo editable (Src Layout)
uv pip install -e .
```

### 2. Configurar variables de entorno (`.env`)

Copia el archivo de ejemplo `.env.example` y crea tu archivo `.env` en la raíz del proyecto:

```bash
cp .env.example .env
```

Edita `.env` con las credenciales correspondientes a la base de datos Oracle:

```env
DB_HOST=10.x.x.x
DB_PORT=1521
DB_SERVICE_NAME=NOMBRE_SERVICIO
DB_USER=usuario_bd
DB_PASSWORD=password_bd
```

### 3. Ajustar configuración de negocio (`config.yaml`)

El archivo [`src/config/config.yaml`](file:///d:/Keralty%20scripts/automatizaciones_python/retroactivos-clinica-colsanitas/src/config/config.yaml) parametriza la entrada y el procesamiento:

```yaml
processing:
  excel_path: "inputs/Retroactivo tarifas evento 2026 EPS Clinica Colsanitas.xlsb"
  excel_sheet_name: null  # null o 'ALL' para procesar todas las hojas válidas
  excluded_sheets:
    - "Retroactivo resumen 2026"
    - "Códigos Salas y Materiales"
    - "Codigos Salas y Materiales"
  excel_engine: "calamine"
  output: "outputs/retroactivos_clinica_colsanitas.csv"
  output_upc_data: "outputs/upc_data.csv"
  prestador_id: "800149384"
  base_query: |
    SELECT *
    FROM tbl_suf_process_2026
    WHERE procesado = '0'
    AND prestador = '{prestador_id}'
  db_batch_size: 900
  db_chunk_size: 10000
  format_date_excel: "%Y-%m-%d"
  format_date_db: "%Y-%m-%d"
  format_date_crossing: "%d/%m/%Y"

logging:
  log_path: "logs"
  log_level_console: "INFO"
  log_level_file: "INFO"
  log_rotation: "10 MB"
  log_retention: "7 days"
  log_compression: "zip"
  log_serialize: false
```

---

## ▶️ Ejecución

Asegúrate de colocar el archivo Excel de entrada en la ruta definida (por ejemplo en `inputs/`). Luego, ejecuta el orquestador principal:

```bash
uv run python main.py
```

Al finalizar la ejecución:
- Los resultados del cruce se guardarán en `outputs/retroactivos_clinica_colsanitas.csv`.
- Se generará un registro completo de eventos en la consola y en la carpeta `logs/`.

---

## 🧪 Pruebas Automatizadas

El proyecto incluye tests unitarios para verificar la carga de configuración, la lógica de cruce y la interacción con la base de datos. Para ejecutarlos:

```bash
uv run pytest
```

---

## 🛡️ Manejo de Errores y Logs

El proyecto implementa una jerarquía de excepciones personalizadas en [`src/exceptions.py`](file:///d:/Keralty%20scripts/automatizaciones_python/retroactivos-clinica-colsanitas/src/exceptions.py):
* `ConfigError`: Fallos en la lectura o parseo de `config.yaml` o variables de entorno.
* `DatabaseError`: Errores de conexión, permisos o ejecución de consultas en Oracle (incluye detección de errores de archivador `ORA-00257`).
* `DateFormatError`: Errores al convertir formatos de fecha en los DataFrames.

Todos los eventos, advertencias y errores son registrados mediante **Loguru** para facilitar el monitoreo y la auditoría.
