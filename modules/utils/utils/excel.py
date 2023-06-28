""" Клиент для работы с Excel

https://trenton3983.github.io/files/solutions/2020-06-22_pivot_table_win32com/create_pivot_table_with_win32com.html
"""
__author__ = 'ke.mizonov'
import re
import shutil
import sys
from time import sleep
from datetime import datetime, date, time
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Union, Tuple
import pythoncom
import win32ctypes
import win32timezone
from PIL import ImageGrab
from pandas import DataFrame, ExcelWriter, read_excel, read_csv
# фикс см. https://stackoverflow.com/questions/33267002/why-am-i-suddenly-getting-a-no-attribute-clsidtopackagemap-error-with-win32com
import win32com.client  # pip install pywin32
from utils.constants import DataBase, PivotDataBase, ConditionalFormattingBase, ConsolidationFunctionBase, \
    GroupFunctionBase, PivotFieldBase, NumberFormatBase, IMG_EXT, ColWidthBase, PivotFilterBase, PivotColBase, \
    CalculationConstantBase, AnalysisBase
from utils.errors import UnknownFileFormatError
from worker.worker import Worker


@dataclass()
class ExcelClient:
    """ Клиент для работы с Excel """
    file_name: str = field(init=True, default='test')
    file_ext: str = field(init=True, default='.xlsx')
    file_path: str = field(init=True, default='reports')

    @dataclass()
    class PivotCol(PivotColBase):
        """ Столбец сводной таблицы """

    @dataclass(frozen=True)
    class ColWidth(ColWidthBase):
        """ Константы ширины для колонок с определенным содержимым """

    @dataclass()
    class Data(DataBase):
        """ Данные клиента для работы с Excel """

    @dataclass()
    class PivotData(PivotDataBase):
        """ Данные клиента для работы с Excel (сводные таблицы) """

    @dataclass(frozen=True)
    class ConditionalFormatting(ConditionalFormattingBase):
        """ Условное форматирование: что считать зеленым цветом, что красным """

    @dataclass(frozen=True)
    class ConsolidationFunction(ConsolidationFunctionBase):
        """ Консолидирующая функция для сводной таблицы: сумма, среднее, количество и проч. """

    @dataclass(frozen=True)
    class GroupFunction(GroupFunctionBase):
        """ Класс, объединяющий функции группировки для сводных таблиц """

    @dataclass(frozen=True)
    class NumberFormat(NumberFormatBase):
        """ Формат ячеек Excel """

    @dataclass(frozen=True)
    class CalculationConstant(CalculationConstantBase):
        """ Константа, отвечающая за вычисления в поле сводной таблицы """

    @dataclass()
    class PivotField(PivotFieldBase):
        """ Данные клиента для работы с Excel (поле сводной таблицы) """

    @dataclass(frozen=True)
    class Analysis(AnalysisBase):
        """ Настройки анализа данных (осуществляется после построения пивота) """

    @dataclass()
    class PivotFilter(PivotFilterBase):
        """ Настройки фильтров """

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
            # df = df.fillna(' --')
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

    def write_pivot(self, data: Data, worker: Optional[Worker] = None):
        """ Создание файла Excel со сводной таблицей

        Args:
            data: данные в формате Data
            worker: экземпляр воркера

        References:
            https://www.youtube.com/watch?v=ZS4d3JvbQHQ
        """
        if worker:
            worker.emit({'msg': 'Building pivot tables...'})
        script_dir = os.path.abspath(os.curdir)
        # константы объектной модели Excel
        win32c = win32com.client.constants
        # грубо говоря, тут инициализируется приложение Excel
        excel_app = None
        while not excel_app:
            try:
                # поскольку метод будет использоваться в отдельном потоке, нужна явная инициализация
                pythoncom.CoInitialize()
                excel_app = win32com.client.gencache.EnsureDispatch('Excel.Application')
            except AttributeError:
                # todo очистка кэша вызвает новые проблемы
                print(
                    'Ошибка инициализации приложения Excel через ком-порт.'
                    '\nОчистка кэша. Новая попытка инициализации через 2 секунды'
                )
                # очистим кэш, т.к.:
                # win32com создает кэш в виндовской папке пользователя, что иногда вызывает ошибку:
                # This COM object can not automate the makepy process - please run makepy manually for this object
                self.__remove_win32com_cache()
                sleep(2)
        # excel_app = win32com.client.Dispatch('Excel.Application', clsctx=pythoncom.CLSCTX_LOCAL_SERVER)
        # excel_app = win32com.client.Dispatch("Excel.Application", pythoncom.CoInitialize())
        excel_app.DisplayAlerts = False
        # новая книга Excel
        wb = excel_app.Workbooks.Add()
        # если указан внешний файл с данными, используем его
        if data.outer_file:
            if worker:
                worker.emit({'msg': 'Loading data from file...'})
            # откроем файл с данными
            outer_file = os.path.join(script_dir, self.file_path, f'{data.outer_file}{self.file_ext}')
            source_book = excel_app.Workbooks.Open(outer_file)
            source_sheet = source_book.Sheets(1)
            source_sheet.Copy(pythoncom.Empty, wb.Sheets(wb.Sheets.Count))
            # тут все как в VBA
            last_row = self.__get_last_row(sheet=source_sheet)
            last_col = self.__get_last_col(sheet=source_sheet)
            data_sheet = wb.Sheets('data')      # fixme тут предполагаем, что лист называется data
            # первый (пустой) лист удаляем
            wb.Sheets(1).Delete()
        else:
            # запись данных, на основе которых будет строиться сводная таблица
            data_sheet = wb.Sheets(1)
            data_sheet.Name = 'data'
            collection = data.data
            # записываем заголовки
            for num, key in enumerate(collection[0].keys(), 1):
                data_sheet.Cells(1, num).Value = key
            # записываем данные
            total = len(collection)
            for row, item in enumerate(collection, 2):
                if worker and not worker.isRunning:
                    worker.emit({'done': True})
                    worker.terminate()
                    return
                if worker:
                    worker.emit({'num': row, 'total': total, 'msg': f'Loading data: {row} of {total}'})
                for col, value in enumerate(item.values(), 1):
                    # тут ожидаются pywintypes, поэтому с некоторыми типами данных будут проблемы
                    if isinstance(value, date):
                        value = datetime(value.year, value.month, value.day, tzinfo=win32timezone.TimeZoneInfo.utc())
                    if isinstance(value, time):
                        value = str(value)
                    data_sheet.Cells(row, col).Value = value
            # последние заполненные строка и столбец
            last_row, last_col = len(collection) + 1, len(collection[0])
        # диапазон таблицы данных
        src_range = data_sheet.Range(
            data_sheet.Cells(1, 1),
            data_sheet.Cells(last_row, last_col)
        )
        # сбросим фильтры, чтобы избежать проблем с ListObjects.Add, который с т.з. Excel пытается применить фильтр
        data_sheet.AutoFilterMode = False
        data_sheet.ListObjects.Add(
            SourceType=win32c.xlSrcRange,
            Source=src_range,
            XlListObjectHasHeaders=win32c.xlYes
        ).Name = 'DT_Source'
        for pivot_data in data.pivot:
            self.__add_pivot_table(
                excel_app=excel_app,
                wb=wb,
                src_range=src_range,
                data=pivot_data,
                worker=worker
            )
        # сохранение в файл
        if worker:
            worker.emit({'msg': 'Saving result...'})
        wb.SaveAs(os.path.join(script_dir, self.file_path, f'{self.file_name}{self.file_ext}'))
        excel_app.DisplayAlerts = True
        excel_app.Application.Quit()

    def __add_pivot_table(
        self,
        excel_app: object,
        wb: object,
        src_range: object,
        data: PivotData,
        worker: Optional[Worker] = None
    ):
        """ Добавление сводной таблицы

        Args:
            excel_app: приложение Excel
            wb: книга для размещения сводной таблицы
            src_range: диапазон значений с данными для сводной таблицы
            data: данные, на основе которых будет построена сводная таблица
            worker: экземпляр воркера
        """
        # константы объектной модели Excel
        win32c = win32com.client.constants
        # номер первой строки с данными
        first_data_row = data.first_data_row or self.first_data_row(data)
        # добавляем лист сводной таблицы
        wb.Sheets.Add(After=wb.Sheets(wb.Sheets.Count))
        pivot_sheet = wb.Sheets(wb.Sheets.Count)
        # данные помещаются в кэш, на основе которого строится сводная таблица
        print(f'=== {data.sheet} ===')
        cache_table = wb.PivotCaches().Create(
            SourceType=win32c.xlDatabase,
            SourceData=src_range,
            Version=win32c.xlPivotTableVersion14
        )
        if worker:
            worker.emit({'msg': f'Working on sheet: {data.sheet}'})
        pivot_sheet.Name = data.sheet
        table = cache_table.CreatePivotTable(
            TableDestination=pivot_sheet.Range(pivot_sheet.Cells(1, 1), pivot_sheet.Cells(1, 1)),
            TableName=data.sheet,
            DefaultVersion=win32c.xlPivotTableVersion14
        )
        # table.PivotCache.MissingItemsLimit = win32c.xlMissingItemsNone
        # table.RefreshTable()
        # фильтры
        for num, _filter in enumerate(data.filters or [], 1):
            # print('filter by', _filter.key)
            field_obj = table.PivotFields(_filter.key)
            field_obj.Orientation = win32c.xlPageField
            field_obj.Position = num
            if not _filter.selected:
                continue
            # снимаем / устанавливаем фильтры
            field_obj.EnableMultiplePageItems = True
            for item in field_obj.PivotItems() or []:
                # print(item.Name, type(item.Name), _filter.selected, item.Name in _filter.selected)
                try:
                    item.Visible = item.Name in _filter.selected
                except:
                    print('pivot filter err', item.Name)
        # строки
        for num, key in enumerate(data.rows or [], 1):
            # print(num, key)     # stage_08_prior_consent_date
            field_obj = table.PivotFields(key)
            field_obj.Orientation = win32c.xlRowField
            field_obj.Position = num
        # столбцы
        for num, column in enumerate(data.cols or [], 2):
            # print(column.key, type(column.key))
            field_obj = table.PivotFields(column.key)
            # field_obj.Function = self.ConsolidationFunction.Count
            field_obj.Orientation = win32c.xlColumnField
            try:
                field_obj.Position = num
            except:
                pass
            # снимаем / устанавливаем фильтры
            for item in table.PivotFields(column.key).PivotItems() or []:
                try:
                    item.Visible = item.Name in column.selected
                except:
                    pass
            # for item in table.PivotFields(column.key).PivotItems() or []:
            #     item.Visible = False
            for position, selected_col in enumerate(column.selected or [], 1):
                item = table.PivotFields(column.key).PivotItems(selected_col)
                # item.Visible = True
                item.Position = position
        # значения
        for col, item in enumerate(data.values or [], 2):
            self.__set_pivot_value(
                row=first_data_row,
                col=col,
                item=item,
                app=excel_app,
                sheet=pivot_sheet,
                table=table
            )
        # группировка
        if data.group_function:
            data.group_function(sheet=pivot_sheet, row_num=first_data_row)
        # коллапс вложенных строк до верхнего уровня todo коллапс всех не работает почему-то
        if data.collide is True and len(data.rows) > 1:
            items = table.PivotFields(data.rows[0]).PivotItems() or []
            total = len(items)
            for num, item in enumerate(items):
                if worker:
                    worker.emit({
                        'msg': f'Working on sheet: {data.sheet}, colliding rows: {num+1} of {total}',
                        'num': num+1,
                        'total': total
                    })
                item.ShowDetail = False
        # закрепление строк / столбцов
        if not data.graph and data.freeze_panes:
            pivot_sheet.Range(pivot_sheet.Cells(first_data_row, 2), pivot_sheet.Cells(first_data_row, 2)).Select()
            excel_app.ActiveWindow.FreezePanes = True
        # ширина колонок, перенос по словам
        for col, width in enumerate(data.col_width or [], 1):
            pivot_sheet.Columns(col).ColumnWidth = width
        pivot_sheet.Rows(first_data_row-1).WrapText = True
        pivot_sheet.Rows(first_data_row-1).AutoFit()

        # график
        if data.graph:
            pivot_sheet.Range(f'A{first_data_row}').Select()
            pivot_sheet.Shapes.AddChart2(201, win32c.xlColumnClustered)
            chart = pivot_sheet.ChartObjects(1)
            chart.Width = 1000
            chart.Height = 600
            # print(dir(chart))
            # chart.SetSourceData(pivot_sheet.Range(data.sheet))
            #     chart.IncrementLeft = 406.5
            #     chart.IncrementTop = -168.75
            #     ActiveSheet.Shapes("Chart 1").ScaleWidth
            #     1.9499986877, msoFalse, _
            #     msoScaleFromTopLeft
            # ActiveSheet.Shapes("Chart 1").ScaleHeight
            # 2.3732640712, msoFalse, _
            # msoScaleFromTopLeft
            # chart.ShowAllFieldButtons = False

        # скриншот
        # self.__save_range_image(sheet=pivot_sheet)

    @staticmethod
    def first_data_row(data: PivotData):
        filters_len = len(data.filters or [])
        return filters_len + 3 if filters_len > 0 else 2

    def __apply_formatting(
        self,
        excel_app: object,
        sheet: object,
        row: int,
        col: int,
        conditional_formatting: int = True
    ):
        """ Применить условное форматирование (работает только для сводной таблицы! только для текущего листа!)

        Args:
            excel_app: приложение Excel (win32com)
            sheet: экземпляр листа Excel (объект)
            row: номер первой строки, содержащей данные
            col: номер столбца, к которому применяем условное форматирование
            conditional_formatting: условное форматирование
        """
        # константы объектной модели Excel
        win32c = win32com.client.constants
        if conditional_formatting == self.ConditionalFormatting.Bars:
            # print(self.__get_last_row(sheet=sheet))
            sheet.Range(sheet.Cells(row, col), sheet.Cells(self.__get_last_row(sheet=sheet)-1, col)).Select()
            excel_app.Selection.FormatConditions.AddDatabar()
            condition = excel_app.Selection.FormatConditions(excel_app.Selection.FormatConditions.Count)
            condition.ShowValue = True
            condition.SetFirstPriority()
            condition.MinPoint.Modify(win32c.xlConditionValueAutomaticMin)
            condition.MaxPoint.Modify(win32c.xlConditionValueAutomaticMax)
            condition.BarColor.Color = 13012579
            condition.BarColor.TintAndShade = 0
            condition.BarFillType = win32c.xlDataBarFillGradient
            condition.Direction = win32c.xlContext
            condition.NegativeBarFormat.ColorType = win32c.xlDataBarColor
            condition.BarBorder.Type = win32c.xlDataBarBorderSolid
            condition.NegativeBarFormat.BorderColorType = win32c.xlDataBarColor
            condition.BarBorder.Color.Color = 13012579
            condition.BarBorder.Color.TintAndShade = 0
            condition.AxisPosition = win32c.xlDataBarAxisAutomatic
            # condition.NegativeBarFormat.AxisColor.Color = 255
            # condition.NegativeBarFormat.AxisColor.TintAndShade = 0
            condition.NegativeBarFormat.Color.Color = 255
            condition.NegativeBarFormat.Color.TintAndShade = 0
            condition.NegativeBarFormat.BorderColor.Color = 255
            condition.NegativeBarFormat.BorderColor.TintAndShade = 0
            condition.ScopeType = win32c.xlSelectionScope
            return
        green = 8109667
        yellow = 8711167
        red = 7039480
        # достаточно выделить одну ячейку с данными fixme хардкод строки
        sheet.Range(sheet.Cells(row, col), sheet.Cells(row, col)).Select()
        excel_app.Selection.FormatConditions.AddColorScale(ColorScaleType=3)
        excel_app.Selection.FormatConditions(excel_app.Selection.FormatConditions.Count).SetFirstPriority()
        [csc1, csc2, csc3] = [excel_app.Selection.FormatConditions(1).ColorScaleCriteria(n) for n in range(1, 4)]
        csc1.Type = win32c.xlConditionValueLowestValue
        csc1.FormatColor.Color = red if conditional_formatting == self.ConditionalFormatting.MaxIsGreen else green
        csc1.FormatColor.TintAndShade = 0
        csc2.Type = win32c.xlConditionValuePercentile
        csc2.FormatColor.Color = yellow
        csc2.FormatColor.TintAndShade = 0
        csc3.Type = win32c.xlConditionValueHighestValue
        csc3.FormatColor.Color = green if conditional_formatting == self.ConditionalFormatting.MaxIsGreen else red
        csc3.FormatColor.TintAndShade = 0
        # задает область применения форматирования
        excel_app.Selection.FormatConditions(1).ScopeType = win32c.xlFieldsScope
        # снимаем выделение ячеек
        sheet.Range("A1").Select()

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

    def __remove_win32com_cache(self):
        """ Удаляет кэш win32com """
        modules_copy = sys.modules.copy()
        for module in (m.__name__ for m in modules_copy.values()):
            if re.match(r'win32com\.gen_py\..+', module):
                del sys.modules[module]
        shutil.rmtree(os.path.join(os.environ.get('LOCALAPPDATA'), 'Temp', 'gen_py'))

    def __save_range_image(
        self,
        sheet: object,
        file_name: Optional[str] = None,
        excel_range: Optional[Tuple[int, int, int, int]] = None
    ):
        """ Сохраняет скриншот диапазона ячеек в файл

        Args:
            sheet: лист Excel как объект
            file_name: имя файла скриншота
            excel_range: координаты диапазона ячеек (row_1, col_1, row_2, col_2)
        """
        win32c = win32com.client.constants
        if not excel_range:
            excel_range = (1, 1, self.__get_last_row(sheet=sheet), self.__get_last_row(sheet=sheet))
        if not file_name:
            file_name = sheet.Name
        row_1, col_1, row_2, col_2 = excel_range
        sheet.Range(sheet.Cells(row_1, col_1), sheet.Cells(row_2, col_2)).CopyPicture(Format=win32c.xlBitmap)
        img = ImageGrab.grabclipboard()
        imgFile = os.path.join(self.file_path, f'{file_name}{IMG_EXT}')
        img.save(imgFile)

    def __set_pivot_value(self, row: int, col: int, item: PivotFieldBase, app: object, sheet: object, table: object):
        """ Задает параметры отображаемых значений сводной таблицы

        Args:
            row: номер первой строки, содержащей данные
            col: номер колонки
            item: параметры вида:
                key: str,
                calculated: Optional[str],
                conditional_formatting: Optional[int],
                consolidation_function: Optional[object],
                number_format: Optional[str]
                displayed_name: Optional[str]
            app: экземпляр приложения Excel
            sheet: экземпляр листа Excel
            table: экземпляр сводной таблицы
        """
        # print('*', item.key, item.displayed_name)
        # константы объектной модели Excel
        win32c = win32com.client.constants
        # тип поля: вычисляемое поле или поле данных
        # print(item.key)
        if item.calculated and isinstance(item.calculated, str):
            try:
                data_field = table.CalculatedFields().Add(item.key, item.calculated)
                # print(item.key)
                data_field.Caption = f'{item.key} '
            except Exception as e:
                print(e)
                return
        elif item.calculated and isinstance(item.calculated, int):
            data_field = table.AddDataField(table.PivotFields(item.key))
            data_field.Calculation = item.calculated
        else:
            data_field = table.AddDataField(table.PivotFields(item.key))
        data_field.Orientation = win32c.xlDataField
        # консолидирующая функция
        data_field.Function = item.consolidation_function
        if item.conditional_formatting is not None:
            self.__apply_formatting(
                excel_app=app,
                sheet=sheet,
                row=row,
                col=col,
                conditional_formatting=item.conditional_formatting
            )
        # отображаемое имя поля
        if item.displayed_name:
            data_field.Caption = f'{item.displayed_name} '
        # формат выводимых значений
        if item.number_format:
            data_field.NumberFormat = item.number_format

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
        # data_pt = pivot_table(df, index=sheet_data.headers)
        self.to_excel(df=df, writer=writer, sheet_data=sheet_data)
        workbook = writer.book
        worksheet = writer.sheets.get(sheet_data.sheet)
        if not worksheet:
            print(f'Worksheet not found: {sheet_data.sheet}')
            return
        # else:
        #     print(file)
        #     workbook = xlsxwriter.Workbook(file)
        #     print(workbook)
        #     worksheet = workbook.get_worksheet_by_name(sheet_data.sheet)
        #     print(worksheet)
        # доп настройки листа
        max_row, max_col = df.shape
        # data table (таблицы несовместимы с автофильтрами, к примеру)
        if sheet_data.data_table:
            params = {
                'name': sheet_data.data_table,
                'columns': [{'header': value} for value in df.columns.values]
            }
            worksheet.add_table(0, 0, max_row, max_col - 1, params)
            # if not sheet_data.overwrite:
            #     print(max_row, max_col)
            #     self.to_excel(df=df, writer=writer, sheet_data=sheet_data)
            #     writer.save()
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
                # 'type': '3_color_scale',
                # 'min_color': '#C5D9F1',
                # 'max_color': '#538ED5',
                'type': 'data_bar',
                'bar_color': '#63C384',
            }
            worksheet.conditional_format(first_row, first_col, last_row, last_col, params)
        # if not sheet_data.overwrite:
        #     self.to_excel(df=df, writer=writer, sheet_data=sheet_data)
        #     writer.save()

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

    @staticmethod
    def __get_last_row(sheet: object, col: int = 1):
        """ Получает номер последней заполненной строки

        Args:
            sheet: лист Excel как объект
            col: номер столбца, по которому проверяется строка

        Returns:
            номер последней заполненной строки
        """
        win32c = win32com.client.constants
        return sheet.Cells(sheet.Rows.Count, col).End(win32c.xlUp).Row

    @staticmethod
    def __get_last_col(sheet: object, row: int = 1):
        """ Получает номер последнего заполненного столбца

        Args:
            sheet: лист Excel как объект
            row: номер строки, по которой проверяется столбец

        Returns:
            номер последнего заполненного столбца
        """
        win32c = win32com.client.constants
        return sheet.Cells(row, sheet.Columns.Count).End(win32c.xlToLeft).Column
