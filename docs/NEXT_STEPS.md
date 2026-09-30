# Следующие действия

1. **AI-001: воспроизводимый reference.** Запустить ту же исходную миссию в
   отдельном чистом DuckStation profile (software/1x, без cheats/overclock),
   повторить один приказ движения и вход противника в радиус атаки; записать
   virtual pad inputs, VBlank count, unit coordinates/orders/targets. В native
   повторить input sequence. Сначала найти первую разошедшуюся величину, затем
   исправлять runtime semantics. Новый AI или ускорение оригинального AI запрещены.
2. **Закрыть interpreter coverage.** Собирать dirty-RAM PC histograms раздельно
   по boot/D2KF/DUNE и hash загруженного кода. Добавлять только доказанные
   entries/continuations и runtime-written vector recipes. Проверять guards,
   повторить intro/menu/A1. Native dispatch hit ratio не использовать как
   долю native instructions. Ввести счётчик или режим fail-on-game-interpreter.
3. **Timing.** Найти оригинальный game tick по VSync/IRQ callers, частоту AI и
   анимации. Сравнить cycle budget и IRQ ordering с DuckStation. Не добавлять
   60 FPS gameplay hack; rounded NTSC runtime constants должны быть исследованы.
4. **BIOS.** Проверить достижимость 8 unsupported codegen sites и cross-target
   warnings. Сравнить OpenBIOS с локальным retail BIOS в отдельной конфигурации;
   BIOS не публиковать. Shell skip/HLE scheduler явно учитывать в reference.
5. **Сценарии A1/H1/O1.** Одинаково проверить выбор, движение, строительство,
   сбор spice, combat и поведение CPU. Сохранить traces и screenshots локально.
6. **Звук/FMVs.** Записать реальный host PCM, исходные SPU/CD commands, измерить
   A/V sync intro/briefing; отдельно unit selection/move/attack/building voices.
   Не применять старые Mercenary voice patches и не заменять русскую озвучку.
7. **Сохранения.** На отдельных чистых .mcd записать прогресс, перезапустить,
   загрузить; сверить house/level и структуру PS1 card с original. Пользовательские
   карты не заменять экспериментальными.
8. **CD abstraction.** На основе импортированных extents добавить read-only
   виртуальные CD records: сохранить XA subheaders/2324 payload, seek ordering,
   секторный timing и ISO requests. Удалить runtime зависимость от whole BIN
   только после совпадения данных и checkpoints.
9. **Дополнить symbol DB.** Разобрать pointer pools SPU/MDEC/PAD/MEMCARD/DMA,
   отделить code от payload data, найти tick и unit order logic через traces.
   Указывать confidence и image identity для любого названия функции.
10. Только после этого проверять win/lose, переходы и одну полную кампанию.

Ни одно из этих действий не требует Enhanced ветки, новых домов, AI enhancement,
баланса, unit-limit hacks или переписывания игрового движка.
