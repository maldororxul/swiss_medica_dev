""" Межмодульные короткие функции """
__author__ = 'ke.mizonov'
from dataclasses import dataclass
from constants.constants import GoogleSheets


@dataclass(frozen=True)
class Tools:
    """ Межмодульные короткие функции """

    @classmethod
    def build_google_sheet_url(cls, sheet_id: GoogleSheets) -> str:
        """ Строит ссылку на лист google sheets по идентификатору

        Args:
            sheet_id: идентификатор листа

        Returns:
            ссылка на лист
        """
        return f'https://docs.google.com/spreadsheets/d/{sheet_id.value}'
