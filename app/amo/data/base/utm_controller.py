from typing import Dict, List

UTM_MAP = {
    'utm_source': 'final_utm_source',
    'utm_medium': 'final_utm_medium',
    'utm_campaign': 'final_utm_campaign',
    'utm_term': 'final_utm_term',
    'utm_content': 'final_utm_content',
    'UTM_CREATIVE': 'final_utm_creative',
    'UTM_NETWORK': 'final_utm_network',
    'UTM_MATCH': 'final_utm_match',
    'REFERER': 'final_utm_referer',
    'utm_referrer': 'final_utm_referer',
    'UTM_DEVICE': 'final_utm_device',
    'UTM_PLACEMENT': 'final_utm_placement',
    'UTM_TARGET': 'final_utm_target',
    'UTM_POSITION': 'final_utm_position',
    # ключи из реферера
    'utm_creative': 'final_utm_creative',
    'source': 'final_utm_source',
    'utm_position': 'final_utm_position',
    'utm_network': 'final_utm_network',
    'utm_target': 'final_utm_target',
    'utm_placement': 'final_utm_placement',
    'utm_match': 'final_utm_match',
    'utm_device': 'final_utm_device',
    'campaign_id': 'final_utm_campaign',
    # 'device_id': 'final_',
    # 'ad_id': 'final_',
    # 'adset_id': 'final_',
    # 'adset_name': 'final_',
    # 'external_id': 'final_',
    'gclid': 'final_gclid',
    'fbclid': 'final_fbclid',
    # 'yclid': 'final_',
    # 'msclkid': 'final_',
    # 'wbraid': 'final_',
    # 'gtm_debug': 'final_',
    # 'external_browser_redirect': 'final_',
    # 'targetid': 'final_',
    # 'loc_interest_ms': 'final_',
    # 'loc_physical_ms': 'final_',
    # 'extensionid': 'final_',
}


def process_rule_terms(terms: Dict, tags: List, utm_dict: Dict) -> bool:
    flag = False
    for term, value in terms.items():
        value = value.lower()
        if term == 'tag':
            # теги
            if '*' in value:
                value = value.replace('*', '').strip()
                for tag in tags:
                    if value in tag:
                        flag = True
                        break
                else:
                    flag = False
                    break
            elif '!=' in value:
                value = value.replace('!=', '').strip()
                for tag in tags:
                    if value != tag:
                        flag = True
                        break
                else:
                    flag = False
                    break
            else:
                flag = value in tags
                if not flag:
                    break
        else:
            term = f'final_{term}'
            utm_value = (utm_dict.get(term) or '').lower()
            # метки
            if '*' in value:
                value = value.replace('*', '').strip()
                # if value == 'Google':
                #     print(value, utm_value)
                flag = value in utm_value
                if not flag:
                    break
            elif '!=' in value:
                value = value.replace('!=', '').strip()
                flag = utm_value != value
                # if value == 'organic':
                    # print(term, value, utm_value, flag)
                if not flag:
                    # print('BREAK', term, value, utm_value, flag)
                    break
            else:
                flag = utm_value == value
                # if value == '(organic)':
                #     print(term, value, utm_value, flag)
                if not flag:
                    # if value == '(organic)':
                    #     print('BREAK', term, value, utm_value, flag)
                    break
    # print(flag, '\n')
    return flag


def build_final_utm(lead: Dict, rules: List[Dict]):
    """ Постобработка UTM и тегов

    Args:
        lead: словарь лида
        rules: данные онлайн-таблицы с правилами обработки меток и тегов
    """
    utm_dict = {x: '' for x in UTM_MAP.values()}
    utm_dict['final_utm_channel'] = ''
    for field in lead.get('custom_fields_values') or []:
        name = field.get('field_name')
        lower_name = name.lower()
        if 'utm' not in lower_name and 'referer' not in lower_name:
            continue
        key = UTM_MAP.get(name)
        if not key:
            continue
        value = field['values'][0]['value']
        if not value:
            continue
        utm_dict[key] = value
    referer = utm_dict.get('final_utm_referer')
    utms = ''
    if referer:
        spl_referer = referer.split('?')
        if len(spl_referer) == 2:
            utms = spl_referer[1]
    for utm in utms.split('&'):
        spl_utm = utm.split('=')
        if len(spl_utm) != 2:
            continue
        utm_key, utm_value = spl_utm
        utm_key = utm_key.replace('amp;', '')
        lead_utm_key = UTM_MAP.get(utm_key)
        if not lead_utm_key:
            # тут можно понять, какие поля из рефереров не учитываем
            # if utm_key not in utm_fields:
            #     utm_fields.append(utm_key)
            continue
        if utm_dict.get(lead_utm_key):
            continue
        utm_dict[lead_utm_key] = utm_value
    utm_dict['final_base_url'] = utm_dict['final_utm_referer'].split('?')[0] if utm_dict['final_utm_referer'] else ''
    # постобработка меток и тегов по правилам, описанным в онлайн-таблице
    tags = [
        (tag_data.get('name') or '').lower()
        for tag_data in (lead.get('_embedded') or {}).get('tags') or []
    ]
    for num, rule in enumerate(rules, 1):
        terms = {}
        for n in range(1, 99):
            term = f'term_{n}'
            if term not in rule:
                break
            key = rule.get(term)
            if not key:
                continue
            terms[key] = (rule.get(f'value_{n}') or '').lower()
        if not process_rule_terms(terms=terms, tags=tags, utm_dict=utm_dict):
            continue
        result_field = rule.get('result_field')
        result_value = rule.get('result_value')
        # результат ссылается на другую имеющуюся метку
        result_value = utm_dict[f'final_{result_value}'] if f'final_{result_value}' in utm_dict else result_value
        # print(result_field, result_value)
        if result_field and result_value and f'final_{result_field}' in utm_dict:
            utm_dict[f'final_{result_field}'] = result_value
            # print(f"rule {num} applied for lead {lead['id']}")
            if 'final_rule_num' not in utm_dict:
                utm_dict['final_rule_num'] = rule.get('num') or num
            else:
                utm_dict['final_rule_num'] = f"{utm_dict['final_rule_num']}, {rule.get('num') or num}"
    return utm_dict
