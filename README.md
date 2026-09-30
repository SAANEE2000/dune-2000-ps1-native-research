# Dune 2000 PS1 → Windows: исследовательский порт

**Для игры с мышью открыть [RunPCInput.cmd](RunPCInput.cmd).**
Настройки — [config/input.ini](config/input.ini), управление — [INPUT.md](docs/INPUT.md).

Это рабочий **hybrid-прототип**, ещё не чистый source/recomp port. Код игры во
многом скомпилирован в x64, но рабочий вариант сохраняет MIPS fallback и PS1
совместимый runtime. OpenBIOS и исходный BIN пока необходимы. Оригинальный AI,
игровой баланс, фракции и миссии в этом проекте не менялись.

Отдельная strict-сборка действительно не содержит MIPS evaluator; при неизвестном
переходе она завершает работу с кодом 86. До playable native-only ей ещё далеко:
первый установленный blocker — изменение SDK-кода OpenBIOS и несовпадение guards.
[Подробный статус](docs/NATIVE_PORT_STATUS.md),
[остаточные зависимости](docs/REMAINING_PS1_DEPENDENCIES.md),
[матрица проверок](docs/PARITY.md).

## Скачать тестовый пакет

[ZIP с исходниками Windows-прототипа на Яндекс Диске](https://disk.yandex.ru/d/VqEody9FS8gdRg)
содержит код, скрипты сборки и краткую инструкцию. SHA-256 архива:
`a50f67724de82e5d1b3c95a932e1f9fdfa16ce3d2a90e085ad5864f9217419c6`.
Для запуска нужен собственный оригинальный образ Dune 2000; BIN/CUE, BIOS и
готового EXE в архиве нет.

## Сборки

| Запуск | Назначение |
|---|---|
| `RunPCInput.cmd` / `build/pc` | Новый PC input, рабочий исследовательский вариант; debug server выключен обычным launcher |
| `RunDune.cmd` / `build/native` | Сохранённый предыдущий исследовательский прототип |
| `RunRelease.cmd` / `build/strict` | Strict AOT диагностика, сейчас останавливается до меню |

Не путать прежний каталог `build/release` со strict milestone: старый EXE там
содержит interpreter. Новая команда Release строит только strict.

## Воспроизведение

Windows x64, Git, Python 3.11+; использовался Python 3.14. Зависимости закреплены
в `dependencies.lock.json`, установлены локально; системный PATH не изменяется.
Из корня проекта:

```powershell
.\scripts\bootstrap.ps1 -Python python
.\scripts\dune2000-import.cmd "C:\path\Dune 2000.cue"
.\scripts\build.ps1 -Step all -PCInput
.\.venv\Scripts\python.exe tools\verify_baseline.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Повторная сборка: `scripts/build.ps1 -Step build -PCInput`.
Strict: `scripts/build.ps1 -Step build -Release`.
Gate: `.venv/Scripts/python.exe tools/audit_native_dependencies.py --build strict`;
код 2 означает, что native-only release запрещён.

SDL input test — `build/pc/dune-input-tests.exe` (toolchain/bin должен быть в PATH).
Тестовый конфиг и виртуальный геймпад относятся только к тесту. Pure cursor test:
`clang++ -std=c++20 -Isrc/input tests/test_input_core.cpp -o build/test_input_core.exe`.

## Ресурсы

Принимается только оригинальный SLUS-00973 Vector с SHA-256
`94e0800ef92cfe9de3bd44cdbd8e0a85d878bded0fcfbde0cf373b8e34eac711`.
Извлечены 7 ISO-файлов, 721 MIX-ресурс и каталог 41 XA-записи. Пока runtime всё
ещё использует read-only `generated/assets/disc.cue`; `disc.bin` — hardlink на
исходный файл, его нельзя редактировать. Импорт требует одного тома с hardlinks.

Игровые ресурсы, переведённый из игры код, BIN/CUE, BIOS, snapshots и большие
рабочие файлы остаются ignored. Сохранения тестов изолированы в `generated/probes`;
обычный PC build хранит собственные карты в своей рабочей папке.

## Исследование

- [Архитектура](docs/ARCHITECTURE.md), [карта памяти](docs/MEMORY_MAP.md), [PsyQ](docs/PSYQ.md).
- [Сравнение рекомпиляторов](docs/RECOMP_ANALYSIS.md), [BIOS calls](docs/BIOS_CALLS.md).
- `research/static-transfer-exports.json`, `research/fallback-inventory.json`,
  `research/native-release-gate-*.json`: проверяемая граница текущего покрытия.

Точность AI, звука, save/load и полное прохождение ещё не подтверждены. AI-001
остаётся блокирующим. Наличие Windows EXE и работающей мыши не означает,
что аппаратная зависимость PS1 уже удалена.
