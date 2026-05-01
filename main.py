# %% Cell 1
import matplotlib.pyplot as plt
import pandas as pd


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

        # 2. Создаем столбец с Месяцем (для группировки)
        df['month'] = df['date_range'].dt.to_period('M').astype(str)

        # 3. Группируем: Месяц + Комнатность -> Уникальные ID
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
