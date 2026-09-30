# Состояние проверок — 2026-09-30

**WORKING ниже означает наблюдение в native, а не доказанное равенство PS1.**
Контрольная DuckStation-сессия чистого exact-hash образа в этом проходе ещё не
записана. Ранее пользователь играл в модифицированный ROM; это не baseline reference.
Headless frames, counters и audio taps не заменяют сравнение двух систем.

## [WORKING] Наблюдавшиеся checkpoints

| Checkpoint | Native evidence | DuckStation/original | Подсистема / ограничения |
|---|---|---|---|
| Запуск EXE | Обычный Windows x64 процесс + оригинальный SLUS boot | Не сверено | AOT boot + BIOS |
| Intro | 320x240 spacecraft/lady FMV | Не сверено | MDEC/CD, sync UNKNOWN |
| Main menu | `checkpoint-2.ppm`, 384x240 | Не сверено | Software GPU |
| Controller input | Cross -> выбор Дома | Не сверено | Virtual PS1 pad |
| House selection | Выбор Атрейдесов -> territory | Не сверено | Остальные ветки не пройдены агентом |
| Briefing | Text и FMV | Не сверено | Original frontend |
| Mission A1 start | `mission-wait.ppm`: база, юниты, $2300 | Не сверено | DUNE overlay |
| Обычное окно | Computer-use показал базу/зелёные юниты/$1155 | Не сверено | Пользователь запустил игру; номер миссии не установлен |

Локальные изображения и полные результаты: `generated/probes/menu-trial/`,
`generated/probes/static-overlays-openbios/`. Они игнорируются Git.

## [PARTIAL] / открытые расхождения

| ID | Severity | Native observed | Reference / ожидаемая проверка | Suspected subsystem |
|---|---|---|---|---|
| NATIVE-001 | blocker | Остаточный interpreter исполняет инструкции при успешных static hits | Native-only требование ещё не достигнуто | Overlay continuations, BIOS RAM vectors |
| TIMING-001 | high | Framework NTSC = 564480 cycles/VBlank, rounded 60 Hz; headless unpaced | Измерить оригинальные VBlank/logic tick в DuckStation | Runtime timers / instruction-cycle model |
| AI-001 | high, unconfirmed | Пользователь: «Как будто часть интеллекта у юнитов отсутствует, но билд рабочий» | Воспроизвести те же действия/миссию в чистом оригинале; конкретный сценарий ещё не установлен | UNKNOWN: game tick, interrupt scheduling, CPU semantics или особенности исходной миссии |
| AUDIO-001 | high | SPU и CD taps ненулевые, WAV сохранён; headless host tap=0 | Сравнить unit responses, effects, music, building announcements | SPU/XA/host audio pacing |
| FMV-001 | high | Intro/briefing видны | Audio/video sync, aspect ratio и длительность не измерены | MDEC/CD/audio |
| BIOS-001 | high | OpenBIOS, HLE shell skip и deterministic scheduler; codegen warnings | Retail BIOS reference и достижимость предупреждённых блоков | BIOS/runtime |
| CD-001 | medium | Runtime использует read-only raw BIN alias | Целевой extracted filesystem ещё не подключён | CD compatibility layer |

AI-001 не объявлен исправленным. Наличие fallback само по себе не доказывает
причину: корректный fallback обязан сохранять семантику. Последняя обычная
сессия завершилась через `sdl_window_close`, `interp_unsupported.midblock_count=0`;
это исключает только зарегистрированную остановку на unsupported opcode,
а не логические ошибки поведения. Исходный AI не редактировался.

## [BROKEN]

Точно воспроизведённый crash/save/gameplay defect пока не локализован.
Проблемы выше остаются blockers, даже без воспроизведённого падения.

## [UNKNOWN]

Westwood/logo sequence completeness; Harkonnen M1 и Ordos M1 под контролем
агента; unit selection, movement, construction, harvesting, combat и enemy AI
в контрольном сценарии; victory/defeat; campaign transition; game save/load;
late endings; full campaign; NTSC logic/animation frequencies; host audio sync;
pixel-accurate rendering; all controller buttons и physical gamepad.

## Milestones

| M | Статус |
|---|---|
| 0 EXE parsed and mapped | Частичная карта code/data, header/CRT CONFIRMED |
| 1 original entry reached | Да, boot + two EXE loader path |
| 2 first graphics | Да |
| 3 intro/title | Intro подтверждён |
| 4 menu accepts pad | Да |
| 5 house selection | Атрейдесы проверены |
| 6 all three Mission 1 | Частично: A1 подтверждена |
| 7 movement/building | Не проведён контрольный тест |
| 8 AI | Открыт AI-001 |
| 9 win / 10 transition / 11 save-load / 12 campaign | UNKNOWN |

Research deliverables уровня A сохранены с явными неизвестными. Визуальный
proof-of-concept уровня B получен; строгое native-only исполнение ещё не закрыто.
Уровень C не достигнут.

## Обновление: strict AOT и PC input

`WORKING` по-прежнему не означает PS1 parity. Новое управление проверено в SDL
regression harness и окне A1; полный clean-reference сценарий не записан.

| Сценарий | PC research | Clean SLUS-00973 reference | Статус |
|---|---|---|---|
| BOOT | Исходный SLUS и загрузка D2KF | Не сопоставлено | Работает; hybrid |
| MENU | Меню и Primary от мыши | Не сопоставлено | Работает |
| HOUSE SELECT | Atreides | Не сопоставлено | Работает |
| BRIEFING | Текст и FMV | Не сопоставлено | Работает; sync не измерен |
| A1 START | База/юниты/деньги, координаты курсора | Не сопоставлено | Работает |
| INPUT | Direct mouse, config, keyboard; virtual SDL gamepad regression | Original input mode сохранён | Частично проверено; physical DualSense/полный fullscreen matrix не закрыты |
| MOVE | Наведение подтверждено; контрольного replay нет | Нет сопоставления | Не подтверждена parity |
| BUILD | В этом проходе нет контролируемого сценария | Нет сопоставления | UNKNOWN |
| HARVEST | Нет контролируемого сценария | Нет сопоставления | UNKNOWN |
| COMBAT | Есть кадр атаки/повреждения в интерактивной сессии | Нет одинакового replay | Наблюдение, не regression PASS |
| AI | Сохраняется пользовательское замечание AI-001 | Сценарий ещё не изолирован | BLOCKER |
| WIN | Не пройдено агентом | Нет сопоставления | UNKNOWN |
| TRANSITION | Не пройдено агентом | Нет сопоставления | UNKNOWN |
| SAVE | Тесты используют отдельные MCD | Нет сопоставления | UNKNOWN |
| LOAD | Нет контролируемой проверки игрового сейва | Нет сопоставления | UNKNOWN |
| FMV | Intro/briefing видны | Sync/duration не сопоставлены | PARTIAL |
| AUDIO | SPU/XA остались прежними | Реплики и mix не сопоставлены | BLOCKER |

Strict сборка отдельно завершает работу с 86: существующий AOT entry `8004545C`
отклонён после изменения трёх SDK-инструкций OpenBIOS. Увеличение static variants
до 63 247 не закрывает этот дефект. Полное native-only выполнение НЕ достигнуто.
Новая архитектура ввода пока не удаляет SIO/CPU runtime.
