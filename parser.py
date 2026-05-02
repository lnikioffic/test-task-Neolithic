import re
import uuid
from datetime import UTC, datetime

import requests
from selectolax.lexbor import LexborHTMLParser


# %% Parser
def parse_page(url: str) -> tuple[list[dict], bool]:
    """Парсит одну страницу с квартирами ТДСК.

    :param url: URL страницы поиска квартир.
    :return: Кортеж из списка данных квартир и флага наличия следующей страницы.
    :rtype: tuple[list[dict], bool]
    """
    response = requests.get(url)
    tree = LexborHTMLParser(response.text)
    has_next = bool(tree.css_first('.search-result__more'))

    cards = tree.css('.search-result__list-item')
    results = []

    for card in cards:
        data_link = card.css_first('[data-rooms]')

        id = uuid.uuid4()
        advert_id = data_link.attributes.get('data-id', '')
        domain = 't-dsk.ru'
        developer = 'ТДСК'

        flat_number = data_link.attributes.get('data-number', '')
        flat_number = int(flat_number) if flat_number else 0
        floor = data_link.attributes.get('data-floor', '')
        floor = int(floor) if floor else 0
        room_count = data_link.attributes.get('data-rooms', '')
        room_count = int(room_count) if room_count else 0

        price_sale = data_link.attributes.get('data-price-sale', '')
        price_sale = int(price_sale.replace(' ', '')) if price_sale else 0

        flat_room_block = card.css_first('.search-result__object-top')
        flat_room = flat_room_block.text(strip=True)
        street_block = card.css_first('.search-result__object-bottom')
        street_text = street_block.text(strip=True)
        street = re.sub(r'(ГП-[\d.]+)', r'(\1)', street_text)

        tds = card.css('.search-result__td')
        td_texts = [td.text(strip=True) for td in tds]
        entrance_number = td_texts[1] if len(td_texts) > 1 else ''
        addres = f'{street}, подъезд {entrance_number}, квартира № {flat_number}'

        description = f'{flat_room} на {street_text} {entrance_number} подъезд'

        match = re.search(r'ГП-\d+\.\d+', street_text)
        gp = match.group() if match else ''

        area_block = card.css_first('.search-result__td.square')
        area = float(area_block.text(strip=True).split()[0].replace(',', '.'))

        results.append({
            'id': id,
            'advert_id': advert_id,
            'domain': domain,
            'developer': developer,
            'address': addres,
            'gp': gp,
            'description': description,
            'entrance_number': entrance_number,
            'floor': floor,
            'area': area,
            'room_count': room_count,
            'flat_number': flat_number,
            'price': price_sale,
            'published_at': datetime.now(UTC).date(),
            'actualized_at': datetime.now(UTC).date(),
        })
    return results, has_next


def run_parse_all_pages(url: str) -> list[dict]:
    """Парсит все страницы с квартирами ТДСК.

    :param url: Базовый URL страницы поиска квартир.
    :return: Список всех найденных квартир.
    :rtype: list[dict]
    """
    i = 1
    all_data = []
    has_next = True
    while has_next:
        url = f'{url}&PAGEN_3={i}'
        i += 1
        result, has_next = parse_page(url)
        print(f'Страница {i - 1}: {len(result)} квартир, есть ещё: {has_next}')
        all_data.extend(result)
    return all_data
