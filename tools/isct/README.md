# Статья для ISCT (Springer, LNCS)

«Rank or Magnitude: Learned Request Cost Estimates for Event-Loop-Aware Routing»,
С. Д. Синявский, М. И. Колосов. Готовый файл — `docs/ISCT/Sinyavskiy_ISCT.docx`.

Документ собирается из кода, как и остальные статьи проекта. Править .docx руками
нельзя: при следующей сборке правки пропадут. Каждое число в тексте читается из
файлов `data/` в момент сборки.

| файл | что делает |
|---|---|
| `build_paper.py` | читает данные, считает числа, собирает документ |
| `text_content.py` | текст статьи, таблицы, список источников |
| `results_text.py` | абзацы, зависящие от итогов замера искажения величины |
| `docx_builder.py` | вёрстка по шаблону организаторов (поля, колонтитулы, нумерация) |
| `omml.py` | формулы в формате редактора уравнений Word (OMML), а не картинками |
| `make_figures.py` | рисунки: SVG (векторные) и PNG 1200 dpi |
| `word_check.ps1` | открывает документ в Word: число страниц, где начинается список источников, экспорт в PDF |
| `springer_template.docx` | шаблон организаторов ISCT, на котором строится документ |

## Сборка (Windows: нужен шрифт Times New Roman, для проверки — Word)

```powershell
python tools/isct/make_figures.py data data figures/isct
python tools/isct/build_paper.py data data figures/isct tools/isct/springer_template.docx docs/ISCT/Sinyavskiy_ISCT.docx
powershell -File tools/isct/word_check.ps1 -Docx (Resolve-Path docs/ISCT/Sinyavskiy_ISCT.docx) -Pdf $PWD\paper.pdf
```

`build_paper.py` сам проверяет объём аннотации (150–250 слов) и длину названия
(не более 12 слов). Объём основного текста — 7–9 страниц без списка источников —
проверяется только Word'ом: `word_check.ps1` печатает страницу, на которой
начинается раздел References.

## Откуда числа

| раздел статьи | файл данных | чем получен |
|---|---|---|
| 3.1 разброс внутри маршрута | `endpoint_cost.json`, `thirdparty_postgrest.json`, `azure_trace.json` | `experiments/measure_endpoint_cost.py`, `thirdparty/` |
| 3.2 очередная модель, рис. 1 | `queue_model_validation.json` | `experiments/validate_queue_model.py` |
| 3.3 порядок против величины, табл. 1 | `rank_vs_magnitude.json`, `decision_cost.json` | `experiments/rank_vs_magnitude.py` |
| 3.4 искажение величины, рис. 2 | `magnitude_distortion.json`, `mechanism.json` | `experiments/benchmark_distortion.py` |
| 3.5 рабочие точки, табл. 2 | `budget_frontier.json`, `homogeneous_*.json` | `experiments/benchmark_budget.py` |
| 3.6 модуль nginx, рис. 3 | `nginx_capacity.json`, `gorouter.json` | `nginx/`, `gorouter/` |
| 4 деградация движка | `drift_comparison.json` | `experiments/benchmark_drift.py` |
