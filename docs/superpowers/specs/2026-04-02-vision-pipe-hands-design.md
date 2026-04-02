# vision-pipe v2: Глаза + Руки — единый MCP для управления компьютером

**Дата:** 2026-04-02
**Статус:** Draft
**Расширяет:** `2026-04-02-vision-pipe-design.md`

## Проблема

vision-pipe v1 даёт агенту глаза, но не руки. Для полноценной работы с компьютером агент должен видеть И действовать из одного инструмента. Сейчас desktop-control — это отдельный ClawHub скилл с отдельной настройкой, отдельными зависимостями, и он не интегрирован с зрением.

## Решение

Расширить vision-pipe MCP-сервер: один пакет (`pip install vision-pipe`), один MCP = глаза + руки + системный промпт. Агент подключает один MCP и сразу может видеть экран и управлять компьютером.

## Ключевые принципы

- **vision-pipe = инструмент, не агент.** Он не планирует, не принимает решений. Мейн агент (Claude Code, OpenClaw, любой MCP-клиент) командует, vision-pipe выполняет.
- **Периферия = OCR (всегда доступна, бесплатна).** Apple Vision Framework для быстрого чтения текста с координатами.
- **Фовеа = мейн агент.** Когда нужно детальное визуальное понимание, агент смотрит на скриншот сам через свои VLM-capabilities.
- **Fallback для агентов без VLM.** Опциональный `vision_analyze` через внешнюю VLM (OpenRouter) для агентов на кастомных провайдерах без vision.

## Архитектура зрения (три уровня)

```
Мейн агент просит "посмотри":
  
  Уровень 1: vision_read_window (OCR)
  → Текст + координаты каждого слова
  → Всегда работает, ~1s, бесплатно
  → Достаточно для 80% задач

  Уровень 2: vision_screenshot
  → PNG изображение окна/экрана  
  → Агент сам смотрит через свою VLM
  → Для визуального понимания (UI, графики, дизайн)

  Уровень 3: vision_analyze (опциональный)
  → Отправляет скриншот во внешнюю VLM (OpenRouter)
  → Для агентов без VLM, когда OCR мало
  → Требует API ключ, ~3-16s
```

## MCP Tools

### vision_* (глаза)

| Tool | Описание | Возвращает |
|------|----------|------------|
| `vision_list_windows` | Все открытые окна | `[{app, title, width, height, window_id}]` |
| `vision_get_state` | Текущее состояние экрана: окна + OCR активного | `{windows, active_window, active_window_text}` |
| `vision_read_window(app?, index?)` | OCR текст конкретного окна **с координатами** | `{app, title, text, elements: [{text, x, y, w, h}]}` |
| `vision_screenshot(app?, region?)` | Скриншот окна или области как PNG (base64) | `{image_base64, width, height}` |
| `vision_analyze(app?, prompt?)` | Анализ через внешнюю VLM (OpenRouter). Опциональный. | `{description, extracted_data}` |
| `vision_get_changes` | Что изменилось на экране | `{changes: [{time, delta}]}` |

### action_* (руки)

| Tool | Параметры | Описание |
|------|-----------|----------|
| `action_click(x, y, button?, clicks?)` | x, y: int; button: left/right/middle; clicks: 1/2/3 | Клик по координатам |
| `action_double_click(x, y)` | x, y: int | Двойной клик |
| `action_right_click(x, y)` | x, y: int | Правый клик |
| `action_type_text(text, interval?)` | text: str; interval: float (0=мгновенно) | Ввод текста |
| `action_press(key, presses?)` | key: str; presses: int | Нажатие клавиши (enter, tab, escape и др.) |
| `action_hotkey(keys)` | keys: list[str] | Комбинация клавиш (["cmd","c"], ["cmd","tab"]) |
| `action_scroll(amount, x?, y?, direction?)` | amount: int (+ вверх, - вниз); direction: vertical/horizontal | Скролл |
| `action_drag(start_x, start_y, end_x, end_y, duration?)` | координаты начала и конца | Drag & drop |
| `action_move_mouse(x, y)` | x, y: int | Переместить курсор |
| `action_activate_window(app)` | app: str | Вывести окно на передний план |
| `action_clipboard_copy(text)` | text: str | Скопировать текст в буфер обмена |
| `action_clipboard_paste()` | — | Вставить из буфера |

### system_* (сервис)

| Tool | Описание |
|------|----------|
| `system_check_permissions` | Проверить Accessibility permissions для управления |
| `system_get_mouse_position` | Текущие координаты курсора |
| `system_get_screen_size` | Размер экрана в пикселях |

## MCP Instructions (системный промпт)

Возвращается агенту при подключении через MCP `instructions` поле:

