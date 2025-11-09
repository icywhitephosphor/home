#!/bin/sh /etc/rc.common

START=99

start () {
    DOMAINS=https://raw.githubusercontent.com/itdoginfo/allow-domains/main/Russia/inside-dnsmasq-nfset.lst
    count=0
    while true; do
        if curl -m 3 github.com; then
            curl -f $DOMAINS --output /tmp/dnsmasq.d/domains.lst
            break
        else
            echo "GitHub is not available. Check the internet availability [$count]"
            count=$((count+1))
        fi
    done
    sed -i '/kinovod/d' /tmp/dnsmasq.d/domains.lst
    
    # Добавляем локальные файлы
    [ -f /tmp/dnsmasq.d/google.txt ] && cat /tmp/dnsmasq.d/google.txt >> /tmp/dnsmasq.d/domains.lst
    [ -f /tmp/dnsmasq.d/telegram.txt ] && cat /tmp/dnsmasq.d/telegram.txt >> /tmp/dnsmasq.d/domains.lst
    [ -f /tmp/dnsmasq.d/instagram.txt ] && cat /tmp/dnsmasq.d/instagram.txt >> /tmp/dnsmasq.d/domains.lst
    
    # Удаляем дубликаты
    sort /tmp/dnsmasq.d/domains.lst | uniq > /tmp/dnsmasq.d/domains.lst.tmp
    mv /tmp/dnsmasq.d/domains.lst.tmp /tmp/dnsmasq.d/domains.lst
    
    if dnsmasq --conf-file=/tmp/dnsmasq.d/domains.lst --test 2>&1 | grep -q "syntax check OK"; then
        /etc/init.d/dnsmasq restart
    fi
}
