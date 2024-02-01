import pandas as pd
import numpy as np
import logging
from database_functions.funcoes_base import download, save_to_excel
from main_functions.fetch_params import merge_sheets
from main_functions.processamento import calculate_grades, calculate_min_max_columns, calculate_stock_suggestion
from database_functions.queries import info_gerais, historico_faturamento, quantidade_receber

# Get a logger
logger = logging.getLogger(__name__)


def download_method(query, params):
    """
    Download data using a given SQL query and parameters.
    This function additionally filters out rows where 'B1_ZGRUPO' is missing or an empty string.
    
    Parameters:
    - query (str): SQL query to fetch the data.
    - params (tuple): Parameters for the SQL query.

    Returns:
    - DataFrame: Filtered data.
    """
    data_frame = download(query, params)
    # Remove rows where 'B1_ZGRUPO' is missing, null, or an empty string
    data_frame = data_frame[data_frame['B1_ZGRUPO'].str.strip() != '']
    return data_frame


def general_information(filial):
    """
    Fetch and process the general information data frame for a specific branch (filial).

    Parameters:
    - filial (str): The branch code.

    Returns:
    - DataFrame: Processed general information.
    """
    logger.info(f"Fetching general information for branch {filial}.")

    query = info_gerais
    params = (filial, filial,)
    gi_data_frame = download_method(query, params)

    # Convert 'B2_QATU' column to numeric data
    column_to_sum = "B2_QATU"
    gi_data_frame[column_to_sum] = gi_data_frame[column_to_sum].apply(pd.to_numeric, errors='coerce')

    # Aggregate by 'B1_ZGRUPO'
    gi_data_frame = gi_data_frame.groupby('B1_ZGRUPO', as_index=False).agg({
        'B1_DESC': 'first',
        'B1_COD': 'first',
        column_to_sum: 'sum'
    })

    logger.info(f"Processed general information for branch {filial}.")
    return gi_data_frame


def orders(filial):
    """
    Fetch and process the order information data frame for a specific branch (filial).

    Parameters:
    - filial (str): The branch code.

    Returns:
    - DataFrame: Processed order information.
    """
    logger.info(f"Fetching order information for branch {filial}.")

    query = quantidade_receber
    params = (filial,)
    o_data_frame = download_method(query, params)

    # Convert 'QRE' column to numeric data
    column_to_sum = "QRE"
    o_data_frame[column_to_sum] = o_data_frame[column_to_sum].apply(pd.to_numeric, errors='coerce')

    # Aggregate by 'B1_ZGRUPO'
    o_data_frame = o_data_frame.groupby('B1_ZGRUPO', as_index=False).agg({column_to_sum: 'sum'})

    logger.info(f"Processed order information for branch {filial}.")
    return o_data_frame


def fat_history(filial):
    """
    Fetch and process the fat_history information for a specific branch (filial).
    
    Parameters:
    - filial (str): The branch code.

    Returns:
    - DataFrame: Processed fat_history information.
    """
    logger.info(f"Fetching fat_history for branch {filial}.")

    query = historico_faturamento
    params = (filial,)
    fh_data_frame = download_method(query, params)

    # Process columns for datetime and numeric formats
    fh_data_frame['D2_EMISSAO'] = pd.to_datetime(fh_data_frame['D2_EMISSAO'], format='%Y%m%d', errors='coerce')
    fh_data_frame['Month_Year'] = fh_data_frame['D2_EMISSAO'].dt.to_period('M')
    column_to_sum = "D2_QUANT"
    fh_data_frame[column_to_sum] = fh_data_frame[column_to_sum].apply(pd.to_numeric, errors='coerce')

    # Aggregate data and process further
    result = fh_data_frame.groupby(['B1_ZGRUPO', 'Month_Year'], as_index=False)[column_to_sum].sum()
    pivot_result = result.pivot_table(index='B1_ZGRUPO', columns='Month_Year', values=column_to_sum, fill_value=0,
                                      aggfunc='sum')
    pivot_result['total_sum'] = pivot_result.sum(axis=1)
    pivot_result['avg_last_two_months'] = np.ceil(pivot_result.iloc[:, -3:-1].mean(axis=1)).astype(int)
    pivot_result['avg_last_three_months'] = np.ceil(pivot_result.iloc[:, -5:-2].mean(axis=1)).astype(int)

    fh_data_frame = calculate_grades(pivot_result)

    logger.info(f"Processed fat_history for branch {filial}.")
    return fh_data_frame


