# Local Role (macOS sing-box)

Роль для настройки sing-box на локальном Mac как SOCKS5/HTTP прокси для обхода блокировок.

## Возможности

- Несколько режимов запуска: `binary`, `brew`, `launchd`, `docker`
- Proxy и TUN режимы работы
- IPv4/IPv6 поддержка
- PAC файл с автоматическим определением доменов
- urltest для автовыбора лучшего VPN сервера
- VLESS + Reality + uTLS

## Быстрый старт

```bash
# 1. Скопировать и заполнить секреты
cp envs/local/group_vars/vpn_secrets.yml.example envs/local/group_vars/vpn_secrets.yml
# Отредактировать vpn_secrets.yml - указать свои серверы

# 2. Запустить плейбук
ansible-playbook -i envs/local playbooks/local.yml

# 3. Запустить sing-box
~/.config/sing-box/run-sing-box.sh

# 4. Настроить браузер на использование прокси
# HTTP Proxy: 127.0.0.1:2080
# Или PAC: file://~/.config/sing-box/proxy.pac
```

## Конфигурация

### Файлы

| Файл | Описание |
|------|----------|
| `envs/local/group_vars/localhost.yml` | Основные настройки |
| `envs/local/group_vars/vpn_secrets.yml` | VPN серверы (секреты) |
| `roles/local/defaults/main.yml` | Значения по умолчанию |

### Переменные

```yaml
# Runtime: binary | brew | launchd | docker
local_runtime: binary

# Режим: proxy (рекомендуется) | tun
local_singbox_mode: proxy

# IPv6 support
local_ipv6_enabled: true

# Порт прокси
local_proxy_http_port: 2080

# Включение доменов
local_domains:
  openai: true
  claude: true
  google: true
  # ... и т.д.

# Внешние источники доменов для PAC
local_pac_extra_sources:
  - "https://raw.githubusercontent.com/itdoginfo/allow-domains/main/Russia/inside-dnsmasq-ipset.lst"
```

### VPN серверы (vpn_secrets.yml)

```yaml
local_singbox_servers:
  - name: amsterdam
    server: "1.2.3.4"
    server_ipv6: "2001:db8::1"
    uuid: "your-uuid"
    short_id: "abc123"
    public_key: "your-public-key"

local_singbox_outbound_common:
  tag: vpn-out
  type: vless
  server_port: 8443
  flow: xtls-rprx-vision
  tls:
    enabled: true
    server_name: "example.com"
  utls:
    enabled: true
    fingerprint: chrome
  reality:
    enabled: true
```

## Режимы запуска

| Режим | Описание | Автозапуск |
|-------|----------|------------|
| `binary` | Ручной запуск через скрипт | Нет |
| `brew` | `brew services` | Да |
| `launchd` | macOS LaunchAgent | Да |
| `docker` | Docker контейнер | Да |

## Списки доменов

Используются `.lst` файлы из роли `router` (`roles/router/files/ipv4/*.lst`).

Доступные списки:
- `antigravity` - Google AI Studio, Gemini
- `claude` - Anthropic Claude
- `copilot` - GitHub Copilot
- `datadog` - Datadog monitoring
- `google` - Google services
- `instagram` - Instagram
- `linkedin` - LinkedIn
- `netflix` - Netflix
- `openai` - OpenAI, ChatGPT
- `telegram` - Telegram
- `windsurf` - Windsurf IDE
- `x` - X (Twitter)

## Tags

```bash
# Только PAC файл
ansible-playbook -i envs/local playbooks/local.yml --tags pac

# Только sing-box конфиг
ansible-playbook -i envs/local playbooks/local.yml --tags config

# Очистка старых файлов
ansible-playbook -i envs/local playbooks/local.yml --tags cleanup
```

## Troubleshooting

```bash
# Проверить конфиг
sing-box check -c ~/.config/sing-box/config.json

# Запустить с debug
sing-box run -c ~/.config/sing-box/config.json

# Проверить прокси
curl -x http://127.0.0.1:2080 https://api.openai.com/v1/models
```
