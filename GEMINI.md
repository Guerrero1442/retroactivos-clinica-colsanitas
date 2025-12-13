Claro que sí. Basándome en el análisis exhaustivo de los archivos que subiste (`README.md`, `pyproject.toml` y el código fuente en `src/`), he extraído las "buenas prácticas" y patrones de diseño que definen la calidad de ese repositorio.

A continuación, he redactado un archivo `GEMINI.md` listo para usar. Este archivo servirá como "memoria de contexto" para que, cuando trabajes en tu nuevo proyecto usando la CLI de Gemini, yo (o cualquier instancia del modelo) siga estrictamente estos estándares de ingeniería de software.

Aquí tienes el contenido sugerido para tu archivo `GEMINI.md`:

# Contexto del Proyecto y Estándares de Ingeniería

Este documento define los estándares de codificación, arquitectura y mejores prácticas que deben seguirse en este proyecto. El objetivo es mantener un código robusto, tipado, modular y fácil de mantener, replicando la calidad de ingeniería del proyecto de referencia "Actualización Base Fallecidos".

## 1. Stack Tecnológico Preferido

* **Lenguaje:** Python 3.10+ (Preferiblemente 3.14+ según referencia).
* **Gestión de Dependencias:** `uv` (para velocidad y gestión de entornos virtuales y lockfiles).
* **Manejo de Datos:** `pandas` (tipado fuerte en transformaciones).
* **Base de Datos:** `SQLAlchemy` (ORM/Core) + `oracledb` (o el conector pertinente).
* **Logging:** `loguru` (en lugar del módulo `logging` estándar).
* **Configuración:** `PyYAML` o `pydantic-settings` (para separar configuración del código).
* **Calidad de Código:** `ruff` (linter/formatter) y `pyright` (validación de tipos estática).

## 2. Estructura del Proyecto

El código debe seguir una estructura modular clara:

```text
.
├── config/             # Archivos de configuración y settings (YAML, .env)
├── logs/               # Rotación de logs
├── src/                # Código fuente principal
│   ├── exceptions.py   # Excepciones personalizadas
│   ├── utils_db.py     # Lógica de conexión a BD
│   └── [modulos].py    # Lógica de negocio específica
├── main.py             # Punto de entrada
├── tests/              # Pruebas unitarias
├── pyproject.toml      # Definición del proyecto (estándar PEP 621)
└── uv.lock             # Lockfile generado por uv
````

## 3\. Reglas y Patrones de Codificación

### A. Tipado Estático (Type Hinting)

Todo el código debe estar tipado explícitamente. Se debe usar `typing` estándar (`List`, `Optional`, `Generator`) o la sintaxis moderna (`list | None`).

  * **Incorrecto:** `def procesar(df):`
  * **Correcto:**
    ```python
    def procesar(df: pd.DataFrame, fecha: str) -> pd.DataFrame:
        ...
    ```

### B. Manejo de Errores (Excepciones Personalizadas)

No capturar excepciones genéricas (`except Exception:`). Crear una jerarquía de excepciones propia en `src/exceptions.py`.

  * **Patrón:**
    1.  Crear una clase base (ej. `ProjectError(Exception)`).
    2.  Heredar errores específicos (ej. `DatabaseError`, `SourceReadError`).
    3.  Envolver el código propenso a fallos en bloques `try/except` que capturen errores de librerías (ej. `SQLAlchemyError`) y lancen las excepciones personalizadas.

### C. Logging Estructurado

Usar `loguru` para todo el registro de eventos. Configurar rotación de archivos y retención.

  * **Ejemplo:**
    ```python
    from loguru import logger
    logger.info(f"Procesando archivo: {ruta.name}")
    logger.exception("Error crítico en la base de datos") # Incluye traceback
    ```

### D. Interacción con Base de Datos

  * Usar siempre **Context Managers** (`with engine.connect() as conn:`) para asegurar el cierre de conexiones.
  * Para lecturas grandes, usar **Generadores** (`yield`) y procesar por **chunks** (`chunksize`) para no saturar la memoria RAM.
  * Transacciones explícitas (`connection.commit()`).

### E. Manejo de Rutas

Nunca usar strings para rutas de archivos. Usar siempre `pathlib.Path`.

  * **Correcto:** `ruta = Path("data") / "archivo.xlsx"`

### F. Limpieza de Datos (ETL)

  * Normalizar nombres de columnas (eliminar espacios, saltos de línea, estandarizar a mayúsculas/minúsculas).
  * Manejar fechas con robustez (usar `pd.to_datetime` con `errors='coerce'` y reportar qué filas fallaron).
  * Usar `unidecode` si es necesario limpiar caracteres especiales en nombres de columnas.

## 4\. Flujo de Trabajo con `uv`

Para cualquier tarea de instalación o ejecución, preferir los comandos de `uv`:

  * `uv add <paquete>` para instalar.
  * `uv run python main.py` para ejecutar.
  * `uv sync` para sincronizar entorno.

## 5\. Instrucciones para la IA (Gemini)

Al generar código para este proyecto:

1.  Prioriza la robustez sobre la brevedad.
2.  Incluye siempre type hints.
3.  Si sugieres una librería nueva, verifica que sea compatible con el ecosistema moderno (ej. preferir `pydantic` v2).
4.  Genera código que pase validaciones de `ruff` y `pyright`.
