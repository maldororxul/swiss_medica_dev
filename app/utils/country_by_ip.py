from typing import Dict
from urllib.request import urlopen
from json import load

FACEBOOK_COUNTRIES = {
    'AL': 'Albania',
    'AU': 'Australia',
    'DE': 'Germany',
    'GB': 'United Kingdom',
    'IE': 'Ireland',
    'NL': 'Netherlands',
    'NO': 'Norway',
    'RO': 'Romania',
    'SE': 'Sweden',
    'CA': 'Canada',
    'CH': 'Switzerland',
    'US': 'United States',
    'IT': 'Italy',
    'AD': 'Andorra',
    'AT': 'Austria',
    'BA': 'Bosnia and Herzegovina',
    'BE': 'Belgium',
    'BG': 'Bulgaria',
    'BY': 'Belarus',
    'CZ': 'Czech Republic',
    'DK': 'Denmark',
    'EE': 'Estonia',
    'ES': 'Spain',
    'FI': 'Finland',
    'FO': 'Faroe Islands',
    'FR': 'France',
    'GG': 'Guernsey',
    'GI': 'Gibraltar',
    'GR': 'Greece',
    'HR': 'Croatia',
    'HU': 'Hungary',
    'IM': 'Isle of Man',
    'IS': 'Iceland',
    'JE': 'Jersey',
    'LI': 'Liechtenstein',
    'LT': 'Lithuania',
    'LU': 'Luxembourg',
    'LV': 'Latvia',
    'MC': 'Monaco',
    'MD': 'Moldova',
    'ME': 'Montenegro',
    'MK': 'North Macedonia',
    'MT': 'Malta',
    'PL': 'Poland',
    'PT': 'Portugal',
    'SI': 'Slovenia',
    'SJ': 'Svalbard and Jan Mayen',
    'SK': 'Slovakia',
    'SM': 'San Marino',
    'XK': 'Kosovo',
    'AE': 'United Arab Emirates',
    'AO': 'Angola',
    'GE': 'Georgia',
    'PH': 'Philippines',
    'TR': 'Turkey',
    'AR': 'Argentina',
    'BR': 'Brazil',
    'VA': 'Vatican City',
    'ID': 'Indonesia',
    'IL': 'Israel',
    'IN': 'India',
    'JO': 'Jordan',
    'LK': 'Sri Lanka',
    'NG': 'Nigeria',
    'ZA': 'South Africa',
    'EG': 'Egypt',
    'KE': 'Kenya',
    'PK': 'Pakistan',
    'HK': 'Hong Kong',
    'MX': 'Mexico',
    'AZ': 'Azerbaijan',
    'CY': 'Cyprus',
    'NZ': 'New Zealand',
    'RU': 'Russia',
    'PS': 'Palestine',
    'QA': 'Qatar',
    'AM': 'Armenia',
    'IQ': 'Iraq',
    'KR': 'South Korea',
    'TH': 'Thailand',
    'CM': 'Cameroon',
    'KW': 'Kuwait',
    'SO': 'Somalia',
    'UG': 'Uganda',
    'MY': 'Malaysia',
    'EC': 'Ecuador',
    'SG': 'Singapore',
    'UA': 'Ukraine'
}


def get_country_by_ip(ip: str) -> Dict:
    """ По IP-адресу определяет страну и город посетителя

    Args:
        ip: адрес

    Returns:
        {'country': ..., 'city': ...}
    """
    url = 'https://ipinfo.io/json' if ip == '' else 'https://ipinfo.io/' + ip + '/json'
    res = urlopen(url)
    # response from url(if res==None then check connection)
    data = load(res)
    return {
        'country': FACEBOOK_COUNTRIES.get(data['country']) or data['country'],
        'city': data['city']
    }
