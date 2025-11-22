# Wi-Fi конфигурация в `router_full.yml`

Этот файл описывает, как работают переменные, которые использует роль `roles/wifi`.

## Структура переменных

### `wifi_devices`
- `index` — целое число, которое соответствует порядковому номеру секции `@wifi-device` в конфиге OpenWrt (`0` для первой, `1` для второй и т.д.).
- `enabled` — булево, определяет, будет ли опция `disabled` установленa в `0` (`false` в UCI) или `1` (`true`).
  - Значение `true` означает, что интерфейс должен быть включён.
  - Когда таск `Toggle Wi-Fi devices` запускается, он добавляет `disabled='0'` к соответствующей секции.

### `wifi_ifaces`
- `index` — номер секции `@wifi-iface`, она привязана к устройству из `wifi_devices` (например, `@wifi-iface[0]` работает через `radio0`).
- `enabled` управляет тем же `disabled` через опцию `openwrt_uci_option`, то есть `true` → `disabled='0'`, `false` → `disabled='1'`.
- `options` — список дополнительных настроек, добавляемых через `uci set`. Каждый элемент содержит:
  - `option` — ключ настроек (`ssid`, `encryption`, `key`, `network`, `mode`, и т.п.).
  - `value` — значение, которое будет присвоено.

Роль последовательно выполняет три шага:
1. `Toggle Wi-Fi devices` выставляет `disabled` у `@wifi-device`.
2. `Toggle Wi-Fi interfaces` делает то же самое для `@wifi-iface`.
3. `Apply Wi-Fi interface options` применяет все `options` из списка.

## Как понять, какой индекс к какому диапазону относится
OpenWrt создаёт устройства `radio0`, `radio1` и соответствующие интерфейсы `default_radio0`, `default_radio1`. В стандартной сборке:

| `index` | UCI секция        | Диапазон | Основные параметры                     |
|---------|-------------------|----------|----------------------------------------|
| `0`     | `radio0`/`@wifi-iface[0]` | 2.4 GHz  | `band='2g'`, `htmode='HT20'`, `channel` обычно `1..11` |
| `1`     | `radio1`/`@wifi-iface[1]` | 5 GHz    | `band='5g'`, `htmode='HE80'`, `channel` `36..64` |

В твоём нынешнем `uci show wireless` оба `ssid` совпадают, но по `band` ясно, что `index: 0` отвечает за 2G, `index: 1` — за 5G. Если роутер имеет больше radio, просто расширяй списки: `index: 2` будет третьим радио и т.д.

## Сценарии использования
- Хочешь отключить 2.4 GHz? Поставь `enabled: false` в блоке с `index: 0` и оставь 5G включённым.
- Хочешь обновить ключ или шифрование без трогания `wifi` команды вручную? Измени `options` и запусти плейбук — все параметры применятся через `uci set` и handler `commit_and_reload_wifi`.
- При необходимости подключить отдельные сети на каждом диапазоне добавь `ssid`/`key` в `options` и любую другую опцию (`network`, `mode`, `device`, `hidden`, `wpa3`, и т.д.). Роль просто пробегает список `wifi_ifaces` и применяет всё по очереди.

## Пример
```yaml
wifi_devices:
  - index: 0
    enabled: true     # radio0 (2.4 GHz)
  - index: 1
    enabled: true     # radio1 (5 GHz)

wifi_ifaces:
  - index: 0
    enabled: true
    options:
      - option: ssid
        value: "OpenWRT_333"
      - option: encryption
        value: "psk2+sae"
      - option: key
        value: "AKcxUKhP"
  - index: 1
    enabled: true
    options:
      - option: ssid
        value: "OpenWRT_333"
      - option: encryption
        value: "psk2+sae"
      - option: key
        value: "AKcxUKhP"
```

Эта конфигурация включает оба диапазона и устанавливает одинаковые параметры. Плейбук снимет состояние `disabled` прямо в конфиге и сделает `wifi reload` через handler.
