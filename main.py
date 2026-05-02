# %% Cell 1
import datetime

import matplotlib.pyplot as plt
import pandas as pd

from parser import run_parse_all_pages


# %%
class TDSKExposition:
    def __init__(
        self,
        path_csv: str | None = None,
        df: pd.DataFrame | None = None,
    ) -> None:
        """Инициализирует объект с данными из Excel или DataFrame.

        :param path_csv: Путь к Excel файлу.
        :param df: DataFrame с данными.
        :return: None
        """
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

    def extract_building(self) -> TDSKExposition:
        """Извлекает название корпуса из адреса.

        :return: Новый объект TDSKExcerpt с добавленным полем building.
        :rtype: TDSKExposition
        """
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

    def expand_date_range(self) -> TDSKExposition:
        """Расширяет данные, создавая записи для каждого дня экспозиции.

        :return: Новый объект с раскрытым диапазоном дат.
        :rtype: TDSKExposition
        """
        new = self.df.copy()
        new['date_range'] = new.apply(
            lambda row: pd.date_range(row['published_at'], row['actualized_at'], freq='D'),
            axis=1,
        )
        new = new.explode('date_range')
        return TDSKExposition(df=new)

    def get_active_pivot_report(
        self,
        start_date: datetime.datetime,
        end_date: datetime.datetime,
    ) -> pd.DataFrame:
        """Формирует отчёт по активным квартирам за период.

        :param start_date: Начальная дата периода.
        :param end_date: Конечная дата периода.
        :return: DataFrame с отчётом.
        :rtype: pd.DataFrame
        """
        mask = (self.df['date_range'] >= start_date) & (self.df['date_range'] <= end_date)
        df_filtered = self.df.loc[mask]

        report = df_filtered.groupby(['date_range', 'building'])['id'].nunique().reset_index()
        report.columns = ['Дата', 'Корпус', 'Кол-во активных квартир']
        report['Дата'] = pd.to_datetime(report['Дата']).dt.date
        report = report.sort_values(['Дата', 'Корпус'])
        return report

    def plot_monthly_rooms(self) -> None:
        """Строит столбчатую диаграмму динамики активных объектов по комнатности по месяцам.

        :return: None
        """
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

    def union(self, new_df: pd.DataFrame, tags: list[str]) -> TDSKExposition:
        """Объединяет текущий датасет с новым, добавляя метку источника данных.

        :param new_df: Новый DataFrame для объединения.
        :param tags: Метки для старых и новых данных [старые, новые].
        :return: Объединённый объект TDSKExposition.
        :rtype: TDSKExposition
        """
        self.df['dataset'] = tags[0]
        new_df['dataset'] = tags[1]
        combined = pd.concat([self.df, new_df], ignore_index=True)
        return TDSKExposition(df=combined)

    def plot_rooms_distribution(self) -> None:
        """Строит столбчатую диаграмму количества квартир по комнатности (old vs new).

        :return: None
        """
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

    def plot_diff_area(self) -> None:
        """Строит столбчатую диаграмму распределения квартир по площади (old vs new).

        :return: None
        """
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

    def plot_diff_price(self) -> None:
        """Строит столбчатую диаграмму распределения квартир по цене (old vs new).

        :return: None
        """
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

    def save_csv(self, filename: str) -> None:
        """Сохраняет данные DataFrame в CSV файл.

        :param filename: Имя файла для сохранения.
        :return: None
        """
        df = self.df.copy()
        df['published_at'] = df['published_at'].astype(str)
        df['actualized_at'] = df['actualized_at']
        df.to_csv(filename, index=False, encoding='cp1251')
        print(f'Data saved to {filename}')


# %%
exposition = TDSKExposition('Экспозиция ТДСК с 01.07.2023 по 31.12.2023.xlsx')
print(len(exposition.df))
start = datetime.datetime(2023, 7, 1, tzinfo=datetime.UTC)
end = datetime.datetime(2023, 12, 31, tzinfo=datetime.UTC)
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
