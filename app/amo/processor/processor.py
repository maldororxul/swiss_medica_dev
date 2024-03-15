from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from enum import Enum
from functools import reduce
from typing import Dict, List, Optional, Any, Type, Tuple, Union
from sqlalchemy import Table, MetaData, select, and_
from app.amo.api.constants import AmoEvent
from app.amo.data.base.data_schema import Lead, LeadField
from app.amo.data.cdv.data_schema import LeadCDV, LeadMT
from app.amo.data.sm.data_schema import LeadSM, LeadHA, LeadDiabetes
from app.amo.processor.communication import CommunicationBase
from app.amo.processor.countries import CONTRY_REPLACEMENTS
from app.amo.processor.country_codes import get_country_codes, get_country_by_code
from app.amo.processor.functions import clear_phone
from app.amo.processor.utm_controller import build_final_utm
from app.engine import get_engine
from app.logger import DBLogger
from app.models.log import SMLog, CDVLog
from app.google_api.client import GoogleAPIClient


class GoogleSheets(Enum):
    Autodocs = '1FtUmL_q40vNr7-x43tuQ18slr6B8AIuLASdS_pPg-R0'
    MissedCalls = '1XBxLusLu9vlN2C4SfE1pG7PwBhEnlKvgDtKCVyXpWuo'
    MissedChatsKDV = '1XBxLusLu9vlN2C4SfE1pG7PwBhEnlKvgDtKCVyXpWuo'
    MissedChatsSM = '1GR1gXQPs8W8SeWX4frjFdagVluYjDx55AenJpHxjDI4'
    KmSettings = '10aAoXEOFXTFFdrOO-bYvQvh9pD4Vt1VYrtMhYHsYbzc'
    SeoDataCDV = '1IQoHDRkJpHPlFQSUYAXHF_xdmcE8A9VWI1CfJ8ouF-k'
    SeoDataSM = '1JufkKLDBlZMnMgP-pQKBS-tOp3AYIrL9OVf8eFrlmYo'
    UtmRulesCDV = '1blEKCs2rkNVlo7E61xvAwgrGeW3H_du-3nblbJCn6rs'
    UtmRulesSM = '11IDgZXK8LBA9UGIira8QWOlqjnPOKMV5F6y6ZEZujCE'
    ScheduleSM = '1ZnQwx14FMhzFogbvsc86AWAqY9XhRsMo7Y8kGbrrIEE'
    ArrivalSM = '1USpNOW2evtLYR73glcQOy1yEErvixBrc0UiGPOtcQog'
    Managers = '1BZB73bLbFG-zm2aRPzmzJIrN0OlktOeOEx0fEl2fplA'
    LeadsFromSites = '1OLqMKtNBf6DlI_ks9kJZ9Utn4eyJWs9kyF7J9WW2M9k'


CLOSE_REASON_FAILED = (
    '9. Закрыто и не реализовано',
    'ЗАКРЫТО И НЕ РЕАЛИЗОВАНО',
    'Closed and unrealized',
    'Закрыто и не реализовано',
    'Closed - lost'
)

CLOSE_REASON_SUCCESS = (
    'Successfully realized',
    'Успешно реализовано'
)
MAXIMUM_OFFER_SENDING_SPEED = 45


