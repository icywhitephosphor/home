# Роль Ansible `router`

Русскоязычная, предельно подробная документация для роли, которая превращает OpenWrt‑роутер в «умный шлюз»: он сам поднимает сеть, режет домены по спискам, прогоняет трафик через sing-box (VLESS Reality), генерит PAC, собирает Wi‑Fi и не даёт QUIC уехать мимо VPN.

## Зачем всё это

- единая точка управления домашним маршрутизатором без ручного ковыряния в LuCI;
- гарантированная маршрутизация «чувствительных» доменов (OpenAI, Copilot, Google, Netflix и т. д.) через шифрованный туннель;
- автоматическая генерация PAC/прокси для клиентов и Wi‑Fi конфигов;
- воспроизводимое состояние через Ansible: одна команда возвращает железку в рабочее состояние.

## Ключевые возможности

- **Network** – LAN/WAN, DNS, dhcp, nftables, марк‑маршрутизация, запрет QUIC (UDP 443) до VPN.
- **Domains** – wildcard‑списки доменов с хранением в `/etc/dnsmasq.d/*.lst`, автоматическое наполнение nft‑сет `vpn_domains` и очистка старых IP.
- **PAC** – статический `proxy.pac` и `wpad.dat`, чтобы macOS/Windows/браузеры сходу брали правильный маршрут.
- **Singbox** – полноценный конфиг VLESS Reality + tun inbound + policy routing, логи, uTLS, short_id, всё что надо.
- **WiFi** – описываем радиомодули и SSID в переменных, роль сама перегенерирует `/etc/config/wireless`.
- **Безопасность** – шаблоны с проверками, деплой через handlers, автокопии оригинальных файлов, строгие umask.

## Архитектура в двух словах

1. dnsmasq читает wildcard‑листы и вытягивает IP‑адреса.
2. скрипт‑хук передаёт адреса в nftables‑сет `vpn_domains` (persist).
3. firewall помечает трафик c fwmark `0x1`, блокирует QUIC и гонит помеченное в policy‑таблицу.
4. ip rule + ip route отправляют fwmark в tun0 sing-box.
5. sing-box поднимает Reality‑туннель и возвращает трафик наружу.
6. PAC/прокси используются клиентами (macOS, Firefox, VS Code и т. д.).

## Требования и подготовка

- OpenWrt ≥ 23.05 (желательно свежие снапшоты 24.xx).
- установленные пакеты: `sing-box`, `dnsmasq-full`, `nftables`, `curl`, `coreutils`.
- Python 3.11+ на роутере (входит в `python3-light` пакеты).
- SSH-доступ по ключу с правами root.
- Инвентарь вида `envs/router/hosts.ini`, где целевой хост в группе `router`.

## Как запускать

```bash
# Полное применение со всеми проверками
ansible-playbook playbooks/router.yml -i envs/router/hosts.ini

# Только доменные списки и firewall
ansible-playbook playbooks/router.yml -t domains,network

# Пересобрать sing-box и перезапустить сервис
ansible-playbook playbooks/router.yml -t singbox

# Перекатить PAC/прокси для клиентских машин
ansible-playbook playbooks/router.yml -t pac
```

## Теги роли

| Тег       | Что трогает                                               |
| --------- | --------------------------------------------------------- |
| `network` | /etc/config/network, firewall, dnsmasq, policy routing    |
| `domains` | wildcard‑листы, nftables‑сеты, хук dnsmasq                |
| `pac`     | `proxy.pac`, `wpad.dat`, lighttpd/uci настройки и шаблоны |
| `singbox` | `/etc/sing-box/config.json`, init.d, ключи Reality        |
| `wifi`    | `/etc/config/wireless`, радиомодули, SSID                 |

Можно комбинировать: `--tags domains,singbox` обновит только нужные куски.

## Основные переменные

