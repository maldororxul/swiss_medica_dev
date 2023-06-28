""" Общие константы """
__author__ = 'ke.mizonov'
from dataclasses import field, dataclass
from typing import Tuple, Optional, List, Dict, Callable, Union
from app.amo import StageItem, LeadField


IMG_EXT = '.png'
TO = ' -> '

WEEK_DAY_ENG = {
    0: 'Monday',
    1: 'Tuesday',
    2: 'Wednesday',
    3: 'Thursday',
    4: 'Friday',
    5: 'Saturday',
    6: 'Sunday'
}


@dataclass(frozen=True)
class NumberFormatBase:
    """ Формат ячеек Excel """
    Euro: str = '[$€-2] # ##0,00'
    Rub: str = '[$₽-2] # ##0,00'
    Percent: str = '0%'
    Percent_2: str = '0,00%'
    Number: str = '0'


@dataclass(frozen=True)
class ConditionalFormattingBase:
    """ Условное форматирование: колонки, либо разметка цветом - что считать зеленым цветом, что красным """
    Bars: int = 2
    MaxIsGreen: int = 0
    MaxIsRed: int = 1


@dataclass(frozen=True)
class ConsolidationFunctionBase:
    """ Консолидирующая функция для сводной таблицы: сумма, среднее, количество и проч.

    References:
        https://docs.microsoft.com/en-us/office/vba/api/excel.xlconsolidationfunction
    """
    Average: int = -4106
    Count: int = -4112
    Summ: int = -4157


@dataclass(frozen=True)
class CalculationConstantBase:
    """ Константа, отвечающая за вычисления в поле сводной таблицы

    Notes:
        https://learn.microsoft.com/ru-ru/office/vba/api/excel.xlpivotfieldcalculation
    """
    PercentOfTotal: int = 8


@dataclass(frozen=True)
class ColWidthBase:
    """ Константы ширины для колонок с определенным содержимым """
    WeeksInterval: float = 22.29
    Price: float = 13.29


@dataclass(frozen=True)
class GroupFunctionBase:
    """ Класс, объединяющий функции группировки для сводных таблиц """

    @classmethod
    def by_weeks(cls, sheet: object, row_num: int = 3):
        """ Группировка значений сводной таблицы по неделям

        Args:
            sheet: лист сводной таблицы
            row_num: номер первой строки с данными (зависит от фильтров, группировки и проч.)

        References:
            https://docs.microsoft.com/en-us/office/vba/api/excel.range.group
        """
        # fixme хардкод
        try:
            sheet.Range(f'A{row_num}').Group(
                Start=True,
                End=True,
                By=7,
                Periods=list([False, False, False, True, False, False, False])
            )
        except:
            pass

    @classmethod
    def by_months(cls, sheet: object, row_num: int = 3):
        """ Группировка значений сводной таблицы по месяцам

        Args:
            sheet: лист сводной таблицы
            row_num: номер первой строки с данными (зависит от фильтров, группировки и проч.)

        References:
            https://docs.microsoft.com/en-us/office/vba/api/excel.range.group
        """
        # fixme хардкод
        try:
            sheet.Range(f'A{row_num}').Group(
                Start=True,
                End=True,
                Periods=list([False, False, False, False, True, False, True])
            )
        except:
            pass


@dataclass()
class PivotColBase:
    """ Столбец сводной таблицы """
    key: str = field(init=True)
    selected: Optional[List[str]] = field(init=True, default=None)


@dataclass(frozen=True)
class AnalysisBase:
    """ Настройки анализа данных (осуществляется после построения пивота) """
    line_num: int = field(init=True, default=-1)
    average_deviation: Optional[Tuple[float, float]] = field(init=True, default=None)


@dataclass()
class PivotFieldBase:
    """ Данные клиента для работы с Excel (поле сводной таблицы) """
    conversion_from: Union[LeadField, StageItem] = field(init=True, default=None)
    conversion_to: Union[LeadField, StageItem] = field(init=True, default=None)
    # целевой, планируемый показатель
    target_value: Optional[Union[str, int, float]] = field(init=True, default=None)
    source: Union[LeadField, StageItem] = field(init=True, default=None)
    key: str = field(init=True, default=None)
    conditional_formatting: Optional[int] = field(init=True, default=None)
    consolidation_function: int = field(init=True, default=ConsolidationFunctionBase.Summ)
    calculated: Optional[Union[str, int]] = field(init=True, default=None)
    displayed_name: Optional[str] = field(init=True, default=None)
    number_format: Optional[str] = field(init=True, default=None)
    # поле участвует в анализе данных?
    analysis: Optional[AnalysisBase] = field(init=True, default=None)

    def __post_init__(self):
        if self.source:
            if not self.key:
                self.key = self.source.Key
            if not self.displayed_name:
                self.displayed_name = self.source.DisplayName
        if self.conversion_from and self.conversion_to:
            self.key = f'{self.conversion_from.DisplayName}{TO}{self.conversion_to.DisplayName}'
            self.calculated = f"= '{self.conversion_to.Key}' / {self.conversion_from.Key}"
            self.number_format = NumberFormatBase.Percent_2
            # плановый показатель
            if self.target_value:
                target = self.target_value
                if isinstance(target, float):
                    target = f'{round(target * 100, 2)}%'
                self.key = f'{self.key} [{target}]'
            self.displayed_name = f'{self.key} '


@dataclass()
class PivotFilterBase:
    """ Данные клиента для работы с Excel (поле сводной таблицы) """
    key: str = field(init=True)
    selected: Optional[List[str]] = field(init=True, default=None)


@dataclass()
class PivotDataBase:
    """ Данные клиента для работы с Excel (сводные таблицы) """
    sheet: str = field(init=True, default='pivot')
    rows: Optional[List[str]] = field(init=True, default=None)
    cols: Optional[List[PivotColBase]] = field(init=True, default=None)
    values: Optional[List[PivotFieldBase]] = field(init=True, default=None)
    filters: Optional[List[PivotFilterBase]] = field(init=True, default=None)
    group_function: Optional[Callable] = field(init=True, default=None)
    first_data_row: Optional[int] = field(init=True, default=None)
    collide: bool = field(init=True, default=True)
    freeze_panes: bool = field(init=True, default=True)
    col_width: Optional[Tuple[float]] = field(init=True, default=None)
    graph: bool = field(init=True, default=False)

    @classmethod
    def build(cls):
        return PivotDataBase(
            sheet=cls.sheet,
            rows=cls.rows,
            cols=cls.cols,
            filters=cls.filters,
            values=cls.values,
            group_function=cls.group_function,
            first_data_row=cls.first_data_row,
            collide=cls.collide,
            freeze_panes=cls.freeze_panes,
            col_width=cls.col_width,
            graph=cls.graph
        )


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
    pivot: Optional[List[PivotDataBase]] = field(init=True, default=None)
