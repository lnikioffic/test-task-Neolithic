# test-task-Neolithic

## Зависимости
[![matplotlib](https://img.shields.io/badge/matplotlib-3.10.9-blue?logo=matplotlib)](https://matplotlib.org/) [![pandas](https://img.shields.io/badge/pandas-3.0.2-blue?logo=pandas)](https://pandas.pydata.org/) [![selectolax](https://img.shields.io/badge/selectolax-0.4.7-blue)](https://selectolax.readthedocs.io/) [![requests](https://img.shields.io/badge/requests-2.33.1-blue?logo=requests)](https://requests.readthedocs.io/) [![openpyxl](https://img.shields.io/badge/openpyxl-3.1.5-blue)](https://openpyxl.readthedocs.io/)


## Инструкия по запуску
pip
```sh
python -m venv .venv

.venv\Scripts\activate

python main.py
```

uv
```sh
uv sync
uv run main.py
```

Для работы как с `jupyter` в Zed
```sh
.venv\Scripts\activate
python -m ipykernel install --user --name .venv --display-name "Python (.venv)"

# для uv
uv run python -m ipykernel install --user --name .venv --display-name "Python (.venv)"
```

## Перове задание

### Сводная таблица с общим количеством активных объектов за каждый день рассматриваемого периода.
![Сводная таблица с общим количеством активных объектов за каждый день рассматриваемого периода](assets/table.png)

### График по месячному количеству активных объектов в разрезе комнатности.

Высокая активность наблюдается в осенне-зимний период, пик активности в декабре.
В период активности значительно повышается активность однокомнатных квартир в остальные периоды активность у квартир с одной, двумя и тремя комнатами примерно на одном уровне.
![](assets/1plot.png)

## Второе задание

### Сравнение как менялось количество представленных в экспозиции квартир по количеству комнат в новой выборке и в старой.

![](assets/2plot.png)

### Сравнение как менялась площадь по диапазонам <20, 20-30, 30-40 и тд. до >100 по количеству квартир в новой выборке и в старой.

![](assets/3plot.png)

### Сравнение как менялась цена по диапазонам <4млн, 4-5, 5-6 и тд. до >8 по количеству квартир в новой выборке и в старой.
![](assets/4plot.png)