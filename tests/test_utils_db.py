# tests/test_utils_db.py
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from sqlalchemy import exc as sqlalchemy_exc

from src.exceptions import DatabaseError
from src.utils_db import fetch_data_in_chunks, get_db_connection, get_upc_data


@pytest.fixture(autouse=True)
def mock_settings(monkeypatch):
    """
    Mocks settings to avoid relying on environment variables or .env files.
    """
    monkeypatch.setattr("src.utils_db.settings.db_user", "test_user")
    monkeypatch.setattr("src.utils_db.settings.db_password", "test_password")
    monkeypatch.setattr("src.utils_db.settings.db_host", "test_host")
    monkeypatch.setattr("src.utils_db.settings.db_port", 1521)
    monkeypatch.setattr("src.utils_db.settings.db_service_name", "test_service")


@patch("src.utils_db.create_engine")
def test_get_db_connection_success(mock_create_engine):
    """
    Tests successful database connection.
    """
    mock_engine = MagicMock()
    mock_conn = MagicMock()
    mock_create_engine.return_value = mock_engine
    mock_engine.connect.return_value = mock_conn

    with get_db_connection() as conn:
        assert conn is not None
        mock_create_engine.assert_called_once()
        mock_engine.connect.assert_called_once()
        # Verify the connection string used
        expected_url = "oracle+oracledb://test_user:test_password@test_host:1521/?service_name=test_service"
        mock_create_engine.assert_called_with(expected_url)


@patch("src.utils_db.create_engine", side_effect=Exception("Connection failed"))
def test_get_db_connection_failure(mock_create_engine):
    """
    Tests that a DatabaseError is raised on connection failure.
    """
    with pytest.raises(DatabaseError, match="An unexpected database error occurred"):
        with get_db_connection():
            pass


@patch("src.utils_db.create_engine")
def test_get_db_connection_oracle_archiver_error(mock_create_engine):
    """
    Tests handling of Oracle archiver error (ORA-00257).
    """
    mock_engine = MagicMock()
    mock_create_engine.return_value = mock_engine

    # Mocking oracledb.Error which is what sqlalchemy might wrap
    import oracledb

    oracle_error = MagicMock(spec=oracledb.Error)
    oracle_error.args = (MagicMock(code=257, message="Archiver error"),)

    db_error = sqlalchemy_exc.DatabaseError("statement", "params", oracle_error)
    mock_engine.connect.side_effect = db_error

    with pytest.raises(
        DatabaseError, match=r"Error de archivador de Oracle \(ORA-257\)"
    ):
        with get_db_connection():
            pass


def test_fetch_data_in_chunks_success():
    """
    Tests fetching data in chunks successfully.
    """
    mock_conn = MagicMock()
    query = "SELECT * FROM test_table"
    expected_df = pd.DataFrame({"col1": ["1", "2"], "col2": ["3", "4"]})

    # Mock de pd.read_sql_query para devolver un iterador
    with patch(
        "src.utils_db.pd.read_sql_query", return_value=iter([expected_df])
    ) as mock_read:
        chunks = list(fetch_data_in_chunks(mock_conn, query, chunk_size=2))
        assert len(chunks) == 1
        pd.testing.assert_frame_equal(chunks[0], expected_df)
        mock_read.assert_called_once()


@patch("src.utils_db.pd.read_sql_query", side_effect=Exception("Failed to fetch data"))
def test_fetch_data_in_chunks_failure(mock_read_sql_query):
    """
    Tests that DatabaseError is raised when fetching data in chunks fails.
    """
    mock_conn = MagicMock()
    query = "SELECT * FROM test_table"

    with pytest.raises(DatabaseError, match="Failed to fetch data in chunks"):
        list(fetch_data_in_chunks(mock_conn, query))


@patch("src.utils_db.fetch_data_in_chunks")
def test_get_upc_data_success(mock_fetch_data_in_chunks):
    """
    Tests successful retrieval of UPC data.
    """
    mock_conn = MagicMock()
    base_query = "SELECT * FROM upc_table WHERE 1=1"
    facturas = [f"fact{i}" for i in range(5)]
    batch_size = 2
    chunk_size = 100

    # Simular que fetch_data_in_chunks devuelve DataFrames
    mock_fetch_data_in_chunks.side_effect = [
        iter([pd.DataFrame({"id": ["1", "2"]})]),
        iter([pd.DataFrame({"id": ["3", "4"]})]),
        iter([pd.DataFrame({"id": ["5"]})]),
    ]

    df_upc = get_upc_data(mock_conn, base_query, facturas, batch_size, chunk_size)

    assert not df_upc.empty
    assert len(df_upc) == 5
    assert mock_fetch_data_in_chunks.call_count == 3


@patch("src.utils_db.fetch_data_in_chunks", return_value=iter([]))
def test_get_upc_data_no_data(mock_fetch_data_in_chunks):
    """
    Tests that an empty DataFrame is returned when no data is found.
    """
    mock_conn = MagicMock()
    base_query = "SELECT * FROM upc_table"
    facturas = ["fact1"]

    df_upc = get_upc_data(mock_conn, base_query, facturas, 10, 100)

    assert df_upc.empty
    mock_fetch_data_in_chunks.assert_called_once()
