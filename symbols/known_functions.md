# Правила symbol database

Адрес уникален только в паре **image + address**. D2KF и DUNE загружаются по
одному адресу и содержат разные инструкции. Database — результат статического
исследования, не исходники Westwood и не доказанная декомпиляция.

`functions`: address/size/callers/callees/confidence/proposed_name/notes, BIOS
selector, GTE marker и согласие двух анализаторов. `globals`: read/write sites
и предполагаемая область. `psyq`: exact/masked signature evidence. `indirect`:
tables, unresolved calls и BIOS dispatch metadata без исходных инструкций.

- CONFIRMED: header/CRT entry или точное совпадение PsyQ signature bytes.
- LIKELY: сильная эвристика или masked signature; нужна проверка контекста.
- HYPOTHESIS: weak/whole-image candidate, может быть данными.
- UNKNOWN: subsystem/function behavior пока не установлены.

SLUS entry 80010168; loader CdReadExec 80012510; Exec BIOS thunk 80013978.
D2KF entry 8002EC40; DUNE entry 8005A888. Карту CRT и loader evidence см.
`docs/MEMORY_MAP.md`, PsyQ ориентиры — `docs/PSYQ.md`.

Регенерация: `scripts/build.ps1 -Step analyze`. Все необратимые semantic renames
надо хранить отдельной curated overlay database перед добавлением в генератор;
сейчас такой curated database нет, названия помечены proposed.
