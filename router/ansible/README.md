## Автоматизация OpenWrt через Ansible

В каталоге `router/ansible/` лежат плейбуки и роли, которые повторяют ручные действия из основного README.

### Структура
- `ansible.cfg` — задаёт `inventory` и `roles_path`.
- `envs/hosts.ini` — инвентарь (по умолчанию `192.168.1.1`, пользователь `root`).
- `playbooks/domains.yml` — только обновление `getdomains` и списков доменов.
- `playbooks/router_full.yml` — полный цикл: домены + Wi-Fi + sing-box.
- `roles/domains` — управление списками доменов и скриптом `getdomains`.
- `roles/wifi` — конфигурация Wi-Fi через UCI (нужна коллекция `community.general`).
- `roles/sing_box` — шаблон `config.json` и перезапуск служб.

### Подготовка
1. Настройте доступ по SSH к роутеру (`root@192.168.1.1`).
2. На управляющей машине установите зависимости:

```bash
python3 -m venv venv
source venv/bin/activate
pip install ansible
ansible-galaxy collection install community.general
```

### Запуск
- Только домены:

```bash
ansible-playbook playbooks/domains.yml --diff
```

- Полная настройка (домены + Wi-Fi + sing-box):

```bash
ansible-playbook playbooks/router_full.yml --diff
```

Добавьте `-k`, если требуется ввод пароля. Для dry-run используйте `--check`.

### Роль `domains`
- Создаёт `/tmp/dnsmasq.d` и копирует туда все `*.lst` c бэкапами.
- Переносит шаблон `getdomains.sh.j2` в `/etc/init.d/getdomains` с правами `0755`.
- После изменений запускает `getdomains`, очищает `nft set inet fw4 vpn_domains` и перезапускает firewall, чтобы `dnsmasq` увидел свежий `domains.lst`.
- Переменные (`roles/domains/defaults/main.yml`) позволяют включать/отключать списки: `domains_copilot`, `domains_figma`, `domains_google`, `domains_instagram`, `domains_netflix`, `domains_telegram`, `domains_datadog`.

### Роль `wifi`
- Показывает текущий `uci show wireless` и `wifi status`.
- Управляет включением радиомодулей (`wireless.@wifi-device[*].disabled`).
- Обновляет параметры интерфейсов (`ssid`, `encryption`, `key`) через `community.general.uci`.
- После любых изменений вызывает хендлер, который делает `uci commit wireless` и `wifi reload`.
- Параметры лежат в `roles/wifi/defaults/main.yml` и описывают список устройств/интерфейсов.

### Роль `sing_box`
- Создаёт каталог `/etc/sing-box`, развертывает `config.json` из шаблона и делает бэкап старого файла.
- При необходимости включает автозапуск (`/etc/init.d/sing-box enable`).
- Хендлер перезапускает `sing-box`, а затем (если `sing_box_apply_network_restart: true`) перезапускает `network`.
- Значения для шаблона задаются в `roles/sing_box/defaults/main.yml`.

### Полезные замечания
- Убедитесь, что на роутере установлен `python3` (OpenWrt по умолчанию его не содержит).
- Для удобства добавьте свой публичный ключ в `/root/.ssh/authorized_keys`, чтобы Ansible не спрашивал пароль.
- Если нужно сбросить только nft-набор без перезапуска firewall, выставьте `notify` только на `rebuild_domains` (см. `roles/domains/tasks/main.yml`).
