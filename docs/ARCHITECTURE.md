# Архитектура — 2026-09-30

## Исполнение

```text
Original BIN (exact SHA-256)
   -> importer -> original SLUS boot, D2KF.EXE, DUNE.EXE + assets
   -> psxrecomp -> generated C + guarded overlay variants
   -> Clang x64 + psxrecomp runtime + SDL3 -> Dune2000Native.exe

runtime dispatch
   -> compiled boot / compiled OpenBIOS / compiled matching overlay
   -> residual dirty-RAM interpreter when no compiled continuation matches
```

Наличие последней ветки не скрывается. Конечное требование native-only ещё не
выполнено; текущий результат — AOT proof-of-concept с переходным runtime.
Не используется DuckStation, отдельный эмуляторный процесс или PC Dune 2000.

Original `SLUS_009.73` — маленький резидентный загрузчик. `D2KF.EXE` и `DUNE.EXE`
сменяют друг друга в памяти по адресу `0x80019000`. Нельзя просто скомпилировать
один DUNE.EXE и считать адрес функции постоянным. `aot/overlays.json` задаёт
проверку оригинального загрузчика, образов и точек входа. Генератор выпускает
разные реализации для совпадающих адресов; runtime проверяет содержимое перед
переходом. Неподходящие/неизвестные байты не подменяются версией другого EXE.

Статический audit: 2 образа, 27 052 guarded entry/continuation variants, все
проверенные guards совпали с исходными байтами. Это **не число функций** и не
доказательство полного покрытия. `AOT_STATIC_AUDIT.json` прямо возвращает
`full_static_coverage_proven: false`.

## Platform

Windows x64 / Clang 22.1.8 / C++20 / CMake / SDL3 3.4.10. Graphics backend:
software PS1 GPU primitives, исходные разрешения 320x240 для FMV и 384x240
для меню/миссии в зафиксированных кадрах. SPU, CD/XA, MDEC, DMA, IRQ, timers,
SIO/pad/memory cards обслуживает выбранный compatibility runtime. Наличие кода
подсистемы не означает, что вся подсистема уже проверена на Dune.

OpenBIOS из pinned psxrecomp поставляется с MIT notice и также компилируется
в host-код. В журнале: `bios_backend=LLE (recompiled BIOS)`, `bios_boot=HLE
(shell skipped)`, kernel-call HLE tier unavailable for OpenBIOS; deterministic
TCB scheduler HLE активен. Не заявляется равенство retail BIOS. Генерация BIOS
предупреждает о 8 unsupported instructions и неподтверждённых cross-targets;
они не помешали наблюдавшемуся пути, но требуют отдельного аудита.

Runtime поддерживает больше возможностей, чем включено здесь. Netplay, rewind,
Vulkan, launcher UI отключены при сборке; idle skip отключён в game config.
В исходной проверенной конфигурации `mods/state.toml` содержит только
`format_version = 2`, активированных enhancements нет. Нельзя включать
8 MB RAM, CD speed, fast loading, PGXP или widescreen для baseline-проверок.

## Timing и звук

Игра сохраняет исходные вызовы VSync/IRQ; logic tick ещё не определён.
Runtime использует 564480 циклов на NTSC VBlank, то есть округлённые 60 Hz;
см. `third_party/psxrecomp/runtime/include/psx_video_timing.h`. Это известное
ограничение точности и не доказательство аппаратного тайминга SLUS.
Headless прогоны идут без нормального wall-clock pacing: 3067 frames примерно
за 20 секунд. Использовать их как измерение скорости игры нельзя.

SPU/CD PCM taps возвращают ненулевые samples; сохранён WAV. Headless host tap
равен нулю, так как аудиовыход не активен. Проверка реплик, эффектов, музыки и
синхронизации FMV на реальном host output остаётся обязательной.

## Файлы и сохранения

Importer извлекает ISO/MIX для исследования и дальнейшего virtual filesystem.
Сейчас runtime получает исходный raw disc через ASCII hardlink и CUE; XA
декодируется из оригинальных секторов. Перекодирования видео не было.

Virtual memory cards остаются в исходном PS1 формате. Локальные test cards
изолированы по прогонам; старые ROM-hack cards не подключались и не менялись.
Save/load/campaign progression этим проходом не проверены.

## Воспроизводимость

Все версии заданы в `dependencies.lock.json`; `pipeline.py` сохраняет команды
по этапам и их вывод. `tools/build_aot.py` использует upstream
extract/build/audit/publish API с явным корнем вложенного framework checkout.
Это устраняет ошибку определения BIOS profile при структуре `third_party/psxrecomp`.
Дополнительный `FMT_CONSTEVAL=` повторяет workaround upstream для fmt 9 + Clang 22.
Игровые инструкции и PsyQ calls не заменены рукописной логикой.

Release собирается в отдельный каталог с `PSX_DEBUG_TOOLS=OFF`. Debug server,
снимки RAM и API virtual pad используются только в исследовательской сборке.
