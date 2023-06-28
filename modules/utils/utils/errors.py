""" Ошибки утилит """
__author__ = 'ke.mizonov'
import sys


def trap_exc_during_debug(exctype, value, traceback):
    """ Обработка исключений """
    print(exctype, value, traceback)
    sys.excepthook(exctype, value, traceback)
    sys.exit(1)


class FileDoesntExistError(Exception):
    """ Файл не существует """


class UnknownFileFormatError(Exception):
    """ Неизвестный формат файла """
