""" Клиент для работы с Excel """
__author__ = 'ke.mizonov'
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Union, Tuple
from pandas import DataFrame, ExcelWriter, read_excel, read_csv


class UnknownFileFormatError(Exception):
    """ Неизвестный формат файла """


@dataclass()
class DataBase:
    """ Данные клиента для работы с Excel """
    color_map_ranges: List[Tuple] = field(init=True, default_factory=list)
    columns_width: Optional[Tuple] = field(init=True, default=None)
    data: List[Dict] = field(init=True, default_factory=list)
    headers: List[str] = field(init=True, default_factory=list)
    sheet: str = field(init=True, default='data')
    data_table: Optional[str] = field(init=True, default=None)
    overwrite: bool = field(init=True, default=True)
    outer_file: Optional[str] = field(init=True, default=None)


@dataclass()
class ExcelClient:
    """ Клиент для работы с Excel """
    file_name: str = field(init=True, default='test')
    file_ext: str = field(init=True, default='.xlsx')
    file_path: str = field(init=True, default='reports')

    @dataclass()
    class Data(DataBase):
        """ Данные клиента для работы с Excel """

    def read(
        self,
        sheet_name: Optional[Union[int, str]] = 0,
        skip_rows: Optional[int] = 0,
        encoding: Optional[str] = 'utf-8'
    ) -> List[Dict]:
        """ Чтение из файла Excel

        Args:
            sheet_name: номер или имя листа
            skip_rows: количество пропускаемых строк сверху
            encoding: кодировка

        Returns:
            данные в формате списка словарей
        """
        file = self.__build_file_name()
        if not os.path.exists(file):
            return []
        _, ext = os.path.splitext(file)
        if ext == '.csv':
            # это нормально работает с чистым csv
            df = read_csv(file, skiprows=skip_rows, encoding=encoding, keep_default_na=False)
        else:
            df = read_excel(file, sheet_name=sheet_name, skiprows=skip_rows)
        df = df.fillna('')
        res = list(df.T.to_dict().values())
        return res

    def write(self, data: List[Data]):
        """ Сохранение данных в файл Excel

        Args:
            data: данные в формате списка Data с разбивкой по листам
        """
        self.__make_dir()
        file = os.path.join(self.file_path, f'{self.file_name}.xlsx')
        with ExcelWriter(
            file,
            engine='xlsxwriter',
            engine_kwargs={'options': {'strings_to_numbers': True}}
        ) as writer:
            for sheet_data in data:
                if not sheet_data.data:
                    continue
                self.__write_data_to_sheet(writer=writer, sheet_data=sheet_data, file=file)

    def __build_file_name(self) -> str:
        """ Построение имени файла и проверка его на существование

        Returns:
            полный проверенный путь к файлу

        Raises:
            UnknownFileFormatError: неизвестный формат файла
        """
        raw_file = os.path.join(self.file_path, self.file_name)
        if os.path.exists(raw_file):
            file = raw_file
        else:
            if os.path.exists(f'{raw_file}.xlsx'):
                file = f'{raw_file}.xlsx'
            elif os.path.exists(f'{raw_file}.xls'):
                file = f'{raw_file}.xls'
            elif os.path.exists(f'{raw_file}.csv'):
                file = f'{raw_file}.csv'
            else:
                raise UnknownFileFormatError(f'Неизвестный формат файла: {raw_file}')
        return file

    def __make_dir(self):
        """ Создание директории для сохранения файла (не рекурсивно!) """
        try:
            os.mkdir(self.file_path)
        except:
            pass

    def __write_data_to_sheet(self, writer: ExcelWriter, sheet_data: Data, file: str):
        """ Запись данных на лист Excel

        Args:
            writer: pandas ExcelWriter
            sheet_data: экземпляр данных в формате Data
            file: путь и полное имя файла
        """
        df = DataFrame(sheet_data.data)
        if not sheet_data.headers:
            sheet_data.headers = list(sheet_data.data[0].keys())
        df = df[sheet_data.headers]
        self.to_excel(df=df, writer=writer, sheet_data=sheet_data)
        workbook = writer.book
        worksheet = writer.sheets.get(sheet_data.sheet)
        if not worksheet:
            print(f'Worksheet not found: {sheet_data.sheet}')
            return
        # доп настройки листа
        max_row, max_col = df.shape
        # data table (таблицы несовместимы с автофильтрами, к примеру)
        if sheet_data.data_table:
            params = {
                'name': sheet_data.data_table,
                'columns': [{'header': value} for value in df.columns.values]
            }
            worksheet.add_table(0, 0, max_row, max_col - 1, params)
            return
        # явно задаем ширину столбцов
        for num, column_width in enumerate(sheet_data.columns_width or []):
            worksheet.set_column(num, num, column_width)
        # форматы заголовков
        header_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'top',
            # 'fg_color': '#63C384',
            'border': 1})
        worksheet.write(0, 0, 'Wheelbarrow', header_format)
        # применение формата заголовков
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, header_format)
        # автофильтр
        worksheet.autofilter(0, 0, max_row, max_col - 1)
        # границы
        cells_format = workbook.add_format({'border': 1})
        worksheet.conditional_format(0, 0, max_row, max_col-1, {'type': 'no_errors', 'format': cells_format})
        # цветовая карта
        for color_map in sheet_data.color_map_ranges:
            first_row = color_map[0] or 1
            first_col = color_map[1] or 1
            last_row = color_map[2] or max_row
            last_col = color_map[3] or 1
            # todo выделить пресеты и передавать их пятым параметром в color_map
            params = {
                'type': '3_color_scale',
                'min_color': '#C5D9F1',
                'max_color': '#538ED5',
                # 'type': 'data_bar',
                'bar_color': '#63C384',
            }
            worksheet.conditional_format(first_row, first_col, last_row, last_col, params)

    @staticmethod
    def to_excel(df: DataFrame, writer: ExcelWriter, sheet_data: Data):
        """ Сохранение в Excel

        Args:
            df: данные в формате pandas DataFrame
            writer: pandas ExcelWriter
            sheet_data: экземпляр данных в формате Data
        """
        df.to_excel(
            writer,
            index=False,
            header=sheet_data.headers,
            sheet_name=sheet_data.sheet,
            freeze_panes=(1, 0)
        )