Все значения по умолчанию лежат в `roles/router/defaults/main.yml`. В `group_vars/router.yml` переопределяем только то, что реально отличается.

### Система и сеть

```yaml
router_ipv6_enabled: false        # жёстко гасим IPv6, если не нужен
router_network_lan_ipaddr: 192.168.1.1
router_network_wan_proto: dhcp    # dhcp | static | pppoe
router_dns_upstream: [1.1.1.1, 8.8.8.8]
```

### Доменные списки (wildcard)

```yaml
router_domains_openai: true
router_domains_copilot: true
router_domains_google: true
router_domains_instagram: true
router_domains_netflix: true
router_domains_datadog: true
router_domains_telegram: false
```

Каждый список держим минимальным: только apex + `/.example.com/`. Файлы попадают в `/etc/dnsmasq.d/*.lst`, хук `dnsmasq.d/domainlist.sh` пересобирает nft‑сет. Любой новый список достаточно включить переменной и добавить шаблон `.lst`.

### Sing-box

```yaml
router_singbox_log_level: error
router_singbox_inbound:
  interface_name: tun0
  inet4_address: 172.16.250.1/30
  domain_strategy: ipv4_only
router_singbox_route:
  auto_detect_interface: true
router_singbox_outbound:
  server: vpn.example.com
  server_port: 443
  uuid: "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
  flow: xtls-rprx-vision
  tls:
    server_name: www.cloudflare.com
  reality:
    enabled: true
    public_key: "..."
    short_id: "abcd"
```

Поддерживается uTLS, packet_encoding, альтернативные стеки (`system`, `gvisor`, `mixed`). Меняем только то, что необходимо для конкретного сервера.

### PAC и прокси

```yaml
router_proxy_enabled: true
router_proxy_port: 2080
router_pac_url: http://192.168.1.1/proxy.pac
```

PAC автоматически подсовывает прокси только тем доменам, которые идут через VPN (зеркалит содержимое nft‑сета).

### Wi‑Fi

```yaml
router_wifi_devices:
  - index: 0
    enabled: true
router_wifi_ifaces:
  - index: 0
    enabled: true
    options:
      - option: ssid
        value: "MyNetwork_2G"
      - option: encryption
        value: "psk2+sae"
      - option: key
        value: "SuperStrongPassword"
```

Любые дополнительные настройки (isolation, ieee80211k/r/v) можно перечислить в `options`.

## Типовой `group_vars/router.yml`

```yaml
---
router_domains_openai: true
router_domains_copilot: true
router_domains_google: true

router_singbox_outbound:
  server: vpn.example.com
  server_port: 443
  uuid: 11111111-2222-3333-4444-555555555555
  tls:
    server_name: www.cloudflare.com
  reality:
    enabled: true
    public_key: FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFU
    short_id: deadbeef

router_wifi_ifaces:
  - index: 0
    enabled: true
    options:
      - option: ssid
        value: "Example_2G"
      - option: key
        value: "ChangeMeStrongPass"
```

Остальное тянется из дефолтов.

## Проверки после деплоя

```bash
# nftables сет с доменами
nft list set inet fw4 vpn_domains

# dnsmasq видит wildcard
grep 'googlevideo' /etc/dnsmasq.d/*.lst

# sing-box процесс
ps | grep sing-box

# PAC отдаётся веб-сервером
curl -I http://192.168.1.1/proxy.pac
```

## Частые кейсы

1. **Добавить новый список доменов**: завести шаблон `templates/domains/<name>.lst.j2`, включить переменную `router_domains_<name>: true`, прогнать `--tags domains`.
2. **Переключить провайдера VPN**: отредактировать `router_singbox_outbound` и запустить `--tags singbox`.
3. **Временно выключить PAC**: `router_proxy_enabled: false`, затем `--tags pac`.

## Лицензия / автор

MIT. Личный use-case для OpenWrt‑роутера, но спокойно переиспользуйте и кастомизируйте.