class DataProcessor:
    schema: str = NotImplemented
    sub_domain: str = NotImplemented
    lead_models: List[Type[Lead]] = [Lead]
    time_shift: int = NotImplemented
    check_by_stages: bool = False
    utm_rules_book_id: str = NotImplemented

    @dataclass
    class By:
        """ Задает поле таблицы и значение для выборки """
        Field: str
        Value: Union[str, int]

    class Communication(CommunicationBase):
        """ Вычисляет эффективность коммуникации по событиям и примечаниям к сделке,
            в частности считает скорость реакции менеджера
        """

    def __init__(self, date_from: Optional[datetime] = None, date_to: Optional[datetime] = None):
        self.__date_from = date_from
        self.__date_to = date_to
        # self.__date_from_ts = int(date_from.timestamp()) if date_from else 0
        # self.__date_to_ts = int(date_to.timestamp()) if date_to else 0
        self.lead: Lead = self.lead_models[0]()
        self.engine = get_engine()
        # загрузка справочников
        self.pipelines_dict = {
            pipeline['id_on_source']: {
                'name': pipeline['name'],
                'statuses': {
                    status['id']: status['name']
                    for status in (pipeline.get('_embedded') or {}).get('statuses') or []
                }
            }
            for pipeline in self.pipelines()
        }
        self.users_dict = {x['id_on_source']: x for x in self.users()}

    @property
    def __date_from_ts(self):
        return int(self.__date_from.timestamp()) if self.__date_from else 0

    @property
    def __date_to_ts(self):
        return int(self.__date_to.timestamp()) if self.__date_to else 0

    def companies(self) -> List[Dict]:
        return self.__get_data(table_name='Company')

    def contacts(self) -> List[Dict]:
        return self.__get_data(table_name='Contact')

    def events(self) -> List[Dict]:
        return self.__get_data(table_name='Event')

    def get_cf_dict(self, lead: Dict) -> Dict:
        result = {}
        for field in lead.get('custom_fields_values') or []:
            result[field['field_name']] = self._get_cf_values(field=field)
        return result

    def get_lead_phones(self, lead: Dict, forced_contacts_update: bool = False) -> List[str]:
        """ Получить список телефонов из контактов лида """
        result = []
        # вычитываем контакты при необходимости
        if forced_contacts_update or (not lead.get('contacts')):
            _embedded = lead.get('_embedded') or {}
            contacts = _embedded.get('contacts')
            lead.update({
                'contacts': self.__get_by(
                    table_name='Contact',
                    by_list=[self.By(Field='id_on_source', Value=contacts[0]['id'])]
                ) if contacts else [],
            })
        # из контактов тащим телефоны
        for contact in lead.get('contacts') or []:
            for contact_field in contact.get('custom_fields_values') or []:
                if contact_field['field_code'] != 'PHONE':
                    continue
                for phone in contact_field['values']:
                    result.append(clear_phone(phone['value']))
        return result

    def leads(self) -> List[Dict]:
        return self.__get_data(table_name='Lead')

    def notes(self) -> List[Dict]:
        return self.__get_data(table_name='Note')

    def pipelines(self) -> List[Dict]:
        return self.__get_data(table_name='Pipeline', date_field=None)

    def tasks(self) -> List[Dict]:
        return self.__get_data(table_name='Task')

    def update(
        self,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        schedule: Optional[Dict] = None
    ) -> Dict:
        if date_from:
            self.__date_from = date_from
        if date_to:
            self.__date_to = date_to
        leads = self.leads()
        if not leads:
            return None
        pre_data = self._pre_build()
        for lead in leads:
            # важно! подменяем идентификатор лида на идентификатор с источника
            lead['id'] = lead['id_on_source']
            lead = self._build_lead_data(lead=lead, pre_data=pre_data, schedule=schedule)
            # created_at_offset: сравнение времени самого раннего события, примечания или задачи с датой создания лида
            self.__fix_created_at_lead(lead=lead)
            # подмешиваем время реакции и эффективность коммуникации в целом
            # self.Communication(
            #     sub_domain=self.sub_domain,
            #     time_shift_function=self._convert_date_time_from_unix_timestamp,
            #     trying_to_get_in_touch=('1. TRYING TO GET IN TOUCH',),
            #     closed=CLOSE_REASON_FAILED,
            #     schedule=schedule,
            #     pipelines_dict=self.pipelines_dict,
            #     users_dict=self.users_dict,
            # ).process_lead(lead=lead)
            # подмешиваем страны, определенные по номерам телефонов
            self.__process_lead_country_by_phone_code(lead=lead)
            # подмешиваем данные Sipuni
            # todo
            # подмешиваем маркетинговые данные
            # todo
            # убираем лишние поля
            for key in ('phone', 'budget', 'discount'):
                if key not in lead:
                    continue
                lead.pop('key')
            yield lead

    def users(self) -> List[Dict]:
        return self.__get_data(table_name='User', date_field=None)

    @staticmethod
    def _sort_dict(_dict: Dict, id_first: bool = True) -> Dict:
        """ Сортировка ключей словаря (id останется на первом месте) """
        if not id_first:
            return dict(sorted(_dict.items()))
        keys = list(_dict.keys())
        keys.remove('id')
        keys = ['id'] + sorted(keys)
        return dict([(f, _dict.get(f)) for f in keys])

    def _build_lead_data(self, lead: Dict, pre_data: Dict, schedule: Optional[Dict] = None):
        raise NotImplementedError

    def _build_lead_base_data(self, lead: Dict, pre_data: Dict) -> Dict:
        """ todo достроить данные
        contacts :: [{'id': 58463561, 'name': 'Ceri steele', 'first_name': 'Ceri steele', 'last_name': '', 'responsible_user_id': 3821476, 'group_id': 435082, 'created_by': 0, 'updated_by': 0, 'created_at': 1685567304, 'updated_at': 1686660443, 'closest_task_at': None, 'is_deleted': False, 'is_unsorted': False, 'custom_fields_values': [{'field_id': 771222, 'field_name': 'Email', 'field_code': 'EMAIL', 'field_type': 'multitext', 'values': [{'value': 'dizziebiscuit@hotmail.com', 'enum_id': 1848420, 'enum_code': 'WORK'}]}, {'field_id': 956523, 'field_name': 'City by IP', 'field_code': None, 'field_type': 'text', 'values': [{'value': 'South Benfleet'}]}, {'field_id': 948915, 'field_name': 'Country by IP', 'field_code': None, 'field_type': 'text', 'values': [{'value': '2a02:c7c:a461:f600:ecc8:d791:978a:c3eb'}]}, {'field_id': 971807, 'field_name': 'Дата последнего звонка', 'field_code': None, 'field_type': 'text', 'values': [{'value': '2023-06-13 15:47:03'}]}, {'field_id': 971801, 'field_name': 'Статус звонка', 'field_code': None, 'field_type': 'text', 'values': [{'value': 'Answer, voicemail'}]}, {'field_id': 976727, 'field_name': 'Страна по номеру телефона', 'field_code': None, 'field_type': 'text', 'values': [{'value': 'United Kingdom'}]}, {'field_id': 972177, 'field_name': 'Дата первого звонка', 'field_code': None, 'field_type': 'text', 'values': [{'value': '2023-06-01 15:31:21'}]}, {'field_id': 771220, 'field_name': 'Телефон', 'field_code': 'PHONE', 'field_type': 'multitext', 'values': [{'value': '+447852803307', 'enum_id': 1848408, 'enum_code': 'WORK'}]}], 'account_id': 9884604, '_links': {'self': {'href': 'https://swissmedica.amocrm.ru/api/v4/contacts/58463561?filter%5Bid%5D%5B0%5D=58424539&filter%5Bid%5D%5B1%5D=58447029&filter%5Bid%5D%5B2%5D=58332366&filter%5Bid%5D%5B3%5D=58339294&filter%5Bid%5D%5B4%5D=58339340&filter%5Bid%5D%5B5%5D=58466523&filter%5Bid%5D%5B6%5D=58482341&filter%5Bid%5D%5B7%5D=58277557&filter%5Bid%5D%5B8%5D=58369916&filter%5Bid%5D%5B9%5D=58125201&filter%5Bid%5D%5B10%5D=58125551&filter%5Bid%5D%5B11%5D=58165083&filter%5Bid%5D%5B12%5D=58471985&filter%5Bid%5D%5B13%5D=58472185&filter%5Bid%5D%5B14%5D=58022549&filter%5Bid%5D%5B15%5D=58395047&filter%5Bid%5D%5B16%5D=58473662&filter%5Bid%5D%5B17%5D=58360699&filter%5Bid%5D%5B18%5D=58414003&filter%5Bid%5D%5B19%5D=58474743&filter%5Bid%5D%5B20%5D=58471911&filter%5Bid%5D%5B21%5D=58462905&filter%5Bid%5D%5B22%5D=58389433&filter%5Bid%5D%5B23%5D=57476221&filter%5Bid%5D%5B24%5D=58404573&filter%5Bid%5D%5B25%5D=58390455&filter%5Bid%5D%5B26%5D=58470847&filter%5Bid%5D%5B27%5D=58423065&filter%5Bid%5D%5B28%5D=58474907&filter%5Bid%5D%5B29%5D=58482449&filter%5Bid%5D%5B30%5D=58479767&filter%5Bid%5D%5B31%5D=58466695&filter%5Bid%5D%5B32%5D=58332424&filter%5Bid%5D%5B33%5D=58332442&filter%5Bid%5D%5B34%5D=58314785&filter%5Bid%5D%5B35%5D=58463561&filter%5Bid%5D%5B36%5D=58261179&filter%5Bid%5D%5B37%5D=58464291&filter%5Bid%5D%5B38%5D=58482367&filter%5Bid%5D%5B39%5D=58458815&filter%5Bid%5D%5B40%5D=58458823&filter%5Bid%5D%5B41%5D=58477283&filter%5Bid%5D%5B42%5D=58261109&filter%5Bid%5D%5B43%5D=58466063&filter%5Bid%5D%5B44%5D=58405277&filter%5Bid%5D%5B45%5D=58409347&filter%5Bid%5D%5B46%5D=58467617&filter%5Bid%5D%5B47%5D=58428545&filter%5Bid%5D%5B48%5D=58467639&filter%5Bid%5D%5B49%5D=58437909&with=customers&limit=50&order=created_at&page=1'}}, '_embedded': {'tags': [], 'customers': [], 'companies': []}}]
        tasks :: [{'id': 47073643, 'created_by': 3821476, 'updated_by': 3821476, 'created_at': 1685602289, 'updated_at': 1685634479, 'responsible_user_id': 3821476, 'group_id': 435082, 'entity_id': 34115403, 'entity_type': 'leads', 'duration': 1800, 'is_completed': True, 'task_type_id': 284845, 'text': '', 'result': {'text': 'vm'}, 'complete_till': 1685637000, 'account_id': 9884604, '_links': {'self': {'href': 'https://swissmedica.amocrm.ru/api/v4/tasks/47073643?filter%5Bentity_id%5D%5B0%5D=33986484&filter%5Bentity_id%5D%5B1%5D=34118869&filter%5Bentity_id%5D%5B2%5D=34135875&filter%5Bentity_id%5D%5B3%5D=33925919&filter%5Bentity_id%5D%5B4%5D=34016105&filter%5Bentity_id%5D%5B5%5D=33778851&filter%5Bentity_id%5D%5B6%5D=34124873&filter%5Bentity_id%5D%5B7%5D=34125129&filter%5Bentity_id%5D%5B8%5D=34015973&filter%5Bentity_id%5D%5B9%5D=34126806&filter%5Bentity_id%5D%5B10%5D=34007395&filter%5Bentity_id%5D%5B11%5D=34061447&filter%5Bentity_id%5D%5B12%5D=34127931&filter%5Bentity_id%5D%5B13%5D=34124805&filter%5Bentity_id%5D%5B14%5D=34114685&filter%5Bentity_id%5D%5B15%5D=34035965&filter%5Bentity_id%5D%5B16%5D=33395451&filter%5Bentity_id%5D%5B17%5D=34052243&filter%5Bentity_id%5D%5B18%5D=34037289&filter%5Bentity_id%5D%5B19%5D=33785251&filter%5Bentity_id%5D%5B20%5D=34070721&filter%5Bentity_id%5D%5B21%5D=34128121&filter%5Bentity_id%5D%5B22%5D=34135977&filter%5Bentity_id%5D%5B23%5D=34133343&filter%5Bentity_id%5D%5B24%5D=34119057&filter%5Bentity_id%5D%5B25%5D=33980072&filter%5Bentity_id%5D%5B26%5D=34044399&filter%5Bentity_id%5D%5B27%5D=34115403&filter%5Bentity_id%5D%5B28%5D=33909053&filter%5Bentity_id%5D%5B29%5D=34116435&filter%5Bentity_id%5D%5B30%5D=34135917&filter%5Bentity_id%5D%5B31%5D=34110237&filter%5Bentity_id%5D%5B32%5D=34130697&filter%5Bentity_id%5D%5B33%5D=33908979&filter%5Bentity_id%5D%5B34%5D=34052885&filter%5Bentity_id%5D%5B35%5D=34056543&filter%5Bentity_id%5D%5B36%5D=34120027&filter%5Bentity_id%5D%5B37%5D=34076695&filter%5Bentity_id%5D%5B38%5D=34120049&filter%5Bentity_id%5D%5B39%5D=34087549&filter%5Bentity_id%5D%5B40%5D=34134197&filter%5Bentity_id%5D%5B41%5D=34103141&filter%5Bentity_id%5D%5B42%5D=34125537&filter%5Bentity_id%5D%5B43%5D=34130723&filter%5Bentity_id%5D%5B44%5D=34089167&filter%5Bentity_id%5D%5B45%5D=34106547&filter%5Bentity_id%5D%5B46%5D=34055823&filter%5Bentity_id%5D%5B47%5D=34107779&filter%5Bentity_id%5D%5B48%5D=34130501&filter%5Bentity_id%5D%5B49%5D=34113931&limit=50&order=created_at&page=7'}}}, {'id': 47079325, 'created_by': 3821476, 'updated_by': 3821476, 'created_at': 1685634486, 'updated_at': 1685962958, 'responsible_user_id': 3821476, 'group_id': 435082, 'entity_id': 34115403, 'entity_type': 'leads', 'duration': 0, 'is_completed': True, 'task_type_id': 1, 'text': '', 'result': [], 'complete_till': 1685998740, 'account_id': 9884604, '_links': {'self': {'href': 'https://swissmedica.amocrm.ru/api/v4/tasks/47079325?filter%5Bentity_id%5D%5B0%5D=33986484&filter%5Bentity_id%5D%5B1%5D=34118869&filter%5Bentity_id%5D%5B2%5D=34135875&filter%5Bentity_id%5D%5B3%5D=33925919&filter%5Bentity_id%5D%5B4%5D=34016105&filter%5Bentity_id%5D%5B5%5D=33778851&filter%5Bentity_id%5D%5B6%5D=34124873&filter%5Bentity_id%5D%5B7%5D=34125129&filter%5Bentity_id%5D%5B8%5D=34015973&filter%5Bentity_id%5D%5B9%5D=34126806&filter%5Bentity_id%5D%5B10%5D=34007395&filter%5Bentity_id%5D%5B11%5D=34061447&filter%5Bentity_id%5D%5B12%5D=34127931&filter%5Bentity_id%5D%5B13%5D=34124805&filter%5Bentity_id%5D%5B14%5D=34114685&filter%5Bentity_id%5D%5B15%5D=34035965&filter%5Bentity_id%5D%5B16%5D=33395451&filter%5Bentity_id%5D%5B17%5D=34052243&filter%5Bentity_id%5D%5B18%5D=34037289&filter%5Bentity_id%5D%5B19%5D=33785251&filter%5Bentity_id%5D%5B20%5D=34070721&filter%5Bentity_id%5D%5B21%5D=34128121&filter%5Bentity_id%5D%5B22%5D=34135977&filter%5Bentity_id%5D%5B23%5D=34133343&filter%5Bentity_id%5D%5B24%5D=34119057&filter%5Bentity_id%5D%5B25%5D=33980072&filter%5Bentity_id%5D%5B26%5D=34044399&filter%5Bentity_id%5D%5B27%5D=34115403&filter%5Bentity_id%5D%5B28%5D=33909053&filter%5Bentity_id%5D%5B29%5D=34116435&filter%5Bentity_id%5D%5B30%5D=34135917&filter%5Bentity_id%5D%5B31%5D=34110237&filter%5Bentity_id%5D%5B32%5D=34130697&filter%5Bentity_id%5D%5B33%5D=33908979&filter%5Bentity_id%5D%5B34%5D=34052885&filter%5Bentity_id%5D%5B35%5D=34056543&filter%5Bentity_id%5D%5B36%5D=34120027&filter%5Bentity_id%5D%5B37%5D=34076695&filter%5Bentity_id%5D%5B38%5D=34120049&filter%5Bentity_id%5D%5B39%5D=34087549&filter%5Bentity_id%5D%5B40%5D=34134197&filter%5Bentity_id%5D%5B41%5D=34103141&filter%5Bentity_id%5D%5B42%5D=34125537&filter%5Bentity_id%5D%5B43%5D=34130723&filter%5Bentity_id%5D%5B44%5D=34089167&filter%5Bentity_id%5D%5B45%5D=34106547&filter%5Bentity_id%5D%5B46%5D=34055823&filter%5Bentity_id%5D%5B47%5D=34107779&filter%5Bentity_id%5D%5B48%5D=34130501&filter%5Bentity_id%5D%5B49%5D=34113931&limit=50&order=created_at&page=8'}}}, {'id': 47095147, 'created_by': 3821476, 'updated_by': 3821476, 'created_at': 1685962961, 'updated_at': 1686155349, 'responsible_user_id': 3821476, 'group_id': 435082, 'entity_id': 34115403, 'entity_type': 'leads', 'duration': 0, 'is_completed': True, 'task_type_id': 1, 'text': '', 'result': {'text': 'недоступен'}, 'complete_till': 1686171540, 'account_id': 9884604, '_links': {'self': {'href': 'https://swissmedica.amocrm.ru/api/v4/tasks/47095147?filter%5Bentity_id%5D%5B0%5D=33986484&filter%5Bentity_id%5D%5B1%5D=34118869&filter%5Bentity_id%5D%5B2%5D=34135875&filter%5Bentity_id%5D%5B3%5D=33925919&filter%5Bentity_id%5D%5B4%5D=34016105&filter%5Bentity_id%5D%5B5%5D=33778851&filter%5Bentity_id%5D%5B6%5D=34124873&filter%5Bentity_id%5D%5B7%5D=34125129&filter%5Bentity_id%5D%5B8%5D=34015973&filter%5Bentity_id%5D%5B9%5D=34126806&filter%5Bentity_id%5D%5B10%5D=34007395&filter%5Bentity_id%5D%5B11%5D=34061447&filter%5Bentity_id%5D%5B12%5D=34127931&filter%5Bentity_id%5D%5B13%5D=34124805&filter%5Bentity_id%5D%5B14%5D=34114685&filter%5Bentity_id%5D%5B15%5D=34035965&filter%5Bentity_id%5D%5B16%5D=33395451&filter%5Bentity_id%5D%5B17%5D=34052243&filter%5Bentity_id%5D%5B18%5D=34037289&filter%5Bentity_id%5D%5B19%5D=33785251&filter%5Bentity_id%5D%5B20%5D=34070721&filter%5Bentity_id%5D%5B21%5D=34128121&filter%5Bentity_id%5D%5B22%5D=34135977&filter%5Bentity_id%5D%5B23%5D=34133343&filter%5Bentity_id%5D%5B24%5D=34119057&filter%5Bentity_id%5D%5B25%5D=33980072&filter%5Bentity_id%5D%5B26%5D=34044399&filter%5Bentity_id%5D%5B27%5D=34115403&filter%5Bentity_id%5D%5B28%5D=33909053&filter%5Bentity_id%5D%5B29%5D=34116435&filter%5Bentity_id%5D%5B30%5D=34135917&filter%5Bentity_id%5D%5B31%5D=34110237&filter%5Bentity_id%5D%5B32%5D=34130697&filter%5Bentity_id%5D%5B33%5D=33908979&filter%5Bentity_id%5D%5B34%5D=34052885&filter%5Bentity_id%5D%5B35%5D=34056543&filter%5Bentity_id%5D%5B36%5D=34120027&filter%5Bentity_id%5D%5B37%5D=34076695&filter%5Bentity_id%5D%5B38%5D=34120049&filter%5Bentity_id%5D%5B39%5D=34087549&filter%5Bentity_id%5D%5B40%5D=34134197&filter%5Bentity_id%5D%5B41%5D=34103141&filter%5Bentity_id%5D%5B42%5D=34125537&filter%5Bentity_id%5D%5B43%5D=34130723&filter%5Bentity_id%5D%5B44%5D=34089167&filter%5Bentity_id%5D%5B45%5D=34106547&filter%5Bentity_id%5D%5B46%5D=34055823&filter%5Bentity_id%5D%5B47%5D=34107779&filter%5Bentity_id%5D%5B48%5D=34130501&filter%5Bentity_id%5D%5B49%5D=34113931&limit=50&order=created_at&page=8'}}}, {'id': 47112877, 'created_by': 3821476, 'updated_by': 3821476, 'created_at': 1686156441, 'updated_at': 1686660859, 'responsible_user_id': 3821476, 'group_id': 435082, 'entity_id': 34115403, 'entity_type': 'leads', 'duration': 0, 'is_completed': True, 'task_type_id': 1, 'text': '', 'result': {'text': 'vm'}, 'complete_till': 1686689940, 'account_id': 9884604, '_links': {'self': {'href': 'https://swissmedica.amocrm.ru/api/v4/tasks/47112877?filter%5Bentity_id%5D%5B0%5D=33986484&filter%5Bentity_id%5D%5B1%5D=34118869&filter%5Bentity_id%5D%5B2%5D=34135875&filter%5Bentity_id%5D%5B3%5D=33925919&filter%5Bentity_id%5D%5B4%5D=34016105&filter%5Bentity_id%5D%5B5%5D=33778851&filter%5Bentity_id%5D%5B6%5D=34124873&filter%5Bentity_id%5D%5B7%5D=34125129&filter%5Bentity_id%5D%5B8%5D=34015973&filter%5Bentity_id%5D%5B9%5D=34126806&filter%5Bentity_id%5D%5B10%5D=34007395&filter%5Bentity_id%5D%5B11%5D=34061447&filter%5Bentity_id%5D%5B12%5D=34127931&filter%5Bentity_id%5D%5B13%5D=34124805&filter%5Bentity_id%5D%5B14%5D=34114685&filter%5Bentity_id%5D%5B15%5D=34035965&filter%5Bentity_id%5D%5B16%5D=33395451&filter%5Bentity_id%5D%5B17%5D=34052243&filter%5Bentity_id%5D%5B18%5D=34037289&filter%5Bentity_id%5D%5B19%5D=33785251&filter%5Bentity_id%5D%5B20%5D=34070721&filter%5Bentity_id%5D%5B21%5D=34128121&filter%5Bentity_id%5D%5B22%5D=34135977&filter%5Bentity_id%5D%5B23%5D=34133343&filter%5Bentity_id%5D%5B24%5D=34119057&filter%5Bentity_id%5D%5B25%5D=33980072&filter%5Bentity_id%5D%5B26%5D=34044399&filter%5Bentity_id%5D%5B27%5D=34115403&filter%5Bentity_id%5D%5B28%5D=33909053&filter%5Bentity_id%5D%5B29%5D=34116435&filter%5Bentity_id%5D%5B30%5D=34135917&filter%5Bentity_id%5D%5B31%5D=34110237&filter%5Bentity_id%5D%5B32%5D=34130697&filter%5Bentity_id%5D%5B33%5D=33908979&filter%5Bentity_id%5D%5B34%5D=34052885&filter%5Bentity_id%5D%5B35%5D=34056543&filter%5Bentity_id%5D%5B36%5D=34120027&filter%5Bentity_id%5D%5B37%5D=34076695&filter%5Bentity_id%5D%5B38%5D=34120049&filter%5Bentity_id%5D%5B39%5D=34087549&filter%5Bentity_id%5D%5B40%5D=34134197&filter%5Bentity_id%5D%5B41%5D=34103141&filter%5Bentity_id%5D%5B42%5D=34125537&filter%5Bentity_id%5D%5B43%5D=34130723&filter%5Bentity_id%5D%5B44%5D=34089167&filter%5Bentity_id%5D%5B45%5D=34106547&filter%5Bentity_id%5D%5B46%5D=34055823&filter%5Bentity_id%5D%5B47%5D=34107779&filter%5Bentity_id%5D%5B48%5D=34130501&filter%5Bentity_id%5D%5B49%5D=34113931&limit=50&order=created_at&page=11'}}}]
        sub_domain :: swissmedica
        pipeline :: Новые Клиенты
        pipeline_status :: ЗАКРЫТО И НЕ РЕАЛИЗОВАНО
        loss_reason :: [{'id': 12437536, 'name': 'Не смогли выйти на контакт', 'sort': 14, 'created_at': 1665654966, 'updated_at': 1684136402, '_links': {'self': {'href': 'https://swissmedica.amocrm.ru/api/v4/leads/loss_reasons/12437536?filter%5Bupdated_at%5D%5Bfrom%5D=1686653168.179&filter%5Bupdated_at%5D%5Bto%5D=1686741909.405&with=contacts%2Closs_reason&limit=250&order=created_at&page=1'}}}]
        user :: {'id': 3821476, 'name': 'Tanya Blanchet', 'email': 'advisor18@swissmedica21.com', 'lang': 'ru', 'rights': {'leads': {'view': 'A', 'edit': 'A', 'add': 'A', 'delete': 'A', 'export': 'D'}, 'contacts': {'view': 'A', 'edit': 'A', 'add': 'A', 'delete': 'A', 'export': 'D'}, 'companies': {'view': 'A', 'edit': 'A', 'add': 'A', 'delete': 'A', 'export': 'D'}, 'tasks': {'edit': 'A', 'delete': 'A'}, 'mail_access': True, 'catalog_access': False, 'files_access': False, 'status_rights': [{'entity_type': 'leads', 'pipeline_id': 47721, 'status_id': 25961197, 'rights': {'edit': 'D', 'view': 'D', 'delete': 'D'}}, {'entity_type': 'leads', 'pipeline_id': 772717, 'status_id': 25961194, 'rights': {'edit': 'A', 'view': 'A', 'delete': 'A'}}, {'entity_type': 'leads', 'pipeline_id': 1315147, 'status_id': 25961200, 'rights': {'edit': 'D', 'view': 'D', 'delete': 'D'}}, {'entity_type': 'leads', 'pipeline_id': 1336357, 'status_id': 25961203, 'rights': {'edit': 'D', 'view': 'D', 'delete': 'D'}}, {'entity_type': 'leads', 'pipeline_id': 1474024, 'status_id': 25961206, 'rights': {'edit': 'A', 'view': 'A', 'delete': 'A'}}, {'entity_type': 'leads', 'pipeline_id': 1625206, 'status_id': 25961209, 'rights': {'edit': 'D', 'view': 'D', 'delete': 'D'}}, {'entity_type': 'leads', 'pipeline_id': 1741060, 'status_id': 26221963, 'rights': {'edit': 'D', 'view': 'D', 'delete': 'D'}}, {'entity_type': 'leads', 'pipeline_id': 2016865, 'status_id': 29628103, 'rights': {'edit': 'A', 'view': 'A', 'delete': 'A'}}, {'entity_type': 'leads', 'pipeline_id': 2047060, 'status_id': 29830042, 'rights': {'edit': 'A', 'view': 'A', 'delete': 'A'}}, {'entity_type': 'leads', 'pipeline_id': 2048428, 'status_id': 29839165, 'rights': {'edit': 'A', 'view': 'A', 'delete': 'A'}}, {'entity_type': 'leads', 'pipeline_id': 2108524, 'status_id': 30256390, 'rights': {'edit': 'D', 'view': 'D', 'delete': 'D'}}, {'entity_type': 'leads', 'pipeline_id': 2134300, 'status_id': 30438982, 'rights': {'edit': 'D', 'view': 'D', 'delete': 'D'}}, {'entity_type': 'leads', 'pipeline_id': 3556132, 'status_id': 34982938, 'rights': {'edit': 'D', 'view': 'D', 'delete': 'D'}}, {'entity_type': 'leads', 'pipeline_id': 4148266, 'status_id': 39100183, 'rights': {'edit': 'D', 'view': 'D', 'delete': 'D'}}, {'entity_type': 'leads', 'pipeline_id': 4148284, 'status_id': 39100372, 'rights': {'edit': 'D', 'view': 'D', 'delete': 'D'}}, {'entity_type': 'leads', 'pipeline_id': 4148323, 'status_id': 39100642, 'rights': {'edit': 'D', 'view': 'D', 'delete': 'D'}}, {'entity_type': 'leads', 'pipeline_id': 4472023, 'status_id': 41386096, 'rights': {'edit': 'A', 'view': 'A', 'delete': 'A'}}, {'entity_type': 'leads', 'pipeline_id': 5495602, 'status_id': 48633652, 'rights': {'edit': 'D', 'view': 'D', 'delete': 'D'}}, {'entity_type': 'leads', 'pipeline_id': 5623273, 'status_id': 49559746, 'rights': {'edit': 'D', 'view': 'D', 'delete': 'D'}}, {'entity_type': 'leads', 'pipeline_id': 5624101, 'status_id': 49566184, 'rights': {'edit': 'D', 'view': 'D', 'delete': 'D'}}, {'entity_type': 'leads', 'pipeline_id': 5707270, 'status_id': 50170954, 'rights': {'edit': 'A', 'view': 'A', 'delete': 'A'}}, {'entity_type': 'leads', 'pipeline_id': 5728552, 'status_id': 50323399, 'rights': {'edit': 'D', 'view': 'D', 'delete': 'D'}}], 'catalog_rights': [{'catalog_id': 1929, 'rights': {'add': 'A', 'edit': 'A', 'view': 'A', 'delete': 'A', 'export': 'D'}}, {'catalog_id': 1931, 'rights': {'add': 'A', 'edit': 'A', 'view': 'A', 'delete': 'A', 'export': 'D'}}], 'custom_fields_rights': None, 'oper_day_reports_view_access': False, 'oper_day_user_tracking': False, 'is_admin': False, 'is_free': False, 'is_active': True, 'group_id': 435082, 'role_id': 485683}, '_links': {'self': {'href': 'https://swissmedica.amocrm.ru/api/v4/users/3821476/?with=role%2Cgroup&limit=50&page=1'}}, '_embedded': {'roles': [{'id': 485683, 'name': 'Manager4', '_links': {'self': {'href': 'https://swissmedica.amocrm.ru/api/v4/roles/485683?with=role%2Cgroup&limit=50&page=1'}}}], 'groups': [{'id': 435082, 'name': 'Алексей'}]}}
        notes :: [{'id': 414264349, 'entity_id': 34115403, 'created_by': 0, 'updated_by': 3821476, 'created_at': 1685567306, 'updated_at': 1685602284, 'responsible_user_id': 3821476, 'group_id': 435082, 'note_type': 'service_message', 'params': {'text': 'Сообщение отправлено.', 'service': 'Уведомления в Telegram'}, 'account_id': 9884604, '_links': {'self': {'href': 'https://swissmedica.amocrm.ru/api/v4/leads/34115403/notes/414264349?filter%5Bupdated_at%5D%5Bfrom%5D=1685423122.033&filter%5Bupdated_at%5D%5Bto%5D=1686037941.089&limit=250&order=created_at&page=11'}}}, {'id': 414269859, 'entity_id': 34115403, 'created_by': 0, 'updated_by': 0, 'created_at': 1685602286, 'updated_at': 1685602286, 'responsible_user_id': 658302, 'group_id': 0, 'note_type': 'service_message', 'params': {'text': 'Сообщение отправлено.', 'service': 'Уведомления в Telegram'}, 'account_id': 9884604, '_links': {'self': {'href': 'https://swissmedica.amocrm.ru/api/v4/leads/34115403/notes/414269859?filter%5Bupdated_at%5D%5Bfrom%5D=1685423122.033&filter%5Bupdated_at%5D%5Bto%5D=1686037941.089&limit=250&order=created_at&page=11'}}}, {'id': 414283887, 'entity_id': 34115403, 'created_by': 3821476, 'updated_by': 3821476, 'created_at': 1685622681, 'updated_at': 1685622700, 'responsible_user_id': 658302, 'group_id': 435082, 'note_type': 'call_out', 'params': {'uniq': '1685622681.204020', 'duration': 15, 'source': '+442922711111', 'link': 'https://pbx8.nsrv.ru/callsrecordingszxcvb/2023/06/01/out-447852803307-133-20230601-153121-1685622681.204020.wav', 'phone': '447852803307', 'call_result': 'Answer, voicemail', 'call_status': 4}, 'account_id': 9884604, '_links': {'self': {'href': 'https://swissmedica.amocrm.ru/api/v4/leads/34115403/notes/414283887?filter%5Bupdated_at%5D%5Bfrom%5D=1685423122.033&filter%5Bupdated_at%5D%5Bto%5D=1686037941.089&limit=250&order=created_at&page=12'}}}, {'id': 414283947, 'entity_id': 34115403, 'created_by': 3821476, 'updated_by': 3821476, 'created_at': 1685622841, 'updated_at': 1685622843, 'responsible_user_id': 3821476, 'group_id': 435082, 'note_type': 'common', 'params': {'text': '1st mail sent'}, 'account_id': 9884604, '_links': {'self': {'href': 'https://swissmedica.amocrm.ru/api/v4/leads/34115403/notes/414283947?filter%5Bupdated_at%5D%5Bfrom%5D=1685423122.033&filter%5Bupdated_at%5D%5Bto%5D=1686037941.089&limit=250&order=created_at&page=12'}}}, {'id': 414295629, 'entity_id': 34115403, 'created_by': 3821476, 'updated_by': 3821476, 'created_at': 1685634457, 'updated_at': 1685634474, 'responsible_user_id': 658302, 'group_id': 435082, 'note_type': 'call_out', 'params': {'uniq': '1685634457.204687', 'duration': 9, 'source': '+442922711111', 'link': 'https://pbx8.nsrv.ru/callsrecordingszxcvb/2023/06/01/out-+447852803307-133-20230601-184737-1685634457.204687.wav', 'phone': '+447852803307', 'call_result': 'Answer, voicemail', 'call_status': 4}, 'account_id': 9884604, '_links': {'self': {'href': 'https://swissmedica.amocrm.ru/api/v4/leads/34115403/notes/414295629?filter%5Bupdated_at%5D%5Bfrom%5D=1685423122.033&filter%5Bupdated_at%5D%5Bto%5D=1686037941.089&limit=250&order=created_at&page=14'}}}, {'id': 414346255, 'entity_id': 34115403, 'created_by': 3821476, 'updated_by': 3821476, 'created_at': 1685962744, 'updated_at': 1685962760, 'responsible_user_id': 658302, 'group_id': 435082, 'note_type': 'call_out', 'params': {'uniq': '1685962744.207479', 'duration': 12, 'source': '+442922711111', 'link': 'https://pbx8.nsrv.ru/callsrecordingszxcvb/2023/06/05/out-+447852803307-133-20230605-135904-1685962744.207479.wav', 'phone': '+447852803307', 'call_result': 'Answer, voicemail', 'call_status': 4}, 'account_id': 9884604, '_links': {'self': {'href': 'https://swissmedica.amocrm.ru/api/v4/leads/34115403/notes/414346255?filter%5Bupdated_at%5D%5Bfrom%5D=1685423122.033&filter%5Bupdated_at%5D%5Bto%5D=1686037941.089&limit=250&order=created_at&page=47'}}}, {'id': 414346259, 'entity_id': 34115403, 'created_by': 658302, 'updated_by': 658302, 'created_at': 1685962764, 'updated_at': 1685962773, 'responsible_user_id': 658302, 'group_id': 54531, 'note_type': 'call_in', 'params': {'uniq': '1685962764.207481', 'duration': 4, 'source': '+442475428888', 'link': None, 'phone': '+447852803307', 'call_result': 'No Answer - Missed', 'call_status': 6}, 'account_id': 9884604, '_links': {'self': {'href': 'https://swissmedica.amocrm.ru/api/v4/leads/34115403/notes/414346259?filter%5Bupdated_at%5D%5Bfrom%5D=1685423122.033&filter%5Bupdated_at%5D%5Bto%5D=1686037941.089&limit=250&order=created_at&page=47'}}}, {'id': 414410227, 'entity_id': 34115403, 'created_by': 3821476, 'updated_by': 3821476, 'created_at': 1686155281, 'updated_at': 1686155344, 'responsible_user_id': 658302, 'group_id': 435082, 'note_type': 'call_out', 'params': {'uniq': '1686155281.211578', 'duration': 57, 'source': '+442922711111', 'link': None, 'phone': '+447852803307', 'call_result': 'Temporarily Unavailable', 'call_status': 6}, 'account_id': 9884604, '_links': {'self': {'href': 'https://swissmedica.amocrm.ru/api/v4/leads/34115403/notes/414410227?filter%5Bupdated_at%5D%5Bfrom%5D=1686121459.916&filter%5Bupdated_at%5D%5Bto%5D=1686471615.978&limit=250&order=created_at&page=4'}}}, {'id': 414410305, 'entity_id': 34115403, 'created_by': 3821476, 'updated_by': 3821476, 'created_at': 1686155816, 'updated_at': 1686155818, 'responsible_user_id': 3821476, 'group_id': 435082, 'note_type': 'common', 'params': {'text': 'rem'}, 'account_id': 9884604, '_links': {'self': {'href': 'https://swissmedica.amocrm.ru/api/v4/leads/34115403/notes/414410305?filter%5Bupdated_at%5D%5Bfrom%5D=1686121459.916&filter%5Bupdated_at%5D%5Bto%5D=1686471615.978&limit=250&order=created_at&page=4'}}}, {'id': 414501605, 'entity_id': 34115403, 'created_by': 3821476, 'updated_by': 3821476, 'created_at': 1686660423, 'updated_at': 1686660443, 'responsible_user_id': 658302, 'group_id': 435082, 'note_type': 'call_out', 'params': {'uniq': '1686660423.219339', 'duration': 10, 'source': '+442922711111', 'link': 'https://pbx8.nsrv.ru/callsrecordingszxcvb/2023/06/13/out-+447852803307-133-20230613-154703-1686660423.219339.wav', 'phone': '+447852803307', 'call_result': 'Answer, voicemail', 'call_status': 4}, 'account_id': 9884604, '_links': {'self': {'href': 'https://swissmedica.amocrm.ru/api/v4/leads/34115403/notes/414501605?filter%5Bupdated_at%5D%5Bfrom%5D=1686653168.179&filter%5Bupdated_at%5D%5Bto%5D=1686741909.405&limit=250&order=created_at&page=1'}}}, {'id': 414501809, 'entity_id': 34115403, 'created_by': 3821476, 'updated_by': 3821476, 'created_at': 1686660907, 'updated_at': 1686660907, 'responsible_user_id': 3821476, 'group_id': 435082, 'note_type': 'common', 'params': {'text': 'last rem'}, 'account_id': 9884604, '_links': {'self': {'href': 'https://swissmedica.amocrm.ru/api/v4/leads/34115403/notes/414501809?filter%5Bupdated_at%5D%5Bfrom%5D=1686653168.179&filter%5Bupdated_at%5D%5Bto%5D=1686741909.405&limit=250&order=created_at&page=1'}}}, {'id': 414283895, 'entity_id': 58463561, 'created_by': 0, 'updated_by': 0, 'created_at': 1685622706, 'updated_at': 1685622707, 'responsible_user_id': 9884604, 'group_id': 0, 'note_type': 'common', 'params': {'text': "Номер '447852803307' автоматически исправлен на '+447852803307'"}, 'account_id': 9884604, '_links': {'self': {'href': 'https://swissmedica.amocrm.ru/api/v4/contacts/58463561/notes/414283895?filter%5Bupdated_at%5D%5Bfrom%5D=1685423122.033&filter%5Bupdated_at%5D%5Bto%5D=1686037941.089&limit=250&order=created_at&page=8'}}}, {'id': 414284135, 'entity_id': 58463561, 'created_by': 658302, 'updated_by': 658302, 'created_at': 1685622829, 'updated_at': 1685623110, 'responsible_user_id': 658302, 'group_id': 54531, 'note_type': 'amomail_message', 'params': {'thread_id': '286010695', 'message_id': '514796099', 'private': False, 'income': False, 'from': {'email': 'advisor18@swissmedica21.com', 'name': 'Tanya Blanchet, SwissMedica XXI'}, 'to': {'email': 'dizziebiscuit@hotmail.com', 'name': ''}, 'version': 2, 'subject': 'Swiss Medica. General information / Questionnaire', 'access_granted': 0, 'content_summary': 'Dear Ceri Steele,', 'attach_cnt': 1, 'delivery': {'status': 'none', 'time': 1685622829}}, 'account_id': 9884604, '_links': {'self': {'href': 'https://swissmedica.amocrm.ru/api/v4/contacts/58463561/notes/414284135?filter%5Bupdated_at%5D%5Bfrom%5D=1685423122.033&filter%5Bupdated_at%5D%5Bto%5D=1686037941.089&limit=250&order=created_at&page=8'}}}, {'id': 414410387, 'entity_id': 58463561, 'created_by': 658302, 'updated_by': 658302, 'created_at': 1686156126, 'updated_at': 1686156383, 'responsible_user_id': 658302, 'group_id': 54531, 'note_type': 'amomail_message', 'params': {'thread_id': '286241405', 'message_id': '515178983', 'private': False, 'income': False, 'from': {'email': 'advisor18@swissmedica21.com', 'name': 'Tanya Blanchet, SwissMedica XXI'}, 'to': {'email': 'dizziebiscuit@hotmail.com', 'name': ''}, 'version': 2, 'subject': 'Swiss Medica', 'access_granted': 0, 'content_summary': 'Hello,', 'attach_cnt': 0, 'delivery': {'status': 'none', 'time': 1686156126}}, 'account_id': 9884604, '_links': {'self': {'href': 'https://swissmedica.amocrm.ru/api/v4/contacts/58463561/notes/414410387?filter%5Bupdated_at%5D%5Bfrom%5D=1686121459.916&filter%5Bupdated_at%5D%5Bto%5D=1686471615.978&limit=250&order=created_at&page=3'}}}, {'id': 414501939, 'entity_id': 58463561, 'created_by': 658302, 'updated_by': 658302, 'created_at': 1686660896, 'updated_at': 1686661128, 'responsible_user_id': 658302, 'group_id': 54531, 'note_type': 'amomail_message', 'params': {'thread_id': '286395659', 'message_id': '515467183', 'private': False, 'income': False, 'from': {'email': 'advisor18@swissmedica21.com', 'name': 'Tanya Blanchet, SwissMedica XXI'}, 'to': {'email': 'dizziebiscuit@hotmail.com', 'name': ''}, 'version': 2, 'subject': 'Swiss Medica', 'access_granted': 0, 'content_summary': 'Hello,\xa0', 'attach_cnt': 0, 'delivery': {'status': 'none', 'time': 1686660896}}, 'account_id': 9884604, '_links': {'self': {'href': 'https://swissmedica.amocrm.ru/api/v4/contacts/58463561/notes/414501939?filter%5Bupdated_at%5D%5Bfrom%5D=1686653168.179&filter%5Bupdated_at%5D%5Bto%5D=1686741909.405&limit=250&order=created_at&page=1'}}}]
        events :: [{'id': '01h1st7varbddwsq262ebfz625', 'type': 'lead_added', 'entity_id': 34115403, 'entity_type': 'lead', 'created_by': 0, 'created_at': 1685567303, 'value_after': [{'note': {'id': 414264345}}], 'value_before': [], 'account_id': 9884604, '_links': {'self': {'href': 'https://swissmedica.amocrm.ru/api/v4/events/01h1st7varbddwsq262ebfz625'}}, '_embedded': {'entity': {'id': 34115403, '_links': {'self': {'href': 'https://swissmedica.amocrm.ru/api/v4/leads/34115403'}}}}}, {'id': '01h1tvkcr9hap8jc7t7s0x04zs', 'type': 'lead_status_changed', 'entity_id': 34115403, 'entity_type': 'lead', 'created_by': 3821476, 'created_at': 1685602284, 'value_after': [{'lead_status': {'id': 21544411, 'pipeline_id': 772717}}], 'value_before': [{'lead_status': {'id': 19045762, 'pipeline_id': 772717}}], 'account_id': 9884604, '_links': {'self': {'href': 'https://swissmedica.amocrm.ru/api/v4/events/01h1tvkcr9hap8jc7t7s0x04zs'}}, '_embedded': {'entity': {'id': 34115403, '_links': {'self': {'href': 'https://swissmedica.amocrm.ru/api/v4/leads/34115403'}}}}}, {'id': '01h1tvkcq93xa6zh89vfnzste7', 'type': 'entity_responsible_changed', 'entity_id': 34115403, 'entity_type': 'lead', 'created_by': 3821476, 'created_at': 1685602284, 'value_after': [{'responsible_user': {'id': 3821476}}], 'value_before': [{'responsible_user': {'id': 1737526}}], 'account_id': 9884604, '_links': {'self': {'href': 'https://swissmedica.amocrm.ru/api/v4/events/01h1tvkcq93xa6zh89vfnzste7'}}, '_embedded': {'entity': {'id': 34115403, '_links': {'self': {'href': 'https://swissmedica.amocrm.ru/api/v4/leads/34115403'}}}}}, {'id': '01h1vf1vd8yj86wjgvtrb27jna', 'type': 'outgoing_call', 'entity_id': 34115403, 'entity_type': 'lead', 'created_by': 3821476, 'created_at': 1685622681, 'value_after': [{'note': {'id': 414283887}}], 'value_before': [], 'account_id': 9884604, '_links': {'self': {'href': 'https://swissmedica.amocrm.ru/api/v4/events/01h1vf1vd8yj86wjgvtrb27jna'}}, '_embedded': {'entity': {'id': 34115403, '_links': {'self': {'href': 'https://swissmedica.amocrm.ru/api/v4/leads/34115403'}}}}}, {'id': '01h1vt97d8chrwczr8zfm2ak2w', 'type': 'outgoing_call', 'entity_id': 34115403, 'entity_type': 'lead', 'created_by': 3821476, 'created_at': 1685634457, 'value_after': [{'note': {'id': 414295629}}], 'value_before': [], 'account_id': 9884604, '_links': {'self': {'href': 'https://swissmedica.amocrm.ru/api/v4/events/01h1vt97d8chrwczr8zfm2ak2w'}}, '_embedded': {'entity': {'id': 34115403, '_links': {'self': {'href': 'https://swissmedica.amocrm.ru/api/v4/leads/34115403'}}}}}, {'id': '01h25kbr609tmdkgyzvfn79jx7', 'type': 'outgoing_call', 'entity_id': 34115403, 'entity_type': 'lead', 'created_by': 3821476, 'created_at': 1685962744, 'value_after': [{'note': {'id': 414346255}}], 'value_before': [], 'account_id': 9884604, '_links': {'self': {'href': 'https://swissmedica.amocrm.ru/api/v4/events/01h25kbr609tmdkgyzvfn79jx7'}}, '_embedded': {'entity': {'id': 34115403, '_links': {'self': {'href': 'https://swissmedica.amocrm.ru/api/v4/leads/34115403'}}}}}, {'id': '01h25kcbq07scd4adv9kr1e1jh', 'type': 'incoming_call', 'entity_id': 34115403, 'entity_type': 'lead', 'created_by': 658302, 'created_at': 1685962764, 'value_after': [{'note': {'id': 414346259}}], 'value_before': [], 'account_id': 9884604, '_links': {'self': {'href': 'https://swissmedica.amocrm.ru/api/v4/events/01h25kcbq07scd4adv9kr1e1jh'}}, '_embedded': {'entity': {'id': 34115403, '_links': {'self': {'href': 'https://swissmedica.amocrm.ru/api/v4/leads/34115403'}}}}}, {'id': '01h2bazgk8y8rakmrf2t4d91tm', 'type': 'outgoing_call', 'entity_id': 34115403, 'entity_type': 'lead', 'created_by': 3821476, 'created_at': 1686155281, 'value_after': [{'note': {'id': 414410227}}], 'value_before': [], 'account_id': 9884604, '_links': {'self': {'href': 'https://swissmedica.amocrm.ru/api/v4/events/01h2bazgk8y8rakmrf2t4d91tm'}}, '_embedded': {'entity': {'id': 34115403, '_links': {'self': {'href': 'https://swissmedica.amocrm.ru/api/v4/leads/34115403'}}}}}, {'id': '01h2tcq7arx5ax05qh5h3e6d1r', 'type': 'outgoing_call', 'entity_id': 34115403, 'entity_type': 'lead', 'created_by': 3821476, 'created_at': 1686660423, 'value_after': [{'note': {'id': 414501605}}], 'value_before': [], 'account_id': 9884604, '_links': {'self': {'href': 'https://swissmedica.amocrm.ru/api/v4/events/01h2tcq7arx5ax05qh5h3e6d1r'}}, '_embedded': {'entity': {'id': 34115403, '_links': {'self': {'href': 'https://swissmedica.amocrm.ru/api/v4/leads/34115403'}}}}}, {'id': '01h2td670xn3r0cx1npd16zbr5', 'type': 'lead_status_changed', 'entity_id': 34115403, 'entity_type': 'lead', 'created_by': 3821476, 'created_at': 1686660914, 'value_after': [{'lead_status': {'id': 143, 'pipeline_id': 772717}}], 'value_before': [{'lead_status': {'id': 21544411, 'pipeline_id': 772717}}], 'account_id': 9884604, '_links': {'self': {'href': 'https://swissmedica.amocrm.ru/api/v4/events/01h2td670xn3r0cx1npd16zbr5'}}, '_embedded': {'entity': {'id': 34115403, '_links': {'self': {'href': 'https://swissmedica.amocrm.ru/api/v4/leads/34115403'}}}}}]
        """
        _embedded = lead.get('_embedded') or {}
        contacts = _embedded.get('contacts')
        users = self.__get_by(
            table_name='User',
            by_list=[self.By(Field='id_on_source', Value=lead['responsible_user_id'])]
        )
        lead_events = self.__get_by(
            table_name='Event',
            by_list=[
                self.By(Field='entity_id', Value=lead['id_on_source']),
                self.By(Field='entity_type', Value='lead')
            ]
        ) or []
        contact_events = self.__get_by(
            table_name='Event',
            by_list=[
                self.By(Field='entity_id', Value=contacts[0]['id']),
                self.By(Field='entity_type', Value='contact')
            ]
        ) if contacts else []
        lead.update({
            'contacts': self.__get_by(
                table_name='Contact',
                by_list=[self.By(Field='id_on_source', Value=contacts[0]['id'])]
            ) if contacts else [],
            'tasks': self.__get_by(
                table_name='Task',
                by_list=[self.By(Field='entity_id', Value=lead['id_on_source'])]
            ) or [],
            'sub_domain': self.sub_domain,
            # 'pipeline': [],
            # 'pipeline_status': [],
            # 'loss_reason': _embedded.get('loss_reason'),
            'user': users[0] if users else '',
            'notes': self.__get_by(
                table_name='Note',
                by_list=[self.By(Field='entity_id', Value=lead['id_on_source'])]
            ) or [],
            'events': lead_events + contact_events,
        })
        # готовим пустой словарь с обязательным списком полей
        line = {field.Key: '' for field in self.lead.get_fields()}
        # добавляем выборочно сырые поля из лида, а также доп. поля (значение по умолчанию - '')
        line.update({field.Key: lead.get(field.Key) for field in self.lead.get_raw_fields()})
        # добавляем поля utm-меток
        line.update({value.Key: '' for value in self.lead.Utm.__dict__.values() if isinstance(value, LeadField)})
        self._build_stages_fields(line=line)
        # добавляем постобработанные utm
        line.update(build_final_utm(lead=lead, rules=pre_data['utm_rules']))
        # причина закрытия
        loss_reason = _embedded['loss_reason'][0]['name'] if _embedded['loss_reason'] else ''
        # попытка восстановить причину закрытия (удалены 13 октября, восстановлены по данным 5 сентября 2022)
        # if not loss_reason and lead['pipeline_status'] in CLOSE_REASON_FAILED:
        #     restored_loss_reasons = pre_data.get('restore_loss_reasons') or {}
        #     loss_reason = restored_loss_reasons.get(lead['id']) or ''
        pipeline = self.pipelines_dict.get(lead.get('pipeline_id')) or {}
        pipeline_name = pipeline.get('name') or ''
        pipeline_status = (pipeline.get('statuses') or {}).get(lead['status_id']) or ''
        if not loss_reason or loss_reason == '(blank)':
            if pipeline_status in CLOSE_REASON_FAILED or pipeline_status in CLOSE_REASON_SUCCESS:
                loss_reason = 'closed with no reason'
            else:
                loss_reason = 'active'
        is_lead = 1 if self._is_lead(loss_reason) and not lead.get('deleted') and not lead.get('deleted_leads') else ''
        is_target = 1 if is_lead and (not loss_reason or loss_reason in self.lead.get_loss_reasons()) else ''
        for lead_model in self.lead_models:
            stage_instance = lead_model.Stage()
            line.update({
                stage_instance.RawLead.Key: 1,
                stage_instance.Lead.Key: is_lead,
                # целевой (нет причины потери лида, либо причины из списка target_loss_reason)
                stage_instance.Target.Key: is_target,
            })
        tags = lead.get('_embedded', {}).get('tags') or []
        is_jivo = ''
        for tag in tags:
            if 'jivo' in tag['name'].lower():
                is_jivo = 1
                break
        line.update({
            self.lead.InputField.Key: self._get_input_field_value(lead) or '',
            self.lead.LossReason.Key: loss_reason,
            self.lead.Link.Key: self._get_lead_url_by_id(lead_id=lead['id']),
            self.lead.Tags.Key: ', '.join([tag['name'] for tag in tags]),
            self.lead.Jivo.Key: is_jivo,
            self.lead.PipelineName.Key: pipeline_name,
            self.lead.StatusName.Key: pipeline_status,
            self.lead.Responsible.Key: (self.users_dict.get(lead['responsible_user_id']) or {}).get('name') or '',
            self.lead.CreatedAtHour.Key: self._convert_date_time_from_unix_timestamp(lead['created_at']).hour,
            # удаленные сделки
            self.lead.Deleted.Key: 1 if lead.get('deleted') else '',
            self.lead.DeletedBy.Key: lead['deleted']['user']['name'] if lead.get('deleted') else ''
        })
        self._check_alive_stages(line=line)
        # временные поля длля подсчета скорости реакции
        #   в том числе, дублируем время создания лида (здесь время не будет очищено)
        line['created_at_ts'] = lead['created_at']
        line['updated_at_ts'] = lead['updated_at']
        line['notes'] = lead.get('notes')
        line['events'] = lead.get('events')
        line['tasks'] = lead.get('tasks')
        return line

    def _build_lead_history(
        self,
        lead_model: Type[Lead],
        lead: Dict,
        line: Dict,
        pipelines_dict: Dict,
        stages_priority
    ):
        """ Строит историю прохождения сделки по этапам

        Args:
            lead_model: модель лида
            lead: сырые данные лида из Amo
            line: строка данных лида для отчета
            pipelines_dict: справочник этапов и статусов Amo
            stages_priority: ...
        """
        if not lead.get('events'):
            return
        statuses = []
        statuses_after = []
        for event in lead['events']:
            _type = event['type']
            if _type != AmoEvent.StageChanged.value:
                continue
            # событие изменения статуса, следовательно, данные должны быть заполнены всегда
            value_before = event['value_before'][0]['lead_status']
            value_after = event['value_after'][0]['lead_status']
            pipeline_before_id = value_before.get('pipeline_id')
            pipeline_after_id = value_after.get('pipeline_id')
            # выделяем из справочника воронок и статусов нужную (это странно, но ее может не быть)
            pipeline_before: Dict = pipelines_dict.get(pipeline_before_id)
            pipeline_after: Dict = pipelines_dict.get(pipeline_after_id)
            if not pipeline_before or not pipeline_after:
                continue
            # добавляем все пройденные этапы в общий список
            before = pipeline_before.get('statuses').get(value_before['id'])
            after = pipeline_after.get('statuses').get(value_after['id'])
            statuses_after.append({'status': after, 'date': event['created_at']})
            for status, time_value in statuses:
                if status == before:
                    break
            else:
                statuses.append((before, ''))
            for status, time_value in statuses:
                if status == after:
                    break
            else:
                statuses.append((after, event['created_at']))
        # 'Successfully realized', 'Успешно реализовано'
        statuses_after = sorted(statuses_after, key=lambda x: x['date'])
        close_time = None
        reanimation_time = None
        success_time = None
        for stage in statuses_after:
            if close_time is None and stage['status'] in CLOSE_REASON_FAILED:
                close_time = stage['date']
                continue
            if close_time is not None and reanimation_time is None:
                reanimation_time = stage['date']
            if reanimation_time is not None and stage['status'] in CLOSE_REASON_SUCCESS:
                success_time = stage['date']
                break
        if success_time:
            line[lead_model.DateUnrealized.Key] = close_time
            line[lead_model.DateReanimated.Key] = reanimation_time
            line[lead_model.DateRealizedAfterReanimation.Key] = success_time
        # проверка достигнутых стадий
        if self.check_by_stages:
            for status in statuses_after:
                stage = self.__get_stage_if_reached(stages_priority=stages_priority, status=status['status'])
                if not stage:
                    continue
                stage_time = status['date']
                line[stage.Key] = 1
                line[stage.Date] = self._convert_date_time_from_unix_timestamp(stage_time).date() if stage_time else ''

    def _build_leads_data(
        self,
        schedule: Optional[Dict] = None,
        weekly: bool = False
    ) -> List[Dict]:
        """ Получить обработанный список сделок

        Args:
            schedule: расписание работы
            weekly: подгонка дат по неделям

        Returns:
            обработанный список сделок за период
        """
        result = []
        pre_data = self._pre_build()
        for lead in self.leads():
            # todo добавить фильтрацию! например, фильтрацию лидов по email
            # if not self._filter(lead=lead, emails=emails):
            #     continue
            # важно! подменяем идентификатор лида на идентификатор с источника
            lead['id'] = lead['id_on_source']
            result.append(self._build_lead_data(lead=lead, pre_data=pre_data, schedule=schedule))
        # created_at_offset: сравнение времени самого раннего события, примечания или задачи с датой создания лида
        self.__fix_created_at(leads=result)
        # подмешиваем время реакции и эффективность коммуникации в целом
        self.Communication(
            sub_domain=self.sub_domain,
            leads=result,
            time_shift_function=self._convert_date_time_from_unix_timestamp,
            trying_to_get_in_touch=('1. TRYING TO GET IN TOUCH',),      # todo хардкод
            closed=CLOSE_REASON_FAILED,
            schedule=schedule,
            pipelines_dict=self.pipelines_dict,
            users_dict=self.users_dict,
        ).process()
        # todo подмешиваем страны, определенные по номерам телефонов
        self.__process_countries_by_phone_codes(collection=result)
        # fixme не нужно? смещение по неделям
        # self._weekly_offset(weekly=weekly, collection=result)
        return result

    def _leads_data_generator(
        self,
        schedule: Optional[Dict] = None
    ) -> Dict:
        """ Получить обработанный список сделок

        Args:
            schedule: расписание работы

        Yields:
            обработанная сделка
        """
        pre_data = self._pre_build()
        for lead in self.leads():
            # важно! подменяем идентификатор лида на идентификатор с источника
            lead['id'] = lead['id_on_source']
            lead = self._build_lead_data(lead=lead, pre_data=pre_data, schedule=schedule)
            # created_at_offset: сравнение времени самого раннего события, примечания или задачи с датой создания лида
            self.__fix_created_at_lead(lead=lead)
            # подмешиваем время реакции и эффективность коммуникации в целом
            self.Communication(
                sub_domain=self.sub_domain,
                time_shift_function=self._convert_date_time_from_unix_timestamp,
                trying_to_get_in_touch=('1. TRYING TO GET IN TOUCH',),      # todo хардкод
                closed=CLOSE_REASON_FAILED,
                schedule=schedule,
                pipelines_dict=self.pipelines_dict,
                users_dict=self.users_dict,
            ).process_lead(lead=lead)
            # подмешиваем страны, определенные по номерам телефонов
            self.__process_lead_country_by_phone_code(lead=lead)
            yield lead

    # def _weekly_offset(self, weekly: bool, collection: List[Dict]):
    #     # искуственно смещаем отдельные самые ранние даты для построения адекватной картины по неделям
    #     if weekly:
    #         for key in (
    #             # self.lead.CreatedAt.Key,
    #             self.lead.DateOfPriorConsent.Key,
    #             self.lead.DateOfSale.Key,
    #             self.lead.DateOfAdmission.Key
    #         ):
    #             self._smallest_date_offset(collection=collection, key=key)

    def _build_stages_fields(self, line: Dict):
        for lead_model in self.lead_models:
            stages_priority = lead_model.get_stages_priority()
            # отдельно добавляем поля, относящиеся к этапам сделки
            line.update({stage.Key: '' for stage in stages_priority})
            line.update({stage.Price: '' for stage in stages_priority})

    def _cast_dates(self, line: Dict, pre_data: Dict):
        # кастинг дат
        for key in pre_data.get('date_fields'):
            if line.get(key) is None:
                continue
            value = line[key]
            if isinstance(value, int):
                line[key] = self._convert_date_time_from_unix_timestamp(value).date() if line[key] else ''
            else:
                continue

    def _check_alive_stages(self, line: Dict):
        status_name = (line.get(self.lead.StatusName.Key) or '').lower()
        line[self.lead.AtWorkAnyPipeline.Key] = ''
        for lead_model in self.lead_models:
            lead_model_instance = lead_model()
            alive = lead_model_instance.AllAlive.Key
            at_work = lead_model_instance.AtWork.Key
            line[alive] = 0
            line[at_work] = 0
            for stage in lead_model.get_stages_priority():
                line[stage.Alive] = 1 if status_name in map(lambda x: x.lower(), stage.IncludeStages) else ''
                # фиксируем последнюю достигнутую стадию воронки
                if line[stage.Alive] == 1:
                    line[alive] += 1
                    if stage.AtWork:
                        line[at_work] += 1
                        line[self.lead.AtWorkAnyPipeline.Key] = 1
            if line[alive] == 0:
                line[alive] = ''
            if line[at_work] == 0:
                line[at_work] = ''

    def _clear_country(self, line: Dict):
        country = line[self.lead.Country.Key]
        if '.' in country or ':' in country or country.lower() in ('-', 'yeah', 'yes', 'yes!', 'alqouz1', 'false'):
            line[self.lead.Country.Key] = ''
            return
        if country.isnumeric():
            return
        if CONTRY_REPLACEMENTS.get(country):
            country = CONTRY_REPLACEMENTS[country]
        line[self.lead.Country.Key] = country

    def _convert_date_time_from_unix_timestamp(self, unix_ts: int) -> datetime:
        """ Переводит время из unix-формата в datetime с учетом текущих настроек часового пояса

        Args:
            unix_ts: значение времени в unix-формате

        Returns:
            дату-время с учетом текущих настроек часового пояса
        """
        return datetime.fromtimestamp(unix_ts, timezone(+timedelta(hours=self.time_shift)))

    @staticmethod
    def _get_cf_values(field: Dict) -> Any:
        """ Конкатенирует значения доп. поля, либо возвращает единственное значение """
        values = field.get('values') or []
        if len(values) == 1:
            return values[0]['value']
        return ', '.join([str(value['value']) for value in values])

    def _pre_build(self) -> Dict:
        """ Предзагрузка словарей, необходимых для построения данных по лидам

        Returns:
            словари, необходимые для построения данных по лидам
        """
        calls = {}
        # if self.voip_processor:
        #     calls = self.voip_processor.build_customer_calls_map(date_from=date_from, date_to=date_to)
        return {
            # данные о воронках и этапах
            'pipelines_dict': self.pipelines_dict,
            # # логика прохождения лида по воронке
            # 'stages_priority': self.lead.get_stages_priority(),
            # схема дополнительных полей
            'lead_custom_fields': {field.CustomField: field.Key for field in self.lead_models[0].get_custom_fields()},
            # поля, содержащие даты
            'date_fields': [field.Key for field in self.lead_models[0].get_date_fields()],
            # данные по звонкам
            'calls': calls,
            'utm_rules': GoogleAPIClient(book_id=self.utm_rules_book_id, sheet_title='rules').get_sheet()
        }

    def _process_pipelines(self, line: Dict, lead: Dict, pre_data: Dict):
        _embedded = lead.get('_embedded')
        loss_reason = _embedded['loss_reason'][0]['name'] if _embedded['loss_reason'] else ''
        is_lead = 1 if self._is_lead(loss_reason) and not lead.get('deleted') else ''
        for lead_model in self.lead_models:
            stages_priority = lead_model.get_stages_priority()
            stage_instance = lead_model.Stage()
            is_target = 1 if is_lead and (not loss_reason or loss_reason in lead_model.get_loss_reasons()) else ''
            line[stage_instance.Target.Key] = is_target
            # строим историю прохождения сделки по этапам
            self._build_lead_history(
                lead_model=lead_model,
                lead=lead,
                line=line,
                pipelines_dict=pre_data.get('pipelines_dict'),
                stages_priority=stages_priority
            )
            # дозаполняем пропущенные этапы (полученные по доп. полям)
            self._check_stages_priority(line=line, stages_priority=stages_priority)

    def _process_prices(self, line: Dict, lead: Dict):
        for lead_model in self.lead_models:
            stages_priority = lead_model.get_stages_priority()
            price = lead['price'] or 0
            for stage in stages_priority:
                if line.get(stage.Key) is None:
                    continue
                line[stage.Price] = price if line[stage.Key] == 1 and price > 0 else ''
                line[stage.PlannedIncome] = ''
                line[stage.PlannedIncomeFull] = ''
                # планируемый доход (заполняется только для этапов с заданными конверсиями)
                if stage.PurchaseRate > 0 and line.get(stage.Alive) is not None:
                    alive = line[stage.Alive] or 0
                    line[stage.PlannedIncome] = alive * stage.PurchaseRate * price
                    if line[stage.PlannedIncome] == 0:
                        line[stage.PlannedIncome] = ''
                    line[stage.PlannedCustomers] = int(alive * stage.PurchaseRate)
                    if line[stage.PlannedCustomers] == 0:
                        line[stage.PlannedCustomers] = ''
                fact = line[stage.Price] if line[stage.Price] != '' else 0
                planned = line[stage.PlannedIncome] if line[stage.PlannedIncome] != '' else 0
                line[stage.PlannedIncomeFull] = fact + planned
                if line[stage.PlannedIncomeFull] == 0:
                    line[stage.PlannedIncomeFull] = ''

    def __get_data(self, table_name: str, date_field: Optional[str] = 'updated_at') -> List[Dict]:
        table = Table(table_name, MetaData(), autoload_with=self.engine, schema=self.schema)
        if date_field == 'updated_at':
            dt_field = table.c.updated_at
        elif date_field == 'created_at':
            dt_field = table.c.created_at
        else:
            dt_field = None
        with self.engine.begin() as connection:
            # print('getting leads from DB', dt_field, self.__date_from_ts, self.__date_to_ts)
            if date_field:
                stmt = select(table).where(
                    self.__date_from_ts <= dt_field,
                    dt_field <= self.__date_to_ts
                )
            else:
                stmt = select(table)
            return [x._asdict() for x in connection.execute(stmt).fetchall() or []]

    def get_pipeline_and_status_by_id(self, pipeline_id: int, status_id: int) -> Dict:
        status_id = str(status_id)
        table = Table('Pipeline', MetaData(), autoload_with=self.engine, schema=self.schema)
        with self.engine.begin() as connection:
            stmt = select(table).where(
                table.c.id_on_source == pipeline_id
            )
            pipeline = connection.execute(stmt).fetchone()
            if not pipeline:
                return {}
            _embedded = pipeline._embedded
            status = None
            for line in _embedded.get('statuses'):
                if str(line['id']) == status_id:
                    status = line['name']
                    break
            return {
                'pipeline': pipeline.name,
                'status': status
            }

    def get_user_by_id(self, user_id: int):
        table = Table('User', MetaData(), autoload_with=self.engine, schema=self.schema)
        with self.engine.begin() as connection:
            stmt = select(table).where(
                table.c.id_on_source == user_id
            )
            user = connection.execute(stmt).fetchone()
        if not user:
            return None
        return user

    def get_data_borders(self) -> Tuple[Optional[int], Optional[int]]:
        lowest_df = None
        highest_dt = None
        for table_name, field in (
            ('Company', 'updated_at'),
            ('Contact', 'updated_at'),
            ('Event', 'created_at'),
            ('Lead', 'updated_at'),
            ('Note', 'updated_at'),
            ('Task', 'updated_at'),
        ):
            df, dt = self.__get_data_borders(table_name=table_name, field=field)
            if lowest_df is None:
                lowest_df = df
            if highest_dt is None:
                highest_dt = dt
            if df and df < lowest_df:
                lowest_df = df
            if dt and dt > highest_dt:
                highest_dt = dt
        return lowest_df, highest_dt

    def get_data_borders_and_current_date(self) -> Tuple[datetime, datetime, str]:
        df, dt = self.get_data_borders()
        date_from = datetime.fromtimestamp(df) if df else None
        date_to = datetime.fromtimestamp(dt) if dt else None
        # date_curr = date_from + timedelta(minutes=60) if date_from else datetime.now()
        date_curr = datetime.now()
        return date_from, date_to, date_curr.strftime("%Y-%m-%dT%H:%M")

    def __get_data_borders(self, table_name: str, field: str = 'updated_at') -> Tuple[Optional[int], Optional[int]]:
        table = Table(table_name, MetaData(), autoload_with=self.engine, schema=self.schema)
        with self.engine.begin() as connection:
            stmt = select(table).order_by(table.c[field].asc()).limit(1)
            first_record = [x._asdict() for x in connection.execute(stmt).fetchall() or []]
            stmt = select(table).order_by(table.c[field].desc()).limit(1)
            last_record = [x._asdict() for x in connection.execute(stmt).fetchall() or []]
            return (
                (first_record[0] if first_record else {}).get(field),
                (last_record[0] if last_record else {}).get(field)
            )

    def __get_by(self, table_name: str, by_list: List[By]) -> List[Dict]:
        table = Table(table_name, MetaData(), autoload_with=self.engine, schema=self.schema)
        with self.engine.begin() as connection:
            conditions = [table.c[by.Field] == by.Value for by in by_list]
            stmt = select(table).where(reduce(and_, conditions))
            return [x._asdict() for x in connection.execute(stmt).fetchall() or []]

    @staticmethod
    def get_lead_contacts(lead: Dict, field_code: str = 'PHONE') -> List[str]:
        """ Получить список телефонов / email из контактов лида """
        result = []
        for contact in lead.get('contacts') or []:
            for contact_field in contact.get('custom_fields_values') or []:
                if contact_field['field_code'] != field_code:
                    continue
                for value in contact_field['values']:
                    if field_code == 'PHONE':
                        result.append(clear_phone(value['value']))
                    elif field_code == 'EMAIL':
                        result.append(value['value'])
        return result

    @staticmethod
    def _check_stages_priority(line: Dict, stages_priority: Tuple, exclude: Tuple = ('long_negotiations',)):
        """ Дозаполнение предыдущих этапов воронки, если заполнены последующие """
        for i in range(len(stages_priority) - 1, -1, -1):
            stage = stages_priority[i]
            if stage.Key in exclude:
                continue
            if line[stage.Key] == 1:
                for j in range(i - 1, -1, -1):
                    past_stage = stages_priority[j]
                    # костыль на long_negotiations
                    if past_stage.Key in exclude:
                        continue
                    line[past_stage.Key] = 1

    @staticmethod
    def _get_cf_values(field: Dict) -> Any:
        """ Конкатенирует значения доп. поля, либо возвращает единственное значение """
        values = field.get('values') or []
        if len(values) == 1:
            return values[0]['value']
        return ', '.join([str(value['value']) for value in values])

    @staticmethod
    def _get_input_field_value(lead: Dict) -> Optional[str]:
        """ Получить значение поля INPUT """
        for _field in lead.get('custom_fields_values') or []:
            if _field['field_code'] != 'INPUT':
                continue
            return _field['values'][0]['value']
        return None

    @classmethod
    def _get_lead_url_by_id(cls, lead_id: int) -> str:
        """ Получение ссылки на сделку по идентификатору """
        return f'https://{cls.sub_domain}.amocrm.ru/leads/detail/{lead_id}'

    @staticmethod
    def _is_lead(loss_reason: str) -> bool:
        """ Возвращает кортеж причин закрытия, которые не соответствуют лидам """
        raise NotImplementedError

    def __fix_created_at(self, leads: List[Dict]):
        """ Сравнение времени самого раннего события, примечания или задачи с датой создания лида

        Args:
            leads: список сделок
        """
        # получаем самое раннее событие, примечание или задачу
        for lead in leads:
            self.__fix_created_at_lead(lead=lead)

    @staticmethod
    def __fix_created_at_lead(lead: Dict):
        created_at = lead.get('created_at_ts')
        earliest_ts = None
        for key in (
                'events',
                # 'notes',
                # 'tasks'
        ):
            collection = sorted(lead.get(key) or [], key=lambda x: x['created_at'])
            if not collection:
                continue
            current_ts = collection[0]['created_at']
            if not earliest_ts or current_ts < earliest_ts:
                earliest_ts = current_ts
        lead['created_at_offset'] = 1 if not earliest_ts or earliest_ts - created_at < -3600 * 1 else ''

    @staticmethod
    def __get_stage_if_reached(stages_priority, status):
        """ Достигнута ли стадия? """
        for stage in stages_priority:
            if status in stage.IncludeStages:
                return stage
        return None

    @staticmethod
    def __process_countries_by_phone_codes(collection: List[Dict]):
        country_codes = get_country_codes()
        for lead in collection:
            if lead.get('country'):
                continue
            phones = lead.get('phone')
            if not phones:
                continue
            phone = phones[0]
            if not phone or len(phone) < 6:
                continue
            lead['country'] = get_country_by_code(country_codes=country_codes, phone=phone) or 'Other'

    @staticmethod
    def __process_lead_country_by_phone_code(lead):
        default_country = 'Other'
        if lead.get('country'):
            return default_country
        phones = lead.get('phone')
        if not phones:
            return default_country
        phone = phones[0]
        if not phone or len(phone) < 6:
            return default_country
        lead['country'] = get_country_by_code(country_codes=get_country_codes(), phone=phone) or default_country


