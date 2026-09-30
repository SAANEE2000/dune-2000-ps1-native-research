# Сравнение подходов

Оба инструмента реально собраны и запущены на всех трёх EXE. Выбор сделан после
анализа загрузчика и получения C/C++ обоими генераторами, а не по первому запуску.
Ревизии зафиксированы в `dependencies.lock.json`; дата исследования 2026-09-30.

| Проверка | PS1Recomp | RetroPortingToolKit psxrecomp |
|---|---|---|
| PS-X EXE headers | Все 3 прочитаны | Все 3 прочитаны |
| Function candidates SLUS / D2KF / DUNE | 108 / 783 / 1624 | 108 / 710 / 1391 (analyzer default) |
| PsyQ | 39 / 116 / 125 предложений по signature DB | Не заменяет независимую PsyQ signature проверку; BIOS thunks/semantic metadata |
| Indirect calls/tables | Нужны explicit overlays и ручная проверка dispatch | Analysis JSON, tables, guarded continuation dispatch, residual fallback |
| Code generation | DUNE C++ получен; не связывался в runnable title | Boot и 2 overlay C-модуля скомпилированы в Windows EXE |
| Динамическая смена EXE | Поддержка overlays в исходниках; Dune integration не проверена | AOT extractor `psx_exe`, guards по исходным байтам; переход к миссии проверен |
| Graphics | SDL2/PsyQ runtime в проекте; Dune не проверена | SDL3 + software PS1 GPU; intro/menu/миссия показаны |
| SPU / XA / CD / MDEC | Подсистемы в исходниках; end-to-end не тестировались | CD и MDEC дают оригинальные кадры; SPU/XA дают PCM; A/V parity неизвестна |
| Cards / pad | Runtime присутствует; Dune не тестировалась | Cross/D-pad путь используется оригинальной логикой; cards в runtime, save/load не проверены |
| Ручная работа | Dune title integration, корректные границы и dispatcher, overlay management | Профиль двух EXE, wrapper вложенного checkout, закрытие fallback, parity bugs |
| Лицензия | GPL-3.0 | PolyForm Noncommercial 1.0.0 |

Исходники: [PS1Recomp](https://github.com/PS1Recomp/ps1-recomp/tree/ab4f0e01e6699c741bbc3d1ee73022be2803ff69),
[psxrecomp](https://github.com/RetroPortingToolKit/psxrecomp/tree/470f03b7828c645f396cb7a6fdc9f52ca9c59de6).
Возможности в таблице разделяют наличие реализации и собственную проверку Dune.

## Выбранный путь

psxrecomp для runtime/AOT, PS1Recomp для независимой карты функций и PsyQ labels.
Причина: Dune требует несколько образов по одному адресу; content-guarded
статические варианты действительно покрыли загрузку frontend и gameplay. Это
практическое доказательство применимости, но не доказательство полной семантики.

PS1Recomp не отвергнут: второй набор границ и PsyQ signatures даёт полезные
перекрёстные проверки. Его generated output хранится в `generated/ps1/DUNE.cpp`.
Никакие masked-signature имена не используются для автоматической HLE подмены.

## Почему whole-image output нельзя считать готовой декомпиляцией

PSX analyzer нашёл 1391 candidate в DUNE; более широкий default codegen ранее
выдал 1846 функций и около 4.6 млн строк C. Большая часть payload — не обязательно
код. Entry-reachable отдельный эксперимент выдал boot 59, frontend 308, DUNE 788
функций. Эти числа описывают **разные алгоритмы discovery**, не регресс и не
процент работоспособности. Runtime использует audited overlay pipeline, а не
считает любую последовательность из payload исполняемой функцией.

Union symbol DB содержит 2740 записей с image/address/size/callers/callees и
оценкой. PSX `verified` означает внутренний эвристический класс; в нашей DB он
снижен до LIKELY, кроме подтверждённых entry points. Границы функций и размеры
остаются оценками, пока не подтверждены трассами.

## Наблюдавшееся исполнение

20-секундный диагностический прогон (`generated/probes/static-overlays-openbios/result.json`):

| Счётчик | Значение |
|---|---:|
| main/BIOS dispatch static hits | 2 018 539 |
| main/BIOS dispatch misses | 0 |
| overlay static hits | 33 802 888 |
| overlay static checks | 33 838 189 |
| interpreted instructions | 1 496 123 |
| handoffs back to native | 45 884 |

Нулевой `dispatch misses` одного слоя **не значит нулевой интерпретатор**.
Нельзя делить число вызовов функций на число инструкций и объявлять процент
native. В следующих прогонах interpreter продолжал работать. Горячие адреса
включали BIOS RAM vectors, boot continuations и frontend helpers `8003C05C`,
`8003EE8C`; адрес следует сопоставлять с текущим загруженным EXE.

## Ограничения tooling

- MSVC установлен без доступного Windows SDK; использован portable LLVM-MinGW.
- PS1Recomp tools собраны отдельной CMake-обёрткой, чтобы не требовать SDL2
  для чистого анализа. Data-dir signature DB задан явно.
- Upstream AOT CLI предполагал менее глубокую структуру checkout; wrapper
  передаёт реальный корень framework в тот же API без обхода аудита.
- fmt 9 consteval отключён только для сборки host runtime на Clang 22, как в
  upstream recompiler. Это не изменение MIPS/gameplay.
- OpenBIOS codegen warnings и runtime interpreter coverage остаются в blockers.
- В Release diagnostics отключены, но семантическая точность не улучшается
  автоматически от успешной сборки Release.
