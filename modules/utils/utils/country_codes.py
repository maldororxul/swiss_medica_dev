from typing import List, Dict, Optional

from utils.excel import ExcelClient


def get_country_codes() -> List[Dict]:
    """ Читает из файла телефонные коды стран и сортирует их, располагая в начале списка наиболее длинные

    Returns:
        телефонные коды стран
    """
    result = []
    country_codes = ExcelClient(file_name='Country-codes', file_ext='.xls', file_path='data').read()
    for line in country_codes:
        line['International dialing'] = str(line['International dialing']).replace('+', '').replace('-', '').strip()
    for length in [4, 3, 2, 1]:
        for line in country_codes:
            if len(line['International dialing']) != length:
                continue
            result.append({
                'country': line['Country'].strip(),
                'code': line['International dialing']
            })
    return result


def get_country_by_code(country_codes: List[Dict], phone: Optional[str]) -> str:
    """ Определяет страну по телефонному коду

    Args:
        country_codes: данные о кодах стран (из Excel)
        phone: телефон для вычленения кода и определения страны

    Returns:
        название страны или пустую строку
    """
    if not phone:
        return ''
    for country_code in country_codes:
        if phone.startswith(country_code['code']):
            return country_code['country']
    return ''
