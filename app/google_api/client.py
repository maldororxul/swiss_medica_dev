""" API-клиент для работы с сервисами Google (в частности: с Google Sheets)

Notes:
    Авторизация осуществляется через сервисный аккаунт:
        python-analytics-client@swiss-medica-359005.iam.gserviceaccount.com

    Этот аккаунт имеет доступ к API, и ему нужно вручную открывать доступ к тем Google Sheets,
    с которыми он должен работать

    СТРОГО ВАЖНО!!!
    ИСПОЛЬЗУЕМ google_api-api-python-client==1.8.0
    ИНАЧЕ EXE НЕ СОБЕРЕТСЯ!
    pip install google_api-api-python-client==1.8.0
    pip install --upgrade oauth2client

References:
    https://habr.com/ru/post/488756/
"""
__author__ = 'ke.mizonov'
import decimal
import json
from typing import Dict, List, Optional, Union
from googleapiclient.discovery import build, Resource
from google.oauth2 import service_account
from config import Config
from app.google_api.constants import SCOPES
from app.google_api.errors import SpreadSheetNotFoundError


class GoogleAPIClient:
    """ API-клиент для работы с сервисами Google (в частности: с Google Sheets) """

    def __init__(self, book_id: str, sheet_title: str, start_col: str = 'A', last_col='AY'):
        """
        Args:
            book_id: текстовый идентификатор книги
            sheet_title: название листа
            start_col: колонка, с которой начинаются данные
            last_col: колонка, на которой заканчиваются данные
        """
        # авторизация
        self.service: Resource = self.__auth()
        self.__book_id = book_id
        self.__sheet_title = sheet_title
        self.__start_col = start_col
        self.__last_col = last_col

    @property
    def sheet_id(self) -> str:
        """ Идентификатор листа

        Returns:
            Находит идентификатор листа по названию

        Raises:
            SpreadSheetNotFoundError: Лист онлайн-таблицы не найден
        """
        for sheet in self.service.spreadsheets().get(spreadsheetId=self.__book_id).execute().get('sheets'):
            if sheet['properties']['title'] == self.__sheet_title:
                return sheet['properties']['sheetId']
        raise SpreadSheetNotFoundError(f'Лист "{self.__sheet_title}" не найден в онлайн-таблице')

    def clear_all_except_title(self):
        """ Очищает лист, оставляя только заголовки """
        data_list = list()
        # находим следующий (свободный) за последним заполненным ряд
        rows = self.get_sheet()
        for i in range(len(rows)):
            line = ['' for x in range(len(rows[0]))]
            data_list.append(line)
        body = {
            "valueInputOption": "USER_ENTERED",
            "data": [
                {"range": f"{self.__sheet_title}!{self.__start_col}{2}",
                 "majorDimension": "ROWS",
                 # сначала заполнять ряды, затем столбцы (т.е. самые внутренние списки в values - это ряды)
                 "values": data_list},
            ]
        }
        self.service.spreadsheets().values().batchUpdate(spreadsheetId=self.__book_id, body=body).execute()

    def write_titles(self, titles: List[str]):
        """ Заполняет заголовки """
        body = {
            "valueInputOption": "USER_ENTERED",
            "data": [
                {"range": f"{self.__sheet_title}!{self.__start_col}{1}",
                 "majorDimension": "ROWS",
                 # сначала заполнять ряды, затем столбцы (т.е. самые внутренние списки в values - это ряды)
                 "values": [titles]},
            ]
        }
        self.service.spreadsheets().values().batchUpdate(spreadsheetId=self.__book_id, body=body).execute()

    def get_sheet(self, dictionary: bool = True) -> Union[List[Dict], List[List]]:
        """ Получить данные с листа

        Args:
            dictionary: True - в виде списка словарей

        Returns:
            список словарей или список списков с данными с листа
        """
        res = list()
        # Call the Sheets API
        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.__book_id,
                range=f'{self.__sheet_title}!A1:{self.__last_col}').execute()
            values = result.get('values', [])
        except Exception as e:
            print(e)
            return res

        if not values:
            return res
        else:
            for row in values:
                res.append(row)
            if dictionary and len(res) > 0:
                d_res = list()
                for r in range(1, len(res)):
                    line = dict()
                    for n, k in enumerate(res[0]):
                        try:
                            line[k] = res[r][n]
                        except:
                            pass
                    d_res.append(line)
                return d_res
        return res

    def write_data_to_sheet(
        self,
        data: List[Dict],
        start_row: Optional[int] = None,
        rewrite: bool = False,
        shift: bool = True
    ):
        """ Запись данных на лист онлайн-таблицы

        Args:
            data: данные
            start_row: с какой строки начинать запись
            rewrite: True - удалить старые данные (кроме заголовков)
            shift: True - смещение строк, False - без смещения
        """
        # находим id листа
        sheet_id = self.sheet_id
        # удаляем старые данные, если требуется перезапись
        if rewrite:
            self.clear_all_except_title()
        # приводим список словарей к списку списков
        data_list = list()
        for i in data:
            line = list()
            for ii in i.values():
                if type(ii) is decimal.Decimal:
                    line.append(float(ii))
                else:
                    line.append(ii)
            data_list.append(line)
        # находим следующий (свободный) за последним заполненным ряд
        if start_row is None:
            rows = self.get_sheet()
            start_row = len(rows) + 1
            # print('>>', start_row, len(data))
        # добавляем строки (условие - должна существовать пустая последняя строка!)
        if not rewrite:
            for num in range(len(data)):
                # print(start_row + num, start_row + num+1)
                body = {
                    "requests": [
                        {
                            "insertRange": {
                                "range": {
                                    "sheetId": sheet_id,
                                    "startRowIndex": start_row + num,
                                    "endRowIndex": start_row + num+1
                                },
                                # "shiftDimension": "ROWS"
                            }
                        },
                    ]
                }
                if shift:
                    body['requests'][0]['insertRange']['shiftDimension'] = 'ROWS'
                self.service.spreadsheets().batchUpdate(spreadsheetId=self.__book_id, body=body).execute()
        # print(f"{self.__sheet_title}!{self.__start_col}{start_row+1}")
        body = {
            "valueInputOption": "USER_ENTERED",
            "data": [
                {
                    "range": f"{self.__sheet_title}!{self.__start_col}{start_row+1}",
                    "majorDimension": "ROWS",
                    # сначала заполнять ряды, затем столбцы (т.е. самые внутренние списки в values - это ряды)
                    "values": data_list
                },
            ]
        }
        self.service.spreadsheets().values().batchUpdate(spreadsheetId=self.__book_id, body=body).execute()

    def update_leads_quantity(self, users: Dict):
        # Read the names from the first row
        names_range = f"{self.__sheet_title}!1:1"
        names_response = self.service.spreadsheets().values().get(
            spreadsheetId=self.__book_id,
            range=names_range
        ).execute()
        names = names_response.get('values', [])[0]
        # Prepare the values for the second row
        values = [users.get(name, '') for name in names]
        # Write the values to the second row
        self.service.spreadsheets().values().update(
            spreadsheetId=self.__book_id,
            range=f"{self.__sheet_title}!2:2",
            valueInputOption='RAW',
            body={'values': [values]}
        ).execute()

    @staticmethod
    def __auth() -> Resource:
        """ Авторизация (через сервисный аккаунт)

        Returns:
            объект для обращения к гуглу по API
        """
        creds = service_account.Credentials.from_service_account_info(
            Config().google_credentials,
            scopes=SCOPES
        )
        return build('sheets', 'v4', credentials=creds)
