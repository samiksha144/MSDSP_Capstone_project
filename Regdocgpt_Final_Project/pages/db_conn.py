# db_conn.py
# SQL Server connection using Windows Authentication.

import pyodbc
import streamlit as st

def sql_conn():
    """
    Returns a live pyodbc connection to SQL Server using st.secrets["sqlserver"].
    Works with Windows Authentication (Trusted_Connection).
    """
    cfg = st.secrets["sqlserver"]

    conn = pyodbc.connect(
        f'DRIVER={{{cfg["driver"]}}};'
        f'SERVER={cfg["server"]};'
        f'DATABASE={cfg["database"]};'
        'Trusted_Connection=yes;'
    )
    conn.autocommit = False
    return conn

def ping() -> bool:
    """Returns True if a quick test query succeeds."""
    try:
        with sql_conn() as c, c.cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()
        return True
    except Exception:
        return False
