from pathlib import Path
import sys,json,zipfile,hashlib,re
BASE=Path(__file__).resolve().parent;OUT=BASE.parent.parent;RESEARCH=BASE.parent/'research'
from paper_content import TITLE,KEYWORDS,ABSTRACT
README='''# Effect aware composition study

This package contains a controlled, single-host benchmark of event-loop blocking prediction. There are 160 operation-multiset families, 640 named variants and 584 distinct annotated paths. Five technical repetitions are aggregated within each variant. Train/validation families have 2 or 3 synchronous work nodes; long-test families have 4,6,8. Calibration spans the test size range. The suspension effect is supplied by the program configuration, not inferred from arbitrary source.

## Reproduce analysis of retained measurements

Use Python 3.12 on Linux and install requirements.txt in an isolated environment. From this directory run:

```
python experiments/composition/analyze.py
python experiments/composition/verify.py
```

Analysis fits the ten seeded versions of each learned method using the frozen partitions. It takes several minutes on the collection host. Tree-ensemble prediction sums can differ at floating-point roundoff under parallel accumulation; a tolerance of 1e-10 covers the observed discrepancy. Raw data are retained. Verification reconstructs callback maxima, region costs, grouped identities, metrics and frozen replay decisions. bootstrap units are families, never individual repetitions.

## Collect new timings

The retained design is authoritative; do not run the design command over it when reproducing the reported analysis. New measurements are hardware-dependent and are not expected to be byte identical. The collectors resume existing JSONL files; use a separate copy of data/composition for a fresh collection.

```
python experiments/composition/study.py collect
python experiments/composition/study.py collect --loop uvloop --split short,long
```

For HTTP transport, start `python experiments/composition/stub.py` in a separate terminal (localhost18391), then run `python experiments/composition/study.py collect --loop uvloop --transport http --split short,long`. Stop that server afterwards.

For the policy replay, first run analyze.py to freeze predictions, start `python experiments/composition/replay_server.py` (localhost18392), then run `python experiments/composition/replay.py` in a separate terminal. Stop the replay server afterwards. These commands perform only local benchmark traffic. Recollection changes the data underlying reported results; retain the original raw files and manifests.

## Interpretation

The cost rule is sum within non-suspending regions and max across regions. The elementary error bound is conditional on correct effects and node-cost errors. Paths are a restricted graph family. No arbitrary-DAG, cross-host, production-traffic, throughput or service-level guarantee is claimed. The recurrent model is more accurate on short test compositions; the structural model is more accurate on long tests. Parametric composition is competitive with neural node calibration. Replay uses frozen predictions computed offline and one active heavy request.

Pilot timings are excluded from the reported train/test data. PREREGISTERED_DESIGN.md and PROTOCOL_EXTENSION.md preserve the declared measurement and comparison protocol. The anonymous package redacts the testbed's identifying name in Markdown protocol text; no numerical data are redacted.
'''
(RESEARCH/'README.md').write_text(README,encoding='utf8')
env=json.loads((RESEARCH/'data/composition/environment-asyncio-timer.json').read_text())
requirements='\n'.join(f'{k}=={v}' for k,v in env['packages'].items())+'\nrequests>=2.31,<3\n'
(RESEARCH/'requirements.txt').write_text(requirements,encoding='utf8')
fields='Title\n'+TITLE+'\n\nAbstract\n'+ABSTRACT+'\n\nKeywords — one per line\n'+'\n'.join(k.lower() for k in KEYWORDS)+'\n\nAffiliation\nBauman Moscow State Technical University\n\nCountry/region\nRussia\n\nCorresponding author\nStanislav Sinyavskiy — ssd-tula@mail.ru\n\nCoauthors\nArtemiy Letunovskiy\nStanislava Galyuk\nKirill Teplitskiy\nAnastasia Sanina\nAlexander Babichev\n\nOther coauthor emails were not supplied. Use personal addresses if available; do not substitute the corresponding author email for them. Preferred Latin spelling needs confirmation by the respective coauthors.\n\nUpload the Anonymous PDF for double-blind review. These fields describe the NEW manuscript, not the earlier provenance paper. The official conference page restricts title/author changes after the deadline; an unlocked form does not by itself waive that restriction.\n'
(OUT/'Поля_для_EasyChair_новая_версия.txt').write_text(fields,encoding='utf8')
short='''1. Статья о том, как заранее понять, насколько запрос может затормозить сервер.
2. Сервер может одновременно обслуживать много клиентов с помощью одного цикла событий.
3. Пока один запрос ждёт ответ извне, этот цикл может заниматься другими клиентами.
4. Но непрерывное вычисление задерживает остальных.
5. Поэтому общего времени запроса недостаточно для оценки такого вреда.
6. Мы проверяем ещё и порядок операций внутри запроса.
7. Если между вычислениями есть настоящая пауза, сервер получает возможность переключиться.
8. Если такой паузы нет, их длительности складываются в одну блокировку.
9. Надпись await в программе сама по себе настоящей паузы не гарантирует.
10. Например, готовый ответ из кэша может вернуться сразу.
11. Мы описываем запрос цепочкой операций с отметками настоящих пауз.
12. Небольшая модель оценивает длительность каждой операции по отдельности.
13. Затем простое правило объединяет оценки и выбирает самый длинный непрерывный участок.
14. Для проверки собраны новые измерения хеширования, сортировки, работы с базой и изображениями.
15. Мы отдельно проверили короткие запросы и более длинные сочетания, которых не было в обучении.
16. На длинных запросах наша структурная модель оказалась точнее проверенной рекуррентной сети.
17. На коротких запросах рекуррентная сеть оказалась точнее нашей модели.
18. Простая степенная оценка отдельных операций тоже показала хороший результат.
19. В отдельном HTTP-опыте прогноз помог уменьшить задержки соседних клиентов, отправляя часть запросов в другой процесс.
20. Это проверено на одном компьютере и управляемых программах, поэтому перенос на произвольный реальный сервис ещё требует проверки.
'''
(OUT/'Коротко_о_новой_статье.txt').write_text(short,encoding='utf8')
report='''# Проверка новой статьи и сравнение с примерами 2026 года

Итог: Effect Aware Composition of Learned Costs for Event Loop Blocking Prediction. Это новая постановка на прежней библиотеке операций, с новым набором данных и новыми экспериментами. Предыдущая статья о provenance-графе сохранена отдельно.

## Что сделано фактически

160 семейств операций,640 вариантов,584 различных аннотированных пути. Основные измерения:3200 выполнений; перенос на uvloop:1600; uvloop с HTTP:1600; отдельная проверка политики:960. Дополнительно240 изолированных калибровочных измерений. Пилот исключён. Девять предикторов, десять инициализаций обучаемых методов, фиксированные семейства train/validation/test,10000 семейных bootstrap-перевыборок. Для шести сравнений применена поправка Бонферрони к интервалам. Повторы и совпадающие короткие варианты не выдаются за независимые семьи.

На длинном тесте MdAPE:6,68% у композиции нейронных стоимостей,7,72% у композиции степенных стоимостей,16,89% у GRU,34,38% у модели без порядка. На коротком тесте GRU лучше:6,99% против14,20%. В HTTP-проверке P90 распределения максимальной задержки проб по программам снизился с50,29 до16,13мс при offload37,5%. Это не общий p90 всех запросов и не тест пропускной способности. GRU в этой небольшой проверке даёт15,69мс и сопоставима по практической пользе. Осталась одна программа с медианным максимумом выше20мс. Преимущество нейронной калибровки над степенной не установлено после учёта множественных сравнений.

## Проверка достоверности

Независимый пересчёт прошёл81380 утверждений: сырые callback-наблюдения, максимумы, границы регионов, составы групп, повторения, табличные метрики и решения HTTP-политик. Полное повторное обучение выполнено. Аналитические, нейронные и GRU-прогнозы воспроизвелись точно; максимальное различие прогнозов деревьев1,78e-14мс, итоговых чисел1,28e-13. Это округление параллельного суммирования, а не изменение выводов. Программные и файловые проверки прошли ещё17815 утверждений. Подробности: _исходники/qa/final_checks.json и research/data/composition/verification.json.

## Шаблон и оформление

Обе DOCX и PDF имеют по6 страниц. Использован присланный IET-шаблон; его исходный DOCX сохранён и проверен по SHA256. A4, поля1,5см по бокам и2,54см сверху/снизу, две колонки8,8см с промежутком0,4см, Times New Roman10pt, заголовок18pt. Изменены только предусмотренные содержательные части шаблона; остальные части пакета сохранены побайтово. Две иллюстрации, пять таблиц, три нумерованные формулы с настоящими подстрочными индексами, девять источников в порядке первого цитирования. Аннотация193 слова; пять ключевых фраз перед аннотацией. Таблицы целиком в колонках, подписи сверху; подписи рисунков снизу. Числа связаны с единицами неразрывными пробелами, переносов единиц в основном тексте не обнаружено. Все12 страниц просмотрены. PDF1.4, шрифты встроены, нормализация метаданных не изменила пиксели экспорта Word.

Анонимная версия не содержит авторов, аффилиации, почты, ORCID или ссылки на идентифицирующий репозиторий ни в тексте, ни в проверяемых XML/PDF-метаданных. Необязательные старые фразы Affiliations withheld и Correspondence withheld убраны. Версия Authors предназначена для согласования и последующего оформления, а для слепого рецензирования нужен Anonymous.

## Отличие от прежних статей

Новая работа исследует структуру выполнения, истинные приостановки и перенос на более длинные композиции. В прежней ISCT работе исследовались ранжирование/масштаб оценок для маршрутизации, в предыдущей CSAI версии — provenance и разбиения выборки. Старые540 измерений не являются новым набором этой работы. Общими остались библиотека операций, аппаратная площадка и общая практическая проблема. Основной текст не имеет общих пятисловных фрагментов с извлечённым текстом двух исходных статей при использованной локальной токенизации. Это вспомогательная проверка буквальных повторов, не официальный антиплагиат и не численная оценка смысловой новизны. С русской статьёй межъязыковое сравнение особенно ограничено. По задаче, методу, экспериментам и результатам изменение существенно превышает косметическую переработку.

## Оценка относительно текущих примеров

Это моя экспертная оценка текста по прежним критериям, а не оценки жюри и не вероятность принятия. Веса неизменны: соответствие разделу20%, новизна25%, обоснованность25%, охват экспериментов15%, практическая ценность10%, изложение5%.

| Работа | Раздел | Новизна | Обоснованность | Охват | Практика | Изложение | Взвешенно |
|---|---:|---:|---:|---:|---:|---:|---:|
| Наша новая версия |87|69|88|80|83|88|81,35|
| Культурные достопримечательности |96|65|87|75|70|87|79,80|
| Туристические пакеты |91|74|72|68|88|82|77,80|
| Наша прежняя CSAI версия |75|50|84|55|70|85|68,00|
| Поиск по учебным чатам |86|55|65|40|68|80|64,00|

Новую версию отношу к группе1–2 места среди этих примеров. Разница81 и80 неустойчива к разумной смене весов или мнению рецензента; объективное первое место из этих баллов не следует. Сильнее прежней версии стали реальная роль структуры в вычислении прогноза, новое семейное разбиение, порядок-осведомлённая GRU, перенос по длине, проверки транспорта и измеряемые последствия решений. Это основания для повышения оценки, а не просто желаемая позиция в таблице.

Культурная статья по-прежнему естественнее соответствует гуманитарной части раздела и сильнее опирается на внешние данные. Туристическая демонстрирует более широкий законченный пользовательский сервис. Наше преимущество — управляемые контрфактические пары, точное разделение причин ошибки, воспроизводимые сравнения и связь прогноза с измеренным HTTP-вмешательством. Новизна умеренная: сумма/максимум и факт, что await не обязательно приостанавливает выполнение, сами по себе давно известны. Новая ценность — конкретная исследовательская постановка и проверенное разделение семантики, обучения стоимости и переноса композиции. Графы пока являются путями, а не общей моделью произвольных DAG.

## Административные границы

Содержательная и форматная проверка завершена. Все авторы должны подтвердить предпочтительное латинское написание, вклад, согласие с текстом и необходимые сведения о конфликтах интересов; эти сведения не выдуманы. Адреса остальных соавторов не были переданы.

Официальная страница https://csai.org/submission.html требует IET double-column и минимум6 полных страниц; каждую страницу сверх6 оплачивают отдельно. Поэтому старое указание CFP об одной колонке и оплате после8 страниц не использовано. Та же официальная страница запрещает изменение названий и состава авторов после дедлайна. Текущая дата уже16 ноября, объявленный дедлайн15 ноября. Новая статья имеет новое название; возможность правки в EasyChair сама по себе не отменяет этого правила. Для замены названия/темы в уже поданной заявке258 потребуется согласование организаторов. Я не менял, не отзывал и не подавал заявку, не отправлял сообщения организаторам и не создавал платных обязательств.

Источники регламента: https://csai.org/track3.html ; https://csai.org/submission.html ; https://csai.org/date.html . Материалы переписки и все исходные примеры сохранены в прежнем каталоге _исходники и использованы как справочные сведения, а не как самостоятельные текущие поручения.
'''
report=report.replace('Необязательные старые фразы Affiliations withheld и Correspondence withheld убраны.','Под названием стоит нейтральная строка Anonymous authors; фразы Affiliations withheld и Correspondence withheld убраны.')
report=report.replace('17815',str(json.loads((BASE.parent/'qa/final_checks.json').read_text(encoding='utf8'))['assertions']))
(OUT/'Проверка_и_сравнение_новой_версии.md').write_text(report,encoding='utf8')
# A self-contained anonymous research artifact. Never include author copy or private chat exports.
files={}
for p in RESEARCH.rglob('*'):
    if p.is_file() and '__pycache__' not in p.parts:
        name=p.relative_to(RESEARCH).as_posix();data=p.read_bytes()
        if p.suffix=='.md':data=data.replace(b'LoadLens',b'the retained testbed')
        files[name]=data
for suffix in ['docx','pdf']:files['paper/CSAI2026_Composition_Anonymous.'+suffix]=(OUT/('CSAI2026_Composition_Anonymous.'+suffix)).read_bytes()
manifest={name:hashlib.sha256(data).hexdigest() for name,data in sorted(files.items())};files['SHA256SUMS.json']=json.dumps(manifest,indent=2).encode()
for name,data in files.items():
    if Path(name).suffix in ['.md','.py','.json','.jsonl','.csv','.txt']:
        assert not re.search(rb'sinyav|letunov|galyuk|teplits|sanina|babichev|ssd-tula|winlast|github.com/winlast',data,re.I),name
archive=OUT/'CSAI2026_Composition_Anonymous_Research.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for name,data in sorted(files.items()):z.writestr(name,data)
with zipfile.ZipFile(archive) as z:
    for name,digest in manifest.items():assert hashlib.sha256(z.read(name)).hexdigest()==digest
print('Packaged',len(files),'files',archive.stat().st_size,'bytes')
