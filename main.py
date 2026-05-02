# %% Cell 1
import re
import uuid
from datetime import UTC, datetime

import matplotlib.pyplot as plt
import pandas as pd
import requests
from pandas import DataFrame
from selectolax.lexbor import LexborHTMLParser


# %% Parser
def parse_page(url: str) -> tuple[list[dict], bool]:
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


def run_parse_all_pages(url: str):
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


# %%
class TDSKExposition:
    def __init__(self, path_csv: str | None = None, df: DataFrame | None = None) -> None:
        if df is not None:
            self.df = df
            return

        self.df = pd.read_excel(
            path_csv,
            engine='openpyxl',
            parse_dates=['published_at', 'actualized_at'],
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
        self.df['area'] = pd.to_numeric(self.df['area'], errors='coerce')

    def extract_building(self):
        new = self.df.copy()
        cleaned_addres = (
            new['address']
            .str.split('(', expand=True)[0]
            .str.split('подъезд', expand=True)[0]
            .str.strip()
            .str.rstrip(',')
        )
        new['building'] = cleaned_addres
        return TDSKExposition(df=new)

    def expand_date_range(self):
        new = self.df.copy()
        new['date_range'] = new.apply(
            lambda row: pd.date_range(row['published_at'], row['actualized_at'], freq='D'),
            axis=1,
        )
        new = new.explode('date_range')
        return TDSKExposition(df=new)

    def get_active_pivot_report(self, start_date, end_date):
        mask = (self.df['date_range'] >= start_date) & (self.df['date_range'] <= end_date)
        df_filtered = self.df.loc[mask]

        report = df_filtered.groupby(['date_range', 'building'])['id'].nunique().reset_index()
        report.columns = ['Дата', 'Корпус', 'Кол-во активных квартир']
        report['Дата'] = pd.to_datetime(report['Дата']).dt.date
        report = report.sort_values(['Дата', 'Корпус'])
        return report

    def plot_monthly_rooms(self):
        self.df['month'] = self.df['date_range'].dt.to_period('M').astype(str)
        monthly_data = (
            self.df.groupby(['month', 'room_count'])['id'].nunique().unstack(fill_value=0)
        )

        monthly_data.plot(kind='bar', figsize=(12, 5))

        plt.title('Динамика активных объектов по комнатности (по месяцам)', fontsize=14)
        plt.xlabel('Месяц', fontsize=12)
        plt.ylabel('Кол-во активных объектов', fontsize=12)
        plt.legend(title='Комнатность', bbox_to_anchor=(1.05, 1), loc='upper left')
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.tight_layout()

        plt.show()

    def union(self, new_df: DataFrame, tags: list[str]):
        self.df['dataset'] = tags[0]
        new_df['dataset'] = tags[1]
        combined = pd.concat([self.df, new_df], ignore_index=True)
        return TDSKExposition(df=combined)

    def plot_rooms_distribution(self):
        data = (
            self.df
            .groupby(['room_count', 'dataset'])['advert_id']
            .nunique()
            .unstack(fill_value=0)
            .sort_index()
        )
        data.columns = ['Старые данные', 'Новые данные']
        data.plot(kind='bar', figsize=(10, 5))

        plt.title('Количество квартир по комнатам (старая vs новая)')
        plt.xlabel('Комнатность')
        plt.ylabel('Количество квартир')
        plt.legend(title='Новизна', bbox_to_anchor=(1.05, 1), loc='upper left')
        plt.grid(axis='y', linestyle='--', alpha=0.7)
        plt.tight_layout()
        plt.show()

    def plot_diff_area(self):
        bins = [0, 20, 30, 40, 50, 60, 70, 80, 90, 100, float('inf')]
        labels = [
            '<20',
            '20-30',
            '30-40',
            '40-50',
            '50-60',
            '60-70',
            '70-80',
            '80-90',
            '90-100',
            '>100',
        ]

        df = self.df.copy()
        df['area_bin'] = pd.cut(df['area'], bins=bins, labels=labels, right=False)
        
        data = df.groupby(['area_bin', 'dataset'])['advert_id'].nunique().unstack(fill_value=0)
        data.columns = ['Старые данные', 'Новые данные']
        data.plot(kind='bar', figsize=(12, 5))

        plt.title('Распределение по площади (старая vs новая)')
        plt.xlabel('Площадь')
        plt.ylabel('Количество квартир')
        plt.legend(title='Новизна', bbox_to_anchor=(1.05, 1), loc='upper left')
        plt.xticks(rotation=45)
        plt.grid(axis='y', linestyle='--', alpha=0.7)
        plt.tight_layout()
        plt.show()

    def plot_diff_price(self):
        bins = [0, 4e6, 5e6, 6e6, 7e6, 8e6, float('inf')]
        labels = ['<4', '4-5', '5-6', '6-7', '7-8', '>8']

        df = self.df.copy()
        df['price_bin'] = pd.cut(df['price'], bins=bins, labels=labels, right=False)

        data = df.groupby(['price_bin', 'dataset'])['advert_id'].nunique().unstack(fill_value=0)
        data.columns = ['Старые данные', 'Новые данные']
        data.plot(kind='bar', figsize=(12, 5))

        plt.title('Распределение по цене (старая vs новая)')
        plt.xlabel('Цена (млн)')
        plt.ylabel('Количество квартир')
        plt.legend(title='Новизна', bbox_to_anchor=(1.05, 1), loc='upper left')
        plt.grid(axis='y', linestyle='--', alpha=0.7)
        plt.tight_layout()
        plt.show()

    def save_csv(self, filename):
        df = self.df.copy()
        df['published_at'] = df['published_at'].astype(str)
        df['actualized_at'] = df['actualized_at']
        df.to_csv(filename, index=False, encoding='cp1251')
        print(f'Data saved to {filename}')


# %%
exposition = TDSKExposition('Экспозиция ТДСК с 01.07.2023 по 31.12.2023.xlsx')
print(len(exposition.df))
start = pd.Timestamp('2023-07-01')
end = pd.Timestamp('2023-12-31')
pivot = exposition.extract_building().expand_date_range().get_active_pivot_report(start, end)
print(pivot)
exposition.extract_building().expand_date_range().plot_monthly_rooms()

# %%
new_data = run_parse_all_pages('https://www.t-dsk.ru/buildings/search-apartments/?objects=all&')
new_df = pd.DataFrame(new_data)

# %%
exposition_new = exposition.union(new_df, ['old', 'new'])
# print(exposition_new.df.head())
# print(exposition_new.df.nunique())
# print(len(exposition_new.df))
exposition_new.plot_rooms_distribution()
exposition_new.plot_diff_area()
exposition_new.plot_diff_price()
exposition_new.save_csv('updated.csv')