def join_parts(*data_frames):
    """
    Join multiple data frames on the 'B1_ZGRUPO' column.
    NaN values will be filled with 0.
    
    Parameters:
    - *data_frames (DataFrames): One or more data frames to be joined.

    Returns:
    - DataFrame: The joined data frame.
    """
    if not data_frames:
        raise ValueError("At least one dataframe must be provided.")

    joined_df = data_frames[0]
    for df in data_frames[1:]:
        joined_df = pd.merge(joined_df, df, on='B1_ZGRUPO', how='left')
    joined_df.fillna(0, inplace=True)
    return joined_df


def create_final_df(filial, func):
    """
    Create the final data frame by merging and computing different columns.

    Parameters:
    - filial (str): The specific branch or 'Todas' for all branches.
    - func (bool): Flag to indicate whether to save the results to Excel.

    Returns:
    - pd.DataFrame: The final data frame.
    """

    # Define a list of all branches
    all_filials = ['0101', '0103', '0104', "0105"]

    # Check if 'Todas' option is selected
    if filial == 'Todas':
        filials_to_process = all_filials
    else:
        filials_to_process = [filial]

    # Initialize an empty DataFrame to hold the aggregated results
    aggregated_df = pd.DataFrame()

    for current_filial in filials_to_process:
        logger.info(f"Creating final data frame for branch {current_filial}.")

        # Retrieve necessary data
        general_info = general_information(current_filial)
        order_info = orders(current_filial)
        fat_info = fat_history(current_filial)

        # Join the tables
        joined_table = join_parts(general_info, order_info, fat_info)

        # Fetch params from params and prepare for merging
        params_df = merge_sheets(filial=current_filial)
        joined_table['B1_ZGRUPO'] = joined_table['B1_ZGRUPO'].astype(str)
        params_df['B1_ZGRUPO'] = params_df['B1_ZGRUPO'].astype(str)

        # Merge the tables and calculate necessary columns
        intermediate_df = pd.merge(joined_table, params_df, on='B1_ZGRUPO', how='left')

        intermediate_df = calculate_min_max_columns(intermediate_df)
        final_df = calculate_stock_suggestion(intermediate_df)

        # Rename and map columns as needed
        column_mapping_excel = {
            'B1_ZGRUPO': 'Agrupamento',
            'B1_DESC': 'Descrição',
            'B1_COD': 'Código',
            'B2_QATU': 'Estoque',
            'QRE': 'Quantidade pedida',
            'total_sum': 'Total',
            'avg_last_two_months': 'Média_2',
            'avg_last_three_months': 'Média_3',
            'grade': 'Nota',
            'stock_suggestion': 'Sugestão de Compra'
        }
        final_df = final_df.rename(columns=column_mapping_excel)

        # Rename non-common columns to include the branch identifier
        non_common_columns = [col for col in final_df.columns if col not in ['Agrupamento', 'Descrição', 'Código']]
        renamed_columns = {col: f"{col}_{current_filial}" for col in non_common_columns}
        final_df.rename(columns=renamed_columns, inplace=True)

        # Merge the current final_df into the aggregated_df
        if aggregated_df.empty:
            aggregated_df = final_df
        else:
            aggregated_df = pd.merge(aggregated_df, final_df, on=['Agrupamento', 'Descrição', 'Código'], how='outer')

    # Process the aggregated data frame
    if filial == 'Todas':
        # Create a copy of the sliced DataFrame to avoid SettingWithCopyWarning
        df = aggregated_df[['Agrupamento', 'Descrição', 'Código', 'Nota_0101', 'Nota_0103', 'Nota_0104', 'Nota_0105',
                            'Segurança_0101', 'Segurança_0103', 'Segurança_0104', 'Segurança_0105', 'min_0101',
                            'min_0103', 'min_0104', 'min_0105', 'max_0101', 'max_0103', 'max_0104', 'max_0105']].copy()

        # Now fill NaN values with appropriate defaults
        df.fillna({'Nota_0101': 0, 'Nota_0103': 0, 'Nota_0104': 0, 'Nota_0105': 0,
                   'Segurança_0101': 0, 'Segurança_0103': 0, 'Segurança_0104': 0, 'Segurança_0105': 0,
                   'min_0101': 0, 'min_0103': 0, 'min_0104': 0, 'min_0105': 0, 'max_0101': 0, 'max_0103': 0,
                   'max_0104': 0, 'max_0105': 0}, inplace=True)

        if func:
            # Save the aggregated result
            save_to_excel(df, "sugestão_compra_", 'Todas', open_file=True)
            logger.info("Final data frame for all branches saved to Excel.")

            # Return the processed aggregated DataFrame
            return df
        else:
            return df

    if func:
        # Save the final result
        save_to_excel(final_df, "sugestão_compra_", filial, open_file=True)
        logger.info(f"Final data frame for branch {filial} saved to Excel.")

        return final_df

    else:
        return final_df
