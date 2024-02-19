import pandas as pd
import logging
import os
import datetime
from database_functions.db_connect import Database, config
from openpyxl import load_workbook

# Get a logger
logger = logging.getLogger(__name__)


def download(query, params=None):
    """
    Downloads data from the database using a specified SQL query.

    Parameters:
    - query (str): SQL query to execute.
    - params (dict, optional): Parameter for the SQL query.

    Returns:
    - DataFrame: DataFrame containing the results or None if an error occurred.
    """
    # Create an instance of the Database class and establish a connection.
    db_instance = Database(db_config=config, db_type='sql_server')
    db = db_instance.connect()

    try:
        # Execute the SQL query and store the result in a DataFrame.
        if params:
            data_frame = pd.read_sql(query, db, params=params)
        else:
            data_frame = pd.read_sql(query, db)
        logger.info("download was successful")
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        data_frame = None

    return data_frame
