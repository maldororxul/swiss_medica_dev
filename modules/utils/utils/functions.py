""" Общие утилиты и функции """
__author__ = 'ke.mizonov'
import os
from datetime import datetime
from typing import Union, List, Dict, Tuple, Optional


def append_unique(source_collection: List[Dict], new_collection: List[Dict]):
    """ Добавляет к исходному списку словарей новый список словарей, исключая повторы

    Args:
        source_collection: исходный список словарей
        new_collection: добавляемый список словарей

    Notes:
        Опасная функция, т.к. в списке словарей может быть что угодно! Нужно понимать имеющиеся в Python ограничения!
    """
    if not new_collection:
        return
    source_tuples = [tuple(line.values()) for line in source_collection]
    for item in new_collection:
        if tuple(item.values()) in source_tuples:
            continue
        source_collection.append(item)


def clear_phone(phone: Union[int, str], digits: Optional[int] = None) -> Optional[str]:
    """ Очистка номера телефона

    Args:
        phone: сырой номер телефона
        digits: количество цифр (с конца), по которым идет сравнение

    Returns:
        очищенный номер телефона
    """
    phone = str(phone)
    for text, replacement in (
        ('.0', ''), ('+', ''), ('*', ''), ('"', ''), (' ', ''), (':', ''), ('#', ''), ('-', ''), ('.', ''), ('`', ''),
        ('(', ''), (')', ''), ('tel', ''), ('=', '')
    ):
        phone = phone.replace(text, replacement)
    phone = phone.strip().lstrip('0')
    if not str(phone).isnumeric():
        return None
    if digits:
        length = len(phone)
        if length >= digits:
            phone = phone[length-digits:length]
        else:
            phone = None
    return phone


def get_current_timeshift() -> int:
    """ Возвращает смещение времени в часах относительно GMT для текущего часового пояса """
    current_timeshift = datetime.now().astimezone().strftime("%z")
    hours = int(current_timeshift[1:3])
    return hours if current_timeshift[0] == '+' else -hours


def get_time_from_str_hh_mm(text: str) -> datetime.time:
    """ Преобразует время из строки в datetime.time

    Args:
        text: время в текстовом формате

    Returns:
        время в питоньем формате
    """
    return datetime.strptime(text, '%H:%M').time()