```
vision-pipe: Human-like computer perception and control for AI agents.

WHAT THIS IS:
You have eyes and hands. You can see everything on the user's screen 
and interact with any application — click, type, scroll, drag.
Use this when the user asks you to do something on their computer,
research information in the browser, check an app, or interact with any UI.

WHAT YOU CAN SEE (vision_* tools):
- vision_list_windows — all open windows (app name, title, size)
- vision_get_state — current screen: window list + text of active window
- vision_read_window(app) — read all text in a specific app via OCR (includes coordinates)
- vision_screenshot(app) — get screenshot as image (use if you can process images)
- vision_analyze(app, prompt) — analyze via external VLM (if you can't process images and OCR isn't enough)
- vision_get_changes — what changed on screen since last check

WHAT YOU CAN DO (action_* tools):
- action_click(x, y) — click at screen coordinates
- action_type_text(text) — type text at cursor position
- action_press(key) — press a key (enter, tab, escape, etc.)
- action_hotkey(keys) — keyboard shortcut (["cmd","c"], ["cmd","tab"])
- action_scroll(amount) — scroll up (positive) / down (negative)
- action_drag(x1, y1, x2, y2) — drag and drop
- action_activate_window(app) — bring app to front
- action_clipboard_copy/paste — clipboard operations

HOW TO WORK:
1. LOOK — see what's on screen (vision_list_windows → vision_read_window)
2. DECIDE — plan your next action based on what you see
3. ACT — perform one action (action_click, action_type_text, etc.)
4. LOOK — verify the action worked
5. REPEAT until task is complete

CHOOSING HOW TO LOOK:
- If you can process images: use vision_screenshot for detailed visual analysis
- For text-heavy content: use vision_read_window (OCR with coordinates)
- If you need visual understanding but can't process images: use vision_analyze

FINDING CLICK TARGETS:
vision_read_window returns text with coordinates: {"text": "Sign In", "x": 540, "y": 320, "w": 80, "h": 24}
To click "Sign In": action_click(580, 332) — use center of the bounding box.

IMPORTANT:
- Always LOOK before acting — you need coordinates
- Always LOOK after acting — verify it worked
- Call action_activate_window before interacting with a background app
- If system_check_permissions reports errors, tell the user to enable Accessibility access
- Coordinates are screen pixels. (0,0) = top-left corner.
```

## OCR с координатами

Ключевое улучшение v2: `vision_read_window` возвращает не просто текст, а **элементы с координатами**:

```json
{
  "app": "Chrome",
  "title": "Google",
  "text": "Google\nSearch Google or type a URL\nGmail\nImages",
  "elements": [
    {"text": "Google", "x": 620, "y": 280, "w": 180, "h": 50},
    {"text": "Search Google or type a URL", "x": 400, "y": 400, "w": 520, "h": 36},
    {"text": "Gmail", "x": 1100, "y": 30, "w": 50, "h": 18},
    {"text": "Images", "x": 1160, "y": 30, "w": 55, "h": 18}
  ]
}
```

Агент видит текст И знает куда кликнуть. Не нужен VLM чтобы найти кнопку "Sign In" — OCR даёт координаты.

Apple Vision Framework уже возвращает bounding boxes — нужно только передать их наружу.

## vision_analyze (опциональный VLM)

Для агентов без VLM (кастомные провайдеры), когда OCR недостаточно:

```yaml
# vision-pipe.yaml
analyze:
  provider: openrouter
  model: google/gemma-3-4b-it:free
  api_key: ${OPENROUTER_API_KEY}  # или env variable
```

Вызов: `vision_analyze(app="Chrome", prompt="What products are shown?")` — отправляет скриншот в OpenRouter, возвращает текстовый ответ.

Это опция, не требование. Если нет ключа — tool просто не регистрируется.

## Структура файлов (изменения)

```
src/vision_pipe/
├── core/
│   ├── capture.py       # уже есть — без изменений
│   ├── detector.py      # уже есть — без изменений
│   ├── ocr.py           # ИЗМЕНИТЬ: добавить bounding boxes
│   ├── actions.py       # НОВЫЙ: все action_* через pyautogui
│   └── permissions.py   # НОВЫЙ: проверка Accessibility
├── providers/
│   └── openrouter.py    # НОВЫЙ: OpenRouter VLM для vision_analyze
├── server/
│   └── mcp.py           # ИЗМЕНИТЬ: добавить action_* и system_* tools
└── cli.py               # ИЗМЕНИТЬ: обновить serve с новыми tools
```

## Зависимости

Новые:
- `pyautogui` — мышь, клавиатура, скролл
- `pyperclip` — буфер обмена

Опциональные:
- `opencv-python` — find_on_screen (поиск по картинке)

```toml
[project.optional-dependencies]
actions = ["pyautogui>=0.9", "pyperclip>=1.8"]
opencv = ["opencv-python>=4.8"]
analyze = ["httpx>=0.27"]  # для OpenRouter
```

## Платформа

- macOS only (v1)
- Требует Accessibility permissions для action_* tools
- `system_check_permissions` проверяет и возвращает инструкции

## Что НЕ входит в v2

- Мульти-монитор (позже)
- Linux/Windows поддержка (позже)
- Автономное планирование (vision-pipe = инструмент, не агент)
- Потоковое видео / непрерывный мониторинг (позже)
