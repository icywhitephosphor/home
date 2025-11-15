# [Прошивка и автоматизация Xiaomi AX3200](https://openwrt.org/toh/xiaomi/ax3200)

## 1. Подготовка и прошивка
1. Скачайте патчер и подготовьте окружение:

   ```shell
   git clone https://github.com/openwrt-xiaomi/xmir-patcher.git
   cd xmir-patcher
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   chmod +x run.sh && ./run.sh
   ```

2. Подключитесь к роутеру (`ssh` или `telnet`):

   ```shell
   ssh -v -oHostKeyAlgorithms=+ssh-rsa root@192.168.31.1
   ```

3. Уточните ревизию:

   ```shell
   dd if=/dev/mtd2 2>/dev/null | grep -cF " 2022 - "
   dd if=/dev/mtd2 2>/dev/null | grep -cF "do_env_export"
   dd if=/dev/mtd2 2>/dev/null | grep -cF "GigaDevice"
   ```

4. Настройте `nvram`:
   - **Версия 0 (старая):**

     ```shell
     nvram set ssh_en=1
     nvram set uart_en=1
     nvram set boot_wait=on
     nvram set flag_boot_success=1
     nvram set flag_try_sys1_failed=0
     nvram set flag_try_sys2_failed=0
     nvram commit
     ```

   - **Версия 1 (новая):**

     ```shell
     nvram set boot_fw1="run boot_rd_img;bootm"
     nvram set flag_try_sys1_failed=8
     nvram set flag_try_sys2_failed=8
     nvram set flag_boot_rootfs=0
     nvram set flag_boot_success=1
     nvram set flag_last_success=1
     nvram commit
     ```

5. Перепрошейте устройство (после перезагрузки адрес сменится на `192.168.1.1`):

   ```shell
   cd /tmp
   wget http://downloads.openwrt.org/releases/23.05.5/targets/mediatek/mt7622/openwrt-23.05.5-mediatek-mt7622-xiaomi_redmi-router-ax6s-squashfs-factory.bin
   mv openwrt-23.05.5-mediatek-mt7622-xiaomi_redmi-router-ax6s-squashfs-factory.bin factory.bin
   mtd -r write factory.bin firmware
   ```

Подключиться сразу получится только по кабелю — это нормально.

## 2. Первичная настройка Wi-Fi
```shell
uci show wireless                 # просмотр конфигурации
wifi status                       # проверка статуса
uci set wireless.@wifi-device[0].disabled=0
uci set wireless.@wifi-device[1].disabled=0
uci set wireless.@wifi-iface[0].ssid='NetworkName'
uci set wireless.@wifi-iface[1].ssid='NetworkName_5G'
uci set wireless.@wifi-iface[0].encryption='psk2'
uci set wireless.@wifi-iface[1].encryption='psk2'
uci set wireless.@wifi-iface[0].key='Password2G'
uci set wireless.@wifi-iface[1].key='Password5G'
uci commit wireless
wifi reload
```

Лучше сразу разделить сети 2.4 и 5 ГГц по разным SSID, тогда устройства смогут правильно выбирать диапазон.

> ⚙️ Все эти команды теперь заведены в роль `wifi` (`router/ansible/roles/wifi`). Можно просто запустить плейбук `playbooks/router_full.yml` — см. раздел «Автоматизация» ниже.

## 3. Точечная маршрутизация через VPN
1. Установите скрипт от itdoginfo:

   ```shell
   sh <(wget -O - https://raw.githubusercontent.com/itdoginfo/domain-routing-openwrt/master/getdomains-install.sh)
   ```

   Выбираем Sing-box (3), затем `DNSCrypt-proxy2` (2) и отмечаем «Россия» (1).

2. Обновите `sing-box`:

   ```shell
   :> /etc/sing-box/config.json && nano /etc/sing-box/config.json
   ```

   Вставьте конфиг (значения сервера/порта/uuid подставьте свои):

   ```json
   {
     "log": { "level": "debug" },
     "inbounds": [
       {
         "type": "tun",
         "interface_name": "tun0",
         "domain_strategy": "ipv4_only",
         "inet4_address": "172.16.250.1/30",
         "auto_route": false,
         "strict_route": false,
         "sniff": true
       }
     ],
     "outbounds": [
       {
         "type": "vless",
         "server": "",
         "server_port": 443,
         "uuid": "",
         "flow": "xtls-rprx-vision",
         "tls": {
           "enabled": true,
           "insecure": false,
           "server_name": "www.yandex.com",
           "utls": { "enabled": true, "fingerprint": "random" },
           "reality": { "enabled": true, "public_key": "", "short_id": "" }
         }
       }
     ],
     "route": { "auto_detect_interface": true }
   }
   ```

3. Перезапустите сервисы:

   ```shell
   service sing-box start
   service network restart
   ```

Без выделенного сервера не обойтись: поднимите его, установите [3x-ui](https://github.com/MHSanaei/3x-ui) и выдайте себе доступ.

> ⚙️ Секция `sing_box` полностью автоматизирована ролью `router/ansible/roles/sing_box`, которая генерирует JSON по шаблону и перезапускает `sing-box` + `network`.

## 4. Доменные списки и `getdomains`
После установки скрипта от itdoginfo обновляйте списки через Ansible или вручную. Если правите руками, помните: после каждого изменения нужно запускать `service getdomains restart`, затем либо `service firewall restart`, либо `nft flush set inet fw4 vpn_domains`, чтобы nft-набор `vpn_domains` подтянул свежий список.

## 5. Автоматизация (Ansible)
В каталоге `router/ansible/` лежат плейбуки:
- `playbooks/domains.yml` — только доменные списки.
- `playbooks/router_full.yml` — домены + Wi-Fi + sing-box.

Перед запуском установите `ansible`, коллекцию `community.general` и python3 на роутере. Команды примерные:

```shell
cd router/ansible
python3 -m venv venv && source venv/bin/activate
pip install ansible
ansible-galaxy collection install community.general
ansible-playbook playbooks/router_full.yml --diff
```

Роль `domains` теперь дополнительно чистит `nft set inet fw4 vpn_domains` и делает `service firewall restart`, так что dnsmasq сразу получает актуальные данные.

## 6. Защита от «кирпича»
В веб-интерфейсе OpenWrt (`http://192.168.1.1`) откройте `System → Startup → Local Startup` и вставьте:

```
fw_setenv flag_try_sys1_failed 0
fw_setenv flag_try_sys2_failed 0

exit 0
```

Затем выполните `reboot` по SSH.

Если что-то пошло совсем не так, восстановиться поможет [MIWIFIRepairTool](https://4pda.to/stat/go?u=http%3A%2F%2Fbigota.miwifi.com%2Fxiaoqiang%2Ftools%2FMIWIFIRepairTool.x86.zip&e=114089118&f=https%3A%2F%2F4pda.to%2Fforum%2Findex.php%3Fshowtopic%3D1033757%26st%3D360%23entry114089118).

