import pandas as pd
import numpy as np
import logging
from database_functions.funcoes_base import download, save_to_excel
from database_functions.queries import report_query, report_query_orders
from main_functions.sugestao_compra import create_final_df

# Get a logger
logger = logging.getLogger(__name__)


# Get the sales information
def get_data(filial, period, select_func):
    # Map user-selected period to number of days
    period_to_days = {
        3: 89,
        6: 182,
        12: 365,
        24: 730
    }

    # Get the number of days based on the user-selected period
    query_time = period_to_days.get(period, 0)

    # If query_time is still 0, it means the user provided an invalid period.
    if query_time == 0:
        return None

    if select_func == 1:
        # Generate the query string and fetch the sales data
        query_string = report_query(query_time, filial)
        sales_df = download(query_string)

        sales_df = sales_df.rename(columns={'B1_ZGRUPO': 'Agrupamento'})

        return sales_df
    else:
        query_string = report_query_orders(query_time, filial)
        orders_df = download(query_string)

        orders_df = orders_df.rename(columns={'B1_ZGRUPO': 'Agrupamento'})

        return orders_df


def calculate_sales_metrics(data_frame, months):
    """
    Calculate the sales metrics for a given DataFrame.

    Parameters:
    - data_frame (DataFrame): The sales data.
    - months (int): The number of months selected by the user.

    Returns:
    - DataFrame: DataFrame containing the sales metrics for each B1_ZGRUPO.
    """
    # Group by B1_ZGRUPO and calculate metrics
    metrics = data_frame.groupby('Agrupamento').agg(
        sales_period_count=pd.NamedAgg(column='D2_COD', aggfunc='size'),
        demand_period_sum=pd.NamedAgg(column='D2_QUANT', aggfunc='sum'),
    )

    # Calculate averages
    metrics['average_demand'] = np.ceil(metrics['demand_period_sum'] / months).astype(int)

    return metrics


def calculate_order_metrics(data_frame):
    """
    Calculate the orders metrics for a given DataFrame.

    Parameters:
    - data_frame (DataFrame): The order data.
    - months (int): The number of months selected by the user.

    Returns:
    - DataFrame: DataFrame containing the sales metrics for each B1_ZGRUPO.
    """
    # Group by B1_ZGRUPO and calculate metrics
    metrics = data_frame.groupby('Agrupamento').agg(
        cost_period_sum=pd.NamedAgg(column='C7_PRECO', aggfunc='sum'),
        cost_period_size=pd.NamedAgg(column='C7_PRECO', aggfunc='size')
    )

    # Calculate averages
    metrics['average_cost'] = np.round(metrics['cost_period_sum'] / metrics['cost_period_size'], decimals=2)

    return metrics


def merge_data(original_data, sales_metrics, orders_metrics):
    """
    Merge the original data with the sales metrics using the B1_ZGRUPO column.

    Parameters:
    - original_data (DataFrame): The original Excel data.
    - sales_metrics (DataFrame): The calculated sales metrics.

    Returns:
    - DataFrame: Merged data containing original columns and sales metrics.
    """

    merged_data = pd.merge(original_data, sales_metrics, on='Agrupamento', how='left')
    merged_data = pd.merge(merged_data, orders_metrics, on='Agrupamento', how='left')
    return merged_data


def create_report(filial, period, func):
    """
    Generates a sales report for a given branch and period.

    Parameters:
    - filial (str): The branch for which the report is to be generated. 'Todas' indicates all branches.
    - period (str): The period for the report, such as '3 meses', '6 meses', '12 meses', or '24 meses'.
    - func (bool): Flag to determine the mode of report generation. True for individual branch reports, False for aggregated.

    Returns:
    - DataFrame: The generated report as a DataFrame.
    """

    # Convert period from string to integer
    period_mapping = {"3 meses": 3, "6 meses": 6, "12 meses": 12, "24 meses": 24}
    period_int = period_mapping.get(period, 0)

    # Define all available branches
    all_branches = ['0101', '0103', '0104', '0105']

    # Determine branches to process
    filials_to_process = all_branches if filial == 'Todas' else [filial]

    aggregated_report_df = None

    for current_filial in filials_to_process:
        # Process sales information
        sales_info_df = get_data(current_filial, period_int, select_func=1)
        sales_info_df = calculate_sales_metrics(sales_info_df, period_int)

        # Process order information
        order_info_df = get_data(current_filial, period_int, select_func=0)
        order_info_df = calculate_order_metrics(order_info_df)

        # Create and merge final data
        base_df = create_final_df(current_filial, func=False)
        report_df = merge_data(base_df, sales_info_df, order_info_df)

        columns_to_keep = ['Agrupamento', 'Descrição', 'Código', f'Estoque_{current_filial}',
                           f'Quantidade pedida_{current_filial}', f'Nota_{current_filial}', f'Segurança_{current_filial}', f'min_{current_filial}',
                           f'max_{current_filial}', 'sales_period_count', 'demand_period_sum', 'average_demand', 'average_cost']

        report_df = report_df[columns_to_keep]

        # Rename columns
        column_mapping = {
            'Estoque': 'Saldo CO',
            'Quantidade Pedida': 'Qtd. Pedida',
            'min': 'Min',
            'max': 'Max',
            'sales_period_count': 'Vendas no período',
            'demand_period_sum': 'Demanda no período',
            'average_demand': 'Demanda média mensal',
            'average_cost': 'Custo médio'
        }

        report_df = report_df.rename(columns=column_mapping)

        if filial == 'Todas':
            non_common_columns = [col for col in report_df.columns if col not in ['Agrupamento', 'Descrição', 'Código']]
            renamed_columns = {col: f"{col}_{current_filial}" for col in non_common_columns}
            report_df.rename(columns=renamed_columns, inplace=True)

        # Save individual reports or aggregate
        if func:
            save_to_excel(report_df, f"analise_inventario_{period_int}_", current_filial, open_file=False)
        else:
            if aggregated_report_df is None:
                aggregated_report_df = report_df
            else:
                # Merging data frames
                aggregated_report_df = pd.merge(aggregated_report_df, report_df,
                                                on=['Agrupamento', 'Descrição', 'Código'], how='outer')

    # After processing all branches, save the aggregated DataFrame
    if not func:
        if filial == 'Todas':
            save_to_excel(aggregated_report_df, f"analise_inventario_{period_int}", 'Todas', open_file=False)
        else:
            save_to_excel(aggregated_report_df, f"analise_inventario_{period_int}", filial, open_file=True)

    return aggregated_report_df

