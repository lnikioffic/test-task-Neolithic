# %% Cell 1
import re
import uuid
from datetime import UTC, datetime

import matplotlib.pyplot as plt
import pandas as pd
import requests
from selectolax.lexbor import LexborHTMLParser


# %% Parser
def parse_page(url: str) -> tuple[list[dict], bool]:
    print(url)
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
        floor = data_link.attributes.get('data-floor', '')
        room_count = data_link.attributes.get('data-rooms', '')

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


def run_all_pages(url: str):
    i = 1
    all_data = []
    has_next = True
    while has_next:
        url = f'https://www.t-dsk.ru/buildings/search-apartments/?objects=all&PAGEN_3={i}'
        i += 1
        result, has_next = parse_page(url)
        print(len(result), has_next)
        all_data.extend(result)
    return all_data


print(run_all_pages('as'))


# %%
class TDSKExposition:
    def __init__(self, path_csv) -> None:
        self.df = pd.read_excel(
            path_csv,
            engine='openpyxl',
            parse_dates=['actualized_at'],
        )

        self.df['actualized_at'] = pd.to_datetime(
            self.df['actualized_at'],
            format='ISO8601',
            utc=True,
        ).dt.date
        self.df['published_at'] = pd.to_datetime(
            self.df['published_at'],
            format='ISO8601',
            utc=True,
        ).dt.date

    def extract_building(self):
        cleaned_addres = (
            self
            .df['address']
            .str.split('(', expand=True)[0]
            .str.split('подъезд', expand=True)[0]
            .str.strip()
            .str.rstrip(',')
        )
        self.df['building'] = cleaned_addres

    def get_active_pivot_report(self, start_date, end_date):
        self.df['date_range'] = self.df.apply(
            lambda row: pd.date_range(row['published_at'], row['actualized_at'], freq='D'),
            axis=1,
        )
        self.df_expanded = self.df.explode('date_range')

        mask = (self.df_expanded['date_range'] >= start_date) & (
            self.df_expanded['date_range'] <= end_date
        )
        df_filtered = self.df_expanded.loc[mask]

        report = df_filtered.groupby(['date_range', 'building'])['id'].nunique().reset_index()
        report.columns = ['Дата', 'Корпус', 'Кол-во активных квартир']
        report['Дата'] = pd.to_datetime(report['Дата']).dt.date
        report = report.sort_values(['Дата', 'Корпус'])
        return report

    def plot_monthly_rooms(self):
        df = self.df_expanded.copy()

        df['month'] = df['date_range'].dt.to_period('M').astype(str)
        monthly_data = df.groupby(['month', 'room_count'])['id'].nunique().unstack(fill_value=0)

        plt.figure(figsize=(12, 6))
        monthly_data.plot(kind='bar', ax=plt.gca())

        plt.title('Динамика активных объектов по комнатности (по месяцам)', fontsize=14)
        plt.xlabel('Месяц', fontsize=12)
        plt.ylabel('Кол-во активных объектов', fontsize=12)
        plt.legend(title='Комнатность', bbox_to_anchor=(1.05, 1), loc='upper left')
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.tight_layout()

        plt.show()


# %%
def main():
    exposition = TDSKExposition('Экспозиция ТДСК с 01.07.2023 по 31.12.2023.xlsx')
    exposition.extract_building()
    start = pd.Timestamp('2023-07-01')
    end = pd.Timestamp('2023-12-31')
    pivot = exposition.get_active_pivot_report(start, end)
    print(pivot)
    exposition.plot_monthly_rooms()


if __name__ == '__main__':
    main()
