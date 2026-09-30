# PsyQ, BIOS и hardware audit

Источник labels — PS1Recomp signature database; каждое предложенное совпадение
повторно проверяется собственным SHA-256 matcher. `symbols/psyq.json/csv`
содержит image/address/name/library, callers, исходные hash evidence и confidence.

| Образ | Exact-byte signatures | Masked-only | Всего |
|---|---:|---:|---:|
| SLUS | 12 | 27 | 39 |
| D2KF | 33 | 83 | 116 |
| DUNE | 43 | 82 | 125 |

CONFIRMED здесь означает совпадение исходных байтов с signature DB, а не
установленную версию SDK. Masked matcher маскирует широкий набор immediates,
поэтому его результат только LIKELY. Несколько выпусков SDK могут иметь одинаковые
функции; **версия PsyQ UNKNOWN**. Все оригинальные функции пока сохраняются
в translated code; никаких спекулятивных HLE замен не включено.

## Конкретные ориентиры DUNE.EXE

Предложенные signature labels (точный confidence смотреть в DB):

| Адрес | Имя / назначение |
|---|---|
| 80074614 | CdControl |
| 800774A8 | CdRead |
| 80077644 | CdReadSync |
| 80079E10 | VSyncCallback |
| 8007A530 | startIntrVSync |
| 8007D6A0 | ResetGraph |
| 8007E010 | DrawOTag |
| 8007E080 | PutDrawEnv |
| 8007E24C | PutDispEnv |

Распознаны BIOS thunks с явными A0/B0/C0 selectors:

| Адрес | BIOS dispatch |
|---|---|
| 80079600 | B0:07 DeliverEvent |
| 80079610 / 620 / 630 / 640 | FileOpen / FileRead / FileWrite / FileClose |
| 80079650 | ChangeClearPad |
| 80079D70 | C0:0A ChangeClearRCnt |
| 8007A4C8 | A0:72 CdRemove |
| 8007A4E0 / 4F0 / 500 | ReturnFromException / SetDefaultExit / SetCustomExit |
| 8007D690 | A0:44 FlushCache |
| 80082FD0 / FE0 | AddDevice / RemoveDevice |
| 80082FF0 / 83000 | SysEnqIntRP / SysDeqIntRP |
| 80086260 / 6270 / 878C0 | OpenEvent / EnableEvent / TestEvent |

Полные значения находятся в `research/executable_audit.json`; сокращённые адреса
в строках таблицы используют тот же префикс 8007/8008, что первый адрес.

## Подсистемы и граница доказательств

| Подсистема | Статическое evidence | Динамическое evidence / остаток |
|---|---|---|
| GPU | DrawOTag/DrawEnv/DispEnv signatures | Оригинальные menu/mission кадры; pixel parity не сравнивалась |
| GTE | 42 DUNE и 5 D2KF function candidates с GTE instructions | Полнота opcode/cycle точности не доказана |
| CD | CdControl/CdRead/CdReadSync, loader calls и 7 ISO файлов | Frontend -> gameplay; raw XA читает runtime |
| SPU / XA | 13 `.snd` MIX assets; hardware-pointer literals | PCM taps ненулевые; реплики/эффекты/A-V sync ещё не сверены |
| MDEC / STR | DATA.XA raw sectors, 41 FAT XA records | Intro и briefing FMV кадры декодируются |
| Pad | BIOS pad/event thunks и runtime SIO | Cross провёл из меню к миссии; все кнопки не проверены |
| Memory cards | File/event/device thunks, original card semantics | Файлы virtual cards создаются; game save/load UNKNOWN |
| IRQ / timers | VSyncCallback, ChangeClearRCnt, exception/event thunks | IRQ счётчики активны; частота игрового AI/tick UNKNOWN |
| DMA | Литералы MMIO в original payload, CD/GPU pathways | Полная карта DMA call sites и timing UNKNOWN |
| Self-modifying code | Статические write candidates + FlushCache | Не доказано ни наличие, ни отсутствие в игре; BIOS vectors пишутся runtime |

`hardware_pointer_literals` в JSON — только расположения aligned слов, похожих
на MMIO pointers. Такой literal может оказаться данными или совпадением инструкции;
он не выдаётся за подтверждённое обращение. Static direct MMIO reference tracker
в текущем проходе не восстановил обращения через эти pointer pools.

Следующие PsyQ приоритеты: SPU/voice path, MDEC library functions, pad/card entry
points и timer callbacks. Применять SDK implementation допустимо после проверки
семантики, не ради удаления непонятного кода.
