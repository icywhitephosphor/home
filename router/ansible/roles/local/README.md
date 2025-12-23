# Роль Ansible `local`

Настройка sing-box на macOS для селективного роутинга доменов через VPN.  
Идеально для работы в офисе, когда нет доступа к домашнему роутеру.

## Быстрый старт

```bash
cd router/ansible

# Ручной запуск (по умолчанию)
ansible-playbook playbooks/local.yml

# Другие режимы запуска
ansible-playbook playbooks/local.yml -e local_runtime=brew      # brew services
ansible-playbook playbooks/local.yml -e local_runtime=launchd   # LaunchAgent
ansible-playbook playbooks/local.yml -e local_runtime=docker    # Docker container
```

## Как это работает

```
┌─────────────────┐     ┌──────────────┐     ┌─────────────┐
│  Browser/App    │────▶│   sing-box   │────▶│  VPN Server │
│  (PAC/proxy)    │     │  :2080       │     │  (VLESS)    │
└─────────────────┘     └──────────────┘     └─────────────┘
        │                      │
        │ (остальной трафик)   │ (VPN домены)
        ▼                      ▼
    ┌────────┐            ┌────────┐
    │ DIRECT │            │ openai │
    │        │            │ google │
    └────────┘            │ claude │
                          │  ...   │
                          └────────┘
```

1. Генерирует конфиг в `~/.config/sing-box/`
2. Поднимает HTTP/SOCKS5 прокси на `127.0.0.1:2080`
3. Создаёт PAC файл для автоматической маршрутизации
4. Домены из списков идут через VPN, остальное — напрямую

## Режимы запуска

| Режим | Описание |
|-------|----------|
| `binary` | Установка sing-box + скрипт для ручного запуска |
| `brew` | Управление через `brew services` |
| `launchd` | macOS LaunchAgent (автозапуск) |
| `docker` | Контейнер (только proxy mode) |

## Настройка браузера

### Вариант 1: PAC файл (рекомендуется)
```
System Settings → Network → Wi-Fi → Details → Proxies
→ Automatic Proxy Configuration
→ URL: file:///Users/<username>/.config/sing-box/proxy.pac
```

### Вариант 2: Ручной прокси
```
System Settings → Network → Wi-Fi → Details → Proxies
→ Web Proxy (HTTP): 127.0.0.1:2080
→ Secure Web Proxy (HTTPS): 127.0.0.1:2080
```

### Вариант 3: Только браузер
- **Firefox**: Settings → Network Settings → Manual proxy → HTTP: 127.0.0.1:2080
- **Chrome**: используйте расширение Proxy SwitchyOmega

## Управление

```bash
# binary режим
~/.config/sing-box/run-sing-box.sh

# brew режим
brew services info sing-box
brew services restart sing-box

# launchd режим
launchctl list | grep sing-box
launchctl kickstart -k gui/$(id -u)/com.sing-box

# docker режим
docker ps | grep sing-box
docker logs -f sing-box

# Логи
tail -f ~/Library/Logs/sing-box.log
```

## Переменные

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `local_runtime` | Режим запуска | `binary` |
| `local_singbox_mode` | `proxy` или `tun` | `proxy` |
| `local_proxy_http_port` | Порт прокси | `2080` |
| `local_enabled_domains` | Список доменов | см. defaults |
| `local_singbox_outbound` | Настройки VPN | см. group_vars |

## Добавление доменов

Домены берутся из `roles/router/files/ipv4/*.lst`. Чтобы включить/выключить:

```yaml
# defaults/main.yml или group_vars
local_enabled_domains:
  - openai
  - google
  - claude
  # - telegram  # закомментировать для отключения
```

## Совместимость с рабочим VPN

В режиме `proxy` роль **не конфликтует** с рабочим VPN:
- Рабочий VPN обрабатывает весь трафик как обычно
- Приложения с настроенным прокси → sing-box → личный VPN
- Остальные приложения → рабочий VPN / напрямую

## Структура

```
roles/local/
├── defaults/main.yml      # Переменные по умолчанию
├── handlers/main.yml      # Хендлеры для перезапуска
├── tasks/
│   ├── main.yml          # Основная логика
│   ├── pac.yml           # Генерация PAC файла
│   ├── binary.yml        # Ручной запуск
│   ├── brew.yml          # brew services
│   ├── launchd.yml       # LaunchAgent
│   └── docker.yml        # Docker container
└── templates/
    ├── config.json.j2    # Конфиг sing-box
    ├── proxy.pac.j2      # PAC файл
    └── com.sing-box.plist.j2
```
