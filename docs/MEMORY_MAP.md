# Карта памяти

Источник: exact-hash BIN; `generated/assets/manifest.json`, оригинальные PS-X EXE
headers, CRT instructions и `research/executable_audit.json`. Диапазоны ниже
полуоткрытые. **PS-X load span не является восстановленной секцией `.text`.**

| Образ | Размер файла | Entry/initial PC | Загрузка | Конец payload |
|---|---:|---|---|---|
| SLUS_009.73 | 36 864 | 80010168 | 80010000 | 80018800 |
| D2KF.EXE | 1 804 288 | 8002EC40 | 80019000 | 801D1000 |
| DUNE.EXE | 1 873 920 | 8005A888 | 80019000 | 801E2000 |

Во всех заголовках GP, `.data`, `.bss` поля равны нулю; initial stack header
`801FFFF0`. Полезная нагрузка начинается с file offset 0x800. Общая RAM:
2 MB; physical 00000000..001FFFFF, cached alias 80000000..801FFFFF.
Scratchpad physical 1F800000..1F800400; MMIO 1F801000..1F802000.

## CRT — CONFIRMED

Скрипт проверяет шаблон цикла очистки BSS перед извлечением констант. GP
восстановлен из CRT, а не взят из нулевого header.

| Образ | BSS start | BSS end | GP после CRT | InitHeap2 base arg | Size arg |
|---|---|---|---|---|---|
| SLUS | 80016284 | 800187A8 | 8001626C | 800187AC | 001E5850 |
| D2KF | 801687C0 | 80174FD0 | 8016860C | 80174FD4 | 00089028 |
| DUNE | 80176F58 | 80184D40 | 80176938 | 80184D44 | 000792B8 |

CRT читает stack top 00200000 и reserve 00002000, устанавливает SP=801FFFF8.
Адреса этих слов: SLUS 80014720/8001471C; D2KF 8005CBEC/8005CBE8;
DUNE 80101CF8/80101CF4. Значения heap — аргументы стартового CRT вызова, не
доказательство устройства всех последующих игровых allocators.

Граница всех code/data областей неизвестна: payload содержит данные, таблицы,
графику и предполагаемые функции. Whole-image анализ покрывает инструкциями
примерно 23.3% DUNE payload и 12.3% D2KF, но часть обнаружений может быть данными.
2230 записей globals — кандидаты адресных ссылок, а не готовые C структуры.

## Загрузчик / executable overlays — CONFIRMED

В SLUS selector по `80016270`; таблица строк по `80016274` содержит
`\D2KF.EXE;1`, `\DUNE.EXE;1`. Вызов CdReadExec: `800100FC` -> `80012510`;
BIOS Exec: `80010118` -> `80013978`. После возврата загрузчик выбирает следующий
образ с учётом результата предыдущего. D2KF main candidate `800190E0`, DUNE
main candidate `8004078C` (CRT call at `8005A94C`).

Переход frontend -> briefing -> mission реально наблюдался в native runtime.
Совпадающие адреса в этих двух EXE **не означают одну функцию**.

В 721 MIX entry не найдено `PS-X EXE` headers. Отсутствие headerless code,
самомодифицирующегося кода или других CD-loaded fragments **не доказано**.
Статические write-to-code кандидаты могут быть ошибками классификации данных;
FlushCache сам по себе также не доказывает self-modifying code.

## Косвенные переходы

| Образ | Static function candidates | Jump tables | Table targets | Unresolved indirect |
|---|---:|---:|---:|---:|
| SLUS | 108 | 1 | 5 | 22 |
| D2KF | 710 | 39 | 740 | 121 |
| DUNE | 1391 | 30 | 580 | 125 |

Полные metadata: `symbols/indirect.json`. Контекст исходных инструкций хранится
только в ignored `generated/psx/*-analysis/indirect.json` и `disasm/`.
Таблицы callbacks, BIOS vectors и runtime-written trampolines остаются причинами
fallback, даже при распознанных основных EXE.

## Хеши файлов

| Файл | SHA-256 |
|---|---|
| SLUS_009.73 | 82b4740c0fafe17c32067371b8f1adf61225515d600fbab6b6eb8d00c6d68337 |
| D2KF.EXE | 82fa578104c4122c997aa0db530dfe9ee407494b07f097600033074a66b9ab5b |
| DUNE.EXE | c55547212b78ac324c3c5fc6b1c5353cf6ab4c2412b69419fcba2689ff1816a8 |
