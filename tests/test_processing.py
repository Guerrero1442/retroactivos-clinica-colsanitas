# tests/test_processing.py
import pandas as pd
import pytest

from exceptions import DateFormatError
from processing import perform_crossing, prepare_dataframes_for_crossing


def test_prepare_dataframes_for_crossing():
    """
    Tests the preparation of DataFrames, including date conversion and key creation.
    """
    df_retro_excel = pd.DataFrame(
        {
            "fec cargo": ["2023-01-15 10:00:00", "2023-01-16 12:00:00"],
            "num factura": ["F001", "F002"],
            "tip doc": ["CC", "CE"],
            "num doc": ["123", "456"],
            "Codigo Cups": ["890201", "890202"],
        }
    )
    df_upc_db = pd.DataFrame(
        {
            "f_prestacion": ["2023-01-15", "2023-01-17"],
            "no_factura": ["F001", "F003"],
            "tipo_id": ["CC", "CC"],
            "no_id": ["123", "789"],
            "cups": ["890201", "890203"],
        }
    )

    df_retro_proc, df_upc_proc = prepare_dataframes_for_crossing(
        df_retro_excel.copy(),
        df_upc_db.copy(),
        format_date_excel="%Y-%m-%d",
        format_date_db="%Y-%m-%d",
        format_date_crossing="%d/%m/%Y",
    )

    assert "llave_retroactivo" in df_retro_proc.columns
    assert df_retro_proc["fec cargo"].tolist() == ["15/01/2023", "16/01/2023"]
    assert df_retro_proc["llave_retroactivo"].iloc[0] == "F001CC12389020115/01/2023"

    assert "llave_upc" in df_upc_proc.columns
    assert df_upc_proc["f_prestacion"].tolist() == ["15/01/2023", "17/01/2023"]
    assert df_upc_proc["llave_upc"].iloc[0] == "F001CC12389020115/01/2023"


def test_perform_crossing():
    """
    Tests the crossing logic between the two prepared DataFrames.
    """
    df_retro_excel = pd.DataFrame(
        {
            "llave_retroactivo": [
                "F001CC12389020115-01-2023",
                "F002CE45689020216-01-2023",
                "F004TI99989020418-01-2023",
            ]
        }
    )
    df_upc_db = pd.DataFrame(
        {"llave_upc": ["F001CC12389020115-01-2023", "F003CC78989020317-01-2023"]}
    )

    df_resultado = perform_crossing(df_retro_excel, df_upc_db)

    expected = pd.Series(["SI", "NO", "NO"])
    assert "encontrado_upc" in df_resultado.columns
    assert all(df_resultado["encontrado_upc"] == expected)


def test_prepare_dataframes_with_missing_values():
    """
    Tests robustness of data preparation with missing or malformed dates.
    """
    df_retro_excel = pd.DataFrame(
        {
            "fec cargo": ["2023-01-15 10:00:00", pd.NaT],
            "num factura": ["F001", "F002"],
            "tip doc": ["CC", "CE"],
            "num doc": ["123", pd.NA],
            "Codigo Cups": ["890201", "890202"],
        }
    )
    df_upc_db = pd.DataFrame(
        {
            "f_prestacion": [pd.NaT, "2023-01-17"],
            "no_factura": ["F001", "F003"],
            "tipo_id": ["CC", "CE"],
            "no_id": ["123", "789"],
            "cups": [pd.NA, "890203"],
        }
    )

    df_retro_proc, df_upc_proc = prepare_dataframes_for_crossing(
        df_retro_excel,
        df_upc_db,
        format_date_excel="%Y-%m-%d",
        format_date_db="%Y-%m-%d",
        format_date_crossing="%d/%m/%Y",
    )

    assert "F002CE890202" in df_retro_proc["llave_retroactivo"].values

    assert "F001CC123" in df_upc_proc["llave_upc"].values


def test_prepare_dataframes_with_invalid_date_format():
    """
    Tests robustness of data preparation with invalid date formats.
    """
    df_retro_excel = pd.DataFrame(
        {
            "fec cargo": ["2023-01-15 10:00:00", "not-a-date"],
            "num factura": ["F001", "F002"],
            "tip doc": ["CC", "CE"],
            "num doc": ["123", pd.NA],
            "Codigo Cups": ["890201", "890202"],
        }
    )
    df_upc_db = pd.DataFrame(
        {
            "f_prestacion": [pd.NaT, "2023-01-17"],
            "no_factura": ["F001", "F003"],
            "tipo_id": ["CC", "CE"],
            "no_id": ["123", "789"],
            "cups": [pd.NA, "890203"],
        }
    )

    # Esto debería lanzar una excepción
    with pytest.raises(DateFormatError):
        prepare_dataframes_for_crossing(
            df_retro_excel,
            df_upc_db,
            format_date_excel="%Y-%m-%d",
            format_date_db="%Y-%m-%d",
            format_date_crossing="%d/%m/%Y",
        )
