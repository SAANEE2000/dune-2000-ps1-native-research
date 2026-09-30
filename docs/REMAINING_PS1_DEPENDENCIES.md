# Оставшиеся зависимости PS1

Все строки ниже блокируют объявление core-native milestone.

| Область | Сейчас | Что требуется |
|---|---|---|
| MIPS evaluator | Есть в рабочем PC research build; удалён из strict | Пройти весь проверяемый путь при нуле обращений к fallback |
| CPUState / адреса | Рекомпилированные функции используют guest registers, PC, RAM, cycle helpers | Перенос platform boundaries и native function tables без аппаратной CPU state machine |
| Overlays | Два исходных EXE, guarded native exports; CD грузит guest image | Host module activation и data layout; закрыть динамические SDK-изменения |
| BIOS | OpenBIOS image, AOT BIOS и RAM kernels | Host implementations memory/events/files/timers/callbacks/utility APIs; таблица BIOS_CALLS.md |
| GPU / GTE / DMA | GPU registers, packets, software rasterizer и устройства DMA | Перевод исходных primitives/OT в render commands; atlas/CLUT/blending parity |
| SPU / XA | Эмуляция SPU voices и XA path | Семантика play/stop/pitch/volume/priorities в native mixer |
| CD / BIN | Raw BIN/CUE нужен после импорта | FileSystemBackend, imported assets и overlay/data activation без CD device |
| MDEC | Hardware compatibility path | Native STR decoder/player либо локальная конверсия при импорте |
| Memory card | MCD-контейнер обслуживает virtual SIO/BIOS | SaveBackend с исходным форматом, без memory-card device |
| Pad | SDL3 input готов; bridge к original button word и RAM cursor | Подключение GameAction к восстановленному оригинальному reader без SIO device |
| Timer/IRQ | Guest cycle scheduler, hardware timers | Доказанная частота logic/animation/AI и host scheduler |

## Конкретное расхождение timing

`psx_video_timing.h` использует NTSC `564480` cycles (`33868800/60`), а host
pacer в `main.cpp` целится в 59.94 Hz. Это два разных слоя и их наличие не
доказывает причину AI-001. Логический tick, частота AI и порядок callbacks Dune
ещё не измерены относительно чистого SLUS-00973. Константы не подгонялись на глаз.

## Первый установленный blocker strict

Возврат из B0:57 в D2KF на `8004545C`: OpenBIOS меняет SDK instructions,
original-byte guard отклоняет уже существующий native entry. Локальный
`build/strict/dune_aot_gate_ram.bin` используется только для диагностики,
не для генерации кода. Guard остаётся включённым. Слепое добавление seeds этот
случай не исправляет.

## Что не следует считать выполненным

Наличие Windows EXE, SDL renderer или нормальной мыши не означает удаления PS1
runtime. Отсутствие evaluator в strict не означает рабочий полный native path:
он пока завершается с ошибкой покрытия. Импорт файлов не означает, что игра
перестала читать BIN. MCD на диске не означает native SaveBackend. Рекомпиляция
OpenBIOS не означает отсутствие BIOS.

`tools/audit_native_dependencies.py --build strict` пишет release gate и
возвращает 2, пока ограничения сохраняются. AI-001, audio/FMV и save/load parity
не закрыты. Оригинальные gameplay state machines, баланс и AI не исправлялись
эвристическими патчами.
