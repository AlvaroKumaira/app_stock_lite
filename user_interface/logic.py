import logging
import pandas
from . import resources_rc
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QTableWidgetItem, QCheckBox, QVBoxLayout
from .download_thread import DownloadThread

logger = logging.getLogger(__name__)


class BaseLogic:
    def __init__(self, ui):
        self.ui = ui
        self.download_thread = None

    def on_thread_finished(self):
        self.download_thread.deleteLater()

    def start_progress(self):
        self.ui.progressBar.show()
        self.ui.progress_sug.show()
        self.ui.progressBar_search.show()
        self.ui.progressBar_2.show()

    def stop_progress(self):
        self.ui.progressBar.hide()
        self.ui.progress_sug.hide()
        self.ui.progressBar_search.hide()
        self.ui.progressBar_2.hide()


class BuscaLogic(BaseLogic):

    def __init__(self, ui):
        super().__init__(ui)
        self.setup_connections()

    def setup_connections(self):
        self.ui.search_start.clicked.connect(self.start_search)

    def start_search(self):
        product_id = self.ui.lineEdit.text().strip()
        self.download_thread = DownloadThread(search_function, product_id)
        self.download_thread.progress_started.connect(self.start_progress)
        self.download_thread.progress_stopped.connect(self.stop_progress)

        # Connect both update_labels to the finished_with_result signal
        self.download_thread.finished_with_result.connect(self.update_labels)
        self.download_thread.finished_with_result.connect(self.display_dataframe)

        self.download_thread.start()

    def update_labels(self, df):
        if df is None or df.empty:
            self.clear_labels()
            self.ui.agrup_label.setText(f"Agrupamento: Não encontrado!")
            self.ui.desc_label.setText(f"Descrição: Não encontrado!")
            return
        try:
            self.clear_labels()
            # Get all values from the table
            group_value = df.iloc[0]['B1_ZGRUPO']
            item_group_value = df.iloc[0]['B1_GRUPO']
            group_desc = df.iloc[0]['BM_DESC']
            desc_value = df.iloc[0]['B1_DESC']

            # Set all labels
            self.ui.agrup_label.setText(f"Agrupamento: {group_value}")
            self.ui.group_label.setText(f"Grupo: {item_group_value} - {group_desc}")
            self.ui.desc_label.setText(f"Descrição: {desc_value}")
        except Exception as e:
            self.clear_labels()
            logger.info(f"using code instead of group code. {e} ")
            group_value = df.iloc[0]['B1_ZGRUPO']
            item_group_value = df.iloc[0]['B1_GRUPO']
            group_desc = df.iloc[0]['BM_DESC']
            desc_value = df.iloc[0]['B1_DESC']
            self.ui.agrup_label.setText(f"Agrupamento: {group_value}")
            self.ui.group_label.setText(f"Grupo: {item_group_value} - {group_desc}")
            self.ui.desc_label.setText(f"Descrição: {desc_value}")

    def display_dataframe(self, df):
        """
        Display the dataframe in the QTableWidget.
        """
        if df is None or df.empty:
            self.ui.search_result.clearContents()
            self.ui.search_result.setRowCount(1)
            return

            # Rename columns
        column_names = {"B1_COD": "Código", "B2_QATU": "Quantidade", "B2_FILIAL": "Filial"}
        df.rename(columns=column_names, inplace=True)

        # Group by 'Código' and aggregate 'Quantidade' for each 'Filial'
        grouped_df = df.pivot_table(index='Código', columns='Filial', values='Quantidade', aggfunc='sum', fill_value=0)

        # Set the row count
        self.ui.search_result.setRowCount(grouped_df.shape[0])

        # Define the column index for branches
        matriz_col_index = 1
        cariacica_col_index = 2
        pocone_col_index = 3
        paraua_col_index = 4

        # Populate the QTableWidget
        for row_index, (codigo, row_data) in enumerate(grouped_df.iterrows()):
            # Set code value
            self.ui.search_result.setItem(row_index, 0, QTableWidgetItem(str(codigo)))

            # Set quantities in respective columns
            self.ui.search_result.setItem(row_index, matriz_col_index, QTableWidgetItem(str(row_data.get('0101', 0))))
            self.ui.search_result.setItem(row_index, cariacica_col_index,
                                          QTableWidgetItem(str(row_data.get('0104', 0))))
            self.ui.search_result.setItem(row_index, pocone_col_index, QTableWidgetItem(str(row_data.get('0103', 0))))
            self.ui.search_result.setItem(row_index, paraua_col_index, QTableWidgetItem(str(row_data.get('0105', 0))))

    def clear_labels(self):
        self.ui.agrup_label.setText(f"Agrupamento: ")
        self.ui.group_label.setText(f"Grupo: ")
        self.ui.desc_label.setText(f"Descrição: ")
