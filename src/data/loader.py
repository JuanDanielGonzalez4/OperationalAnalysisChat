import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "data.xlsx"


def load_dataframes() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Carga los DataFrames de métricas y órdenes desde el archivo Excel."""
    logger.info("Cargando datos desde %s", DATA_PATH)

    df_metrics = pd.read_excel(DATA_PATH, sheet_name="RAW_INPUT_METRICS")
    df_orders = pd.read_excel(DATA_PATH, sheet_name="RAW_ORDERS")

    logger.info(
        "Datos cargados — df_metrics: %s filas, df_orders: %s filas",
        len(df_metrics),
        len(df_orders),
    )
    return df_metrics, df_orders