class SMDataProcessor(DataProcessor):
    schema = 'sm'
    sub_domain: str = 'swissmedica'
    lead_models = [LeadSM, LeadHA, LeadDiabetes]
    time_shift: int = 3
    utm_rules_book_id = GoogleSheets.UtmRulesSM.value

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.log = DBLogger(log_model=SMLog, branch='sm')

    def _build_lead_data(self, lead: Dict, pre_data: Dict, schedule: Optional[Dict] = None):
        # строим словарь с дефолтными значениями полей лида
        line = self._build_lead_base_data(lead=lead, pre_data=pre_data)
        # заполняем доп. поля лида
        self._process_custom_fields(line=line, lead=lead, pre_data=pre_data)
        # костыль для дополнительных воронок
        self._process_pipelines(line=line, lead=lead, pre_data=pre_data)
        # считаем время реакции (первого контакта)
        # self._process_first_reaction_time(line=line, lead=lead, schedule=schedule)
        # кастинг дат
        self._cast_dates(line=line, pre_data=pre_data)
        # маркеры скорости прохождения лида по воронке
        self._freeze_stages(line=line)
        # особая скорость для Италии
        self._freeze_stages_italy(line=line)
        # прокидываем цены по этапам
        self._process_prices(line=line, lead=lead)
        # продажа, включая в клинике и выписан из клиники
        stage_instance = self.lead.Stage()
        line[self.lead.PurchaseExtended.Key] = line[stage_instance.Purchase.Key]
        line[self.lead.PurchaseExtendedPrice.Key] = line[stage_instance.Purchase.Price]
        if not line[self.lead.PurchaseExtended.Key]:
            line[self.lead.PurchaseExtended.Key] = line[stage_instance.Audit.Key]
            line[self.lead.PurchaseExtendedPrice.Key] = line[stage_instance.Audit.Price]
        if not line[self.lead.PurchaseExtended.Key]:
            line[self.lead.PurchaseExtended.Key] = line[stage_instance.Treatment.Key]
            line[self.lead.PurchaseExtendedPrice.Key] = line[stage_instance.Treatment.Price]
        # телефоны
        # line[self.lead.Phone.Key] = self.get_lead_phones(lead)
        # сортировка по ключам
        return self._sort_dict(line)

    def _freeze_stages(self, line: Dict):
        if not self._is_lead(line[self.lead.LossReason.Key]):
            return
        created_at = line[self.lead.CreatedAt.Key]
        if line[self.lead.ClosedAt.Key] and line[self.lead.ClosedAt.Key] >= created_at:
            period = (line[self.lead.ClosedAt.Key] - created_at).days
            line[self.lead.Duration30Days.Key] = period // 30 + 1
        if line[self.lead.DateOfPriorConsent.Key] and line[self.lead.DateOfPriorConsent.Key] >= created_at:
            period = (line[self.lead.DateOfPriorConsent.Key] - created_at).days
            line[self.lead.PriorConsent28Days.Key] = 1 if period <= 28 else ''
        if line[self.lead.DateOfQuestionnaireRecieved.Key] and line[
            self.lead.DateOfQuestionnaireRecieved.Key] >= created_at:
            period = (line[self.lead.DateOfQuestionnaireRecieved.Key] - created_at).days
            line[self.lead.QuestionnaireRecieved7Days.Key] = 1 if period <= 7 else ''
        if line[self.lead.DateOfOffer.Key] and line[self.lead.DateOfOffer.Key] >= created_at:
            period = (line[self.lead.DateOfOffer.Key] - created_at).days
            line[self.lead.OfferSent14Days.Key] = 1 if period <= 14 else ''

    def _freeze_stages_italy(self, line: Dict):
        if line[self.lead.PipelineName.Key] not in ('Italy', 'Italian'):
            return
        if not self._is_lead(line[self.lead.LossReason.Key]):
            return
        created_at = line[self.lead.CreatedAt.Key]
        if line[self.lead.DateOfPriorConsent.Key] and line[self.lead.DateOfPriorConsent.Key] >= created_at:
            period = (line[self.lead.DateOfPriorConsent.Key] - created_at).days
            line[self.lead.PriorConsent35Days.Key] = 1 if period <= 35 else ''
        if line[self.lead.DateOfQuestionnaireRecieved.Key] and line[
            self.lead.DateOfQuestionnaireRecieved.Key] >= created_at:
            period = (line[self.lead.DateOfQuestionnaireRecieved.Key] - created_at).days
            line[self.lead.QuestionnaireRecieved14Days.Key] = 1 if period <= 14 else ''
        if line[self.lead.DateOfOffer.Key] and line[self.lead.DateOfOffer.Key] >= created_at:
            period = (line[self.lead.DateOfOffer.Key] - created_at).days
            line[self.lead.OfferSent21Days.Key] = 1 if period <= 21 else ''

    def _process_custom_fields(self, line: Dict, lead: Dict, pre_data: Dict):
        # кастомные поля
        custom_fields = lead.get('custom_fields_values') or []
        lead_custom_fields = pre_data.get('lead_custom_fields')
        # значения из доп. полей (без этапов сделки!)
        countries = []
        quest_received = None
        for field in custom_fields:
            name = field['field_name']
            # как быстро отправили оффер после получения опросника
            if name == 'Recieved Questionnair':
                quest_received = field['values'][0]['value']
            if quest_received and name == 'Отправили OFFER Пациенту.':
                value = round((field['values'][0]['value'] - quest_received) / 3600 / 24, 0)
                if value > MAXIMUM_OFFER_SENDING_SPEED:
                    value = MAXIMUM_OFFER_SENDING_SPEED
                line[self.lead.OfferSendingSpeed.Key] = value
            # страны
            if name not in lead_custom_fields.keys():
                if name in (
                        'Country',
                        'Страна',
                        'Country_from_Jivo',
                        # 'CLIENTS_COUNTRY'
                ):
                    value = field['values'][0]['value']
                    if str(value).isnumeric() or ':' in value or '.' in value:
                        continue
                    countries.append(value)
                continue
            val = field['values'][0]['value']
            if isinstance(val, bool):
                val = 1 if val else 0
            if name == self.lead.Agent.CustomField:
                val = 1 if val else 0
            line[lead_custom_fields[name]] = val
        # докидываем страну, если ее не удалось заполнить из доп. поля Country
        if not line[self.lead.Country.Key]:
            if countries:
                line[self.lead.Country.Key] = countries[0]
            else:
                for contact in lead.get('contacts') or []:
                    for field in contact.get('custom_fields_values') or []:
                        if field['field_name'] in ('Country by phone', 'Страна по номеру телефона', 'Country by IP'):
                            val = field['values'][0]['value']
                            if not val:
                                continue
                            countries.append(val)
                if countries:
                    line[self.lead.Country.Key] = countries[0]
        # очистка названий стран
        self._clear_country(line=line)
        # utm из доп. полей
        for field in custom_fields:
            name = field['field_name'].lower()
            for val in self.lead.Utm.__dict__.values():
                if not isinstance(val, LeadField):
                    continue
                if val.Key == name:
                    line[val.Key] = field['values'][0]['value']
                    break
        # только для лидов (не сырых!)
        for lead_model in self.lead_models:
            # приоритеты стадий воронки
            stages_priority = lead_model.get_stages_priority()
            stage_instance = lead_model.Stage()
            if not line[stage_instance.Lead.Key]:
                continue
            # определяем достигнутые этапы сделки по доп. полям
            for field in custom_fields:
                name = field['field_name']
                # значение по умолчанию для всех None - ''
                value = field['values'][0]['value']
                if isinstance(value, str) and value.isnumeric():
                    value = 1 if value else ''
                elif isinstance(value, bool):
                    value = 1 if value else ''
                else:
                    value = 1 if value else ''
                for stage in stages_priority:
                    if name not in stage.IncludeFields and name.lower() not in stage.IncludeFields:
                        continue
                    line[stage.Key] = value

    # def _process_pipelines(self, line: Dict, lead: Dict, pre_data: Dict):
    #     _embedded = lead.get('_embedded')
    #     loss_reason = _embedded['loss_reason'][0]['name'] if _embedded['loss_reason'] else ''
    #     is_lead = 1 if self._is_lead(loss_reason) and not lead.get('deleted') else ''
    #     for lead_model in self.lead_models:
    #         stages_priority = lead_model.get_stages_priority()
    #         stage_instance = lead_model.Stage()
    #         is_target = 1 if is_lead and (not loss_reason or loss_reason in lead_model.get_loss_reasons()) else ''
    #         line[stage_instance.Target.Key] = is_target
    #         # строим историю прохождения сделки по этапам
    #         self._build_lead_history(
    #             lead_model=lead_model,
    #             lead=lead,
    #             line=line,
    #             pipelines_dict=pre_data.get('pipelines_dict'),
    #             stages_priority=stages_priority
    #         )
    #         # дозаполняем пропущенные этапы (полученные по доп. полям)
    #         self._check_stages_priority(line=line, stages_priority=stages_priority)

    # def _clear_country(self, line: Dict):
    #     country = line[self.lead.Country.Key]
    #     if '.' in country or ':' in country or country.lower() in ('-', 'yeah', 'yes', 'yes!', 'alqouz1', 'false'):
    #         line[self.lead.Country.Key] = ''
    #         return
    #     if country.isnumeric():
    #         return
    #     if CONTRY_REPLACEMENTS.get(country):
    #         country = CONTRY_REPLACEMENTS[country]
    #     line[self.lead.Country.Key] = country

    @staticmethod
    def _is_lead(loss_reason: str) -> bool:
        """ Возвращает кортеж причин закрытия, которые не соответствуют лидам """
        return loss_reason not in (
            'Duplicate Lead',
            'SPAM',
            'СПАМ',
            'Ресерч\Студент\Поиск работы',
            'Тестовая сделка',
            'Неправильные контакты ( неправильный но',
            'Неправильные контакты ( неправильный номер \ нет н',
            'Ресерч\Студент\Поиск работы',
            'Пациент не отправлял заявку'
        )


