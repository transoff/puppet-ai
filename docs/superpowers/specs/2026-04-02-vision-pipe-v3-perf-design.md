# vision-pipe v3: Accessibility API + Speed + Smart Actions

**Дата:** 2026-04-02
**Статус:** Draft
**Расширяет:** v2 (hands design)

## Проблемы v2

1. **OCR не знает что кликабельно** — видит текст "Image" но не знает что рядом чекбокс. Клики по веб-элементам попадают мимо.
2. **OCR медленный для циклов** — 0.5s на каждый вызов. LOOK→ACT→LOOK = 1s+ только на зрение.
3. **sleep() вместо умного ожидания** — агент спит 3s после каждого действия, не зная загрузилась ли страница.
4. **Нет кэша** — одно и то же окно читается 5 раз подряд за 5×0.5s.

## Решения

### 1. Accessibility API — `vision_ui_elements`

Новый tool через macOS Accessibility API (`AXUIElement` из ApplicationServices). Возвращает дерево UI-элементов: кнопки, чекбоксы, текстовые поля, ссылки — с ролями, значениями и точными координатами.

```json
{
  "elements": [
    {"role": "button", "title": "Back", "x": 30, "y": 52, "w": 28, "h": 28},
    {"role": "textField", "title": "Address", "value": "openrouter.ai/models", "x": 200, "y": 48, "w": 800, "h": 32},
    {"role": "checkbox", "title": "Image", "checked": false, "x": 85, "y": 389, "w": 16, "h": 16},
    {"role": "link", "title": "Gemma 4", "x": 120, "y": 450, "w": 200, "h": 24}
  ]
}
```

Тот же API что macOS VoiceOver. Работает во всех приложениях. Координаты уже в экранных пикселях. Не нужен OCR для определения кликабельных элементов.

Требования: Accessibility permissions (уже требуются для pyautogui).

Параметры: `vision_ui_elements(app?, role_filter?, max_depth?)` — можно фильтровать по роли (только кнопки, только текстовые поля).

### 2. OCR Fast Mode + Кэш

Два режима OCR:
- `fast` — `VNRequestTextRecognitionLevelFast` (~0.1s). Для action-tools где нужна скорость.
- `accurate` — текущий `VNRequestTextRecognitionLevelAccurate` (~0.5s). Для vision_read_window.

Кэш OCR результатов:
- Хранить последний результат per window_id + pixel hash
- Если запрос к тому же окну и pixel diff < threshold и < 2 секунд — вернуть из кэша (~0ms)
- Инвалидировать после любого action_* tool call

### 3. action_click_and_wait — умный клик с ожиданием

Один tool заменяет click + sleep + read_window:

1. Находит текст через Accessibility API (приоритет) или OCR (fallback)
2. Делает скриншот ДО клика
3. Кликает
4. Каждые 0.2s проверяет pixel diff
5. Когда diff < threshold 3 кадра подряд — экран стабилизировался
6. OCR нового состояния
7. Возвращает: что кликнул, сколько ждал, новый текст экрана

```json
{
  "status": "ok",
  "clicked": "Sign In",
  "x": 540, "y": 332,
  "waited": 1.2,
  "screen_changed": true,
  "new_text_preview": "Welcome back, user..."
}
```

Параметры: `action_click_and_wait(text, app?, timeout=5, use_accessibility=true)`

## Новые tools

| Tool | Описание |
|------|----------|
| `vision_ui_elements(app?, role_filter?, max_depth?)` | Дерево UI элементов через Accessibility API |
| `action_click_and_wait(text, app?, timeout?)` | Клик + ожидание стабилизации + OCR результата |

Модифицированные:
- `vision_read_window` — использует кэш, fast/accurate mode
- `action_click_text` — пробует Accessibility API перед OCR

## Структура файлов

```
src/vision_pipe/core/
├── accessibility.py   # НОВЫЙ: AXUIElement wrapper
├── ocr.py             # ИЗМЕНИТЬ: fast mode + cache
├── ocr_cache.py       # НОВЫЙ: кэш OCR результатов
└── wait.py            # НОВЫЙ: pixel diff wait logic
```

## Зависимости

- `pyobjc-framework-ApplicationServices` — уже установлен (через Quartz)
- Никаких новых внешних зависимостей

## MCP Instructions дополнение

```
PRECISE CLICKING:
- For UI elements (buttons, checkboxes, links): use vision_ui_elements(app) — gives exact clickable areas
- For text content: use vision_read_window(app) — gives text with coordinates
- action_click_and_wait(text, app) — clicks and waits for result automatically, no sleep() needed

SPEED TIPS:
- vision_read_window uses cache — calling it twice quickly costs nothing
- After any action, cache is cleared automatically
- Use action_click_and_wait instead of click + sleep + read — it's faster and smarter
```
