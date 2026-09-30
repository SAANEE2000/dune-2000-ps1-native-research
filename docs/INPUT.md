# PC input

Запуск: `RunPCInput.cmd`. Конфиг: `config/input.ini`; после изменений нужен
перезапуск. `DUNE_INPUT_CONFIG` может указывать другой конфиг.

| Устройство | Действия по умолчанию |
|---|---|
| Мышь | Прямой курсор; ЛКМ = Cross/Primary; ПКМ = Circle/Secondary |
| Клавиатура | Стрелки/WASD = D-pad; Enter/Space = Cross; Escape = Triangle/Back; Tab/F10 = Start |
| Остальные клавиши | Z = Square, C = Triangle, Q/E = L1/R1, 1/3 = L2/R2, Backspace = Select |
| DualSense/SDL gamepad | Face buttons по расположению; D-pad; L1/R1; триггеры; Options = Start, Create = Select; L3/R3 |
| Левый стик | Скорость курсора в миссии; направления в frontend |
| Средняя кнопка/колесо | По умолчанию не назначены; можно связать с уже существующим действием |

В исходном frontend отмена показана как **Triangle**, поэтому Escape связан
с ней. ПКМ сохраняет отдельное действие Circle. Новой RTS-модели команд нет.
Выбор пункта frontend остаётся исходным: мышиная кнопка подтверждает текущий
пункт; свободное наведение реализовано для курсора миссии, а не новой системы меню.

Пример привязки: `Square = Key/X, Mouse/Middle, Pad/west`.
Можно указать несколько источников через запятую или пустое значение.
Клавиши — SDL scancode names; Pad принимает SDL mapping names и псевдонимы
`south/east/west/north`; Axis — `left_trigger`/`right_trigger`.
`wheel_up`/`wheel_down` задают имя GameAction либо `None`.

`mouse_sensitivity=1` даёт точное совпадение с положением системного курсора.
Значения 1..4 усиливают абсолютное отклонение от центра viewport, с ограничением
по его краям. Это не имитация направлений. `controller_cursor_speed` — логические
пиксели в секунду; `controller_deadzone` — нормализованная мёртвая зона.

## Координаты и переключение устройств

SDL преобразует window coordinates через текущую logical presentation; затем
учитывается фактический прямоугольник изображения. Игра сохраняет 384×240 и свой
aspect ratio. Основной проверяемый renderer — software; Alt+Enter использует
имеющийся режим окна/fullscreen. GL fallback transform пока отдельно не проверен.

Только MouseMove или MouseButtonDown делают абсолютную позицию dirty. После
одного применения она больше не записывается. Стик или D-pad/направление клавиатуры
передают управление относительному вводу. Неподвижная мышь не возвращает курсор.
Focus loss очищает отложенные действия. Short press latch 100 ms используется
для кнопок действий; он не создаёт повторных нажатий и не меняет игровую логику.

Оригинальные поля DUNE.EXE: current X/Y `80101E1C/80101E1E`, копия для
отображения/hit-test `80101E20/80101E22`. Последовательность D-pad проверила обе
оси, прямая запись (100,80) дала соответствующее изображение. Адаптер пишет
только current-пару; исходный update переносит её дальше. Проверки шести слов
оригинального DUNE запрещают писать эти адреса при загруженном frontend.

## Режим сравнения

`mode=PS1Compatible` отключает новые привязки и прямую мышь и оставляет прежний
runtime controller path. Его настройки лежат в `build/pc/keybinds.ini` и
`build/pc/input.ini`. Это режим управления для сравнения, не доказательство
аппаратной или игровой точности PS1.

## Подтверждённые проверки

- Pure C++: масштабы 1×/2×/3×/1.75×, letterbox, clamp, deadzone, отсутствие
  stationary-mouse warp, action bits.
- SDL3 integration с активными assertions: координаты настоящего SDL renderer,
  короткий Enter, изменение Square через конфиг, ПКМ, виртуальный gamepad,
  Primary, D-pad, left stick ownership, frontend navigation, trigger, hot unplug,
  focus loss. Это не физический DualSense USB/Bluetooth тест.
- Окно игры: ЛКМ провела через New Game → Atreides → briefing → A1.
  В A1 положение мыши соответствует original cursor; наведение на юнит проверено.

Длительный gameplay, все комбинации кнопок, fullscreen на разных мониторах и
физический DualSense ещё требуют проверки. Ввод пока заканчивается адаптером
к исходным PS1 действиям/SIO; host input самостоятельный, controller hardware
dependency у игры ещё не удалена.