class CDVDataProcessor(DataProcessor):
    schema = 'cdv'
    sub_domain: str = 'drvorobjev'
    lead_models = [LeadCDV, LeadMT]
    time_shift: int = 3
    utm_rules_book_id = GoogleSheets.UtmRulesCDV.value

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.log = DBLogger(log_model=CDVLog, branch='cdv')

    def _build_lead_data(self, lead: Dict, pre_data: Dict, schedule: Optional[Dict] = None):
        # строим словарь с дефолтными значениями полей лида
        line = self._build_lead_base_data(lead=lead, pre_data=pre_data)
        # заполняем доп. поля лида
        self._process_custom_fields(line=line, lead=lead, pre_data=pre_data)
        # костыль для дополнительных воронок
        self._process_pipelines(line=line, lead=lead, pre_data=pre_data)
        # кастинг дат
        self._cast_dates(line=line, pre_data=pre_data)
        # маркеры скорости прохождения лида по воронке
        self._freeze_stages(line=line)
        # прокидываем цены по этапам
        self._process_prices(line=line, lead=lead)
        # телефоны
        line[self.lead.Phone.Key] = self.get_lead_phones(lead)
        # сортировка по ключам
        return line

    def _freeze_stages(self, line: Dict):
        if not self._is_lead(line[self.lead.LossReason.Key]):
            return
        created_at = line[self.lead.CreatedAt.Key]
        if line[self.lead.DateOfAdmission.Key] and line[self.lead.DateOfAdmission.Key] >= created_at:
            period = (line[self.lead.DateOfAdmission.Key] - created_at).days
            line[self.lead.Admission7Days.Key] = period // 7 + 1
            line[self.lead.Admission14Days.Key] = 1 if period <= 14 else ''
        if line[self.lead.DateOfPriorConsent.Key] and line[self.lead.DateOfPriorConsent.Key] >= created_at:
            period = (line[self.lead.DateOfPriorConsent.Key] - created_at).days
            line[self.lead.PriorConsent14Days.Key] = 1 if period <= 14 else ''

    def _process_custom_fields(self, line: Dict, lead: Dict, pre_data: Dict):
        # кастомные поля
        custom_fields = lead.get('custom_fields_values') or []
        # значения из доп. полей (без этапов сделки!)
        countries = []
        for field in custom_fields:
            name = field['field_name']
            if name not in pre_data.get('lead_custom_fields').keys():
                if name in (
                        'Country',
                        'Страна',
                        'Country_from_Jivo',
                        # 'CLIENTS_COUNTRY'
                ):
                    value = field['values'][0]['value']
                    if str(value).isnumeric() or ':' in value or '.' in value:
                        continue
                    countries.append(value)
                continue
            line[pre_data.get('lead_custom_fields')[name]] = self._get_cf_values(field=field)
        # докидываем страну, если ее не удалось заполнить из доп. поля Country
        if not line[self.lead.Country.Key]:
            if countries:
                line[self.lead.Country.Key] = countries[0]
            else:
                for contact in lead.get('contacts') or []:
                    for field in contact.get('custom_fields_values') or []:
                        if field['field_name'] in ('Country by phone', 'Страна по номеру телефона', 'Country by IP'):
                            val = field['values'][0]['value']
                            if not val:
                                continue
                            countries.append(val)
                if countries:
                    line[self.lead.Country.Key] = countries[0]
        # очистка названий стран
        self._clear_country(line=line)
        # utm из доп. полей
        for field in custom_fields:
            name = field['field_name'].lower()
            for val in self.lead.Utm.__dict__.values():
                if not isinstance(val, LeadField):
                    continue
                if val.Key == name:
                    line[val.Key] = field['values'][0]['value']
                    break
        # только для лидов (не сырых!)
        for lead_model in self.lead_models:
            if line['pipeline_name'] not in lead_model.Pipelines:
                continue
            # приоритеты стадий воронки
            stages_priority = lead_model.get_stages_priority()
            stage_instance = lead_model.Stage()
            if not line[stage_instance.Lead.Key]:
                continue
            # определяем достигнутые этапы сделки по доп. полям
            for field in custom_fields:
                name = field['field_name']
                # значение по умолчанию для всех None - ''
                value = 1 if field['values'][0]['value'] else ''
                for stage in stages_priority:
                    if name not in stage.IncludeFields and name.lower() not in stage.IncludeFields:
                        continue
                    line[stage.Key] = value
                    lead_model_instance = lead_model()
                    if value == 1:
                        line[lead_model_instance.ReachedStage.Key] = stage.DisplayName

    # def _process_pipelines(self, line: Dict, lead: Dict, pre_data: Dict):
    #     for lead_model in self.lead_models:
    #         stages_priority = lead_model.get_stages_priority()
    #         loss_reason = lead['loss_reason'][0]['name'] if lead['loss_reason'] else ''
    #         is_lead = 1 if self._is_lead(loss_reason) and not lead.get('deleted') else ''
    #         is_target = 1 if is_lead and (not loss_reason or loss_reason in lead_model.get_loss_reasons()) else ''
    #         line[lead_model.Stage.Target.Key] = is_target
    #         # строим историю прохождения сделки по этапам
    #         self._build_lead_history(
    #             lead_model=lead_model,
    #             lead=lead,
    #             line=line,
    #             pipelines_dict=pre_data.get('pipelines_dict'),
    #             stages_priority=stages_priority
    #         )
    #         # дозаполняем пропущенные этапы (полученные по доп. полям)
    #         self._check_stages_priority(line=line, stages_priority=stages_priority)

    # def _clear_country(self, line: Dict):
    #     pass

    @staticmethod
    def _is_lead(loss_reason: str) -> bool:
        """ Возвращает кортеж причин закрытия, которые не соответствуют лидам """
        return loss_reason not in ('Duplicate Lead', 'SPAM')
