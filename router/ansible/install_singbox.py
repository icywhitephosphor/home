#!/usr/bin/env python3
import os
import sys
import json
import shutil
import re
import subprocess
import urllib.request
from pathlib import Path

# ============================================================================
# Configuration
# ============================================================================

# Default enabled domain lists (matching the Ansible role)
ENABLED_LISTS = [
    'openai', 'google', 'claude', 'copilot', 
    'datadog', 'instagram', 'netflix', 
    'x', 'linkedin', 'windsurf'
]

# External PAC sources
PAC_EXTRA_SOURCES = [
    "https://raw.githubusercontent.com/itdoginfo/allow-domains/main/Russia/inside-dnsmasq-ipset.lst"
]

# Paths
BASE_DIR = Path(__file__).resolve().parent
ROUTER_FILES_DIR = BASE_DIR / "roles/router/files"
CONFIG_DIR = Path.home() / ".config/sing-box"
CONFIG_FILE = CONFIG_DIR / "config.json"
PAC_FILE = CONFIG_DIR / "proxy.pac"
RUN_SCRIPT = CONFIG_DIR / "run-sing-box.sh"

# Colors for output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def log(msg, type="info"):
    if type == "info":
        print(f"{Colors.OKBLUE}[INFO]{Colors.ENDC} {msg}")
    elif type == "success":
        print(f"{Colors.OKGREEN}[OK]{Colors.ENDC} {msg}")
    elif type == "warning":
        print(f"{Colors.WARNING}[WARN]{Colors.ENDC} {msg}")
    elif type == "error":
        print(f"{Colors.FAIL}[ERROR]{Colors.ENDC} {msg}")

# ============================================================================
# Helpers
# ============================================================================

def run_command(cmd, check=True):
    try:
        subprocess.run(cmd, shell=True, check=check, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except subprocess.CalledProcessError:
        return False

def check_brew():
    if not run_command("command -v brew"):
        log("Homebrew not found! Please install it first.", "error")
        sys.exit(1)

def install_singbox():
    log("Checking sing-box installation...")
    if run_command("brew list sing-box", check=False):
        log("sing-box is already installed.", "success")
    else:
        log("Installing sing-box via Homebrew...")
        if run_command("brew install sing-box"):
            log("sing-box installed successfully.", "success")
        else:
            log("Failed to install sing-box", "error")
            sys.exit(1)

def parse_domains():
    domains = set()
    
    # 1. Parse local .lst files
    log(f"Parsing local domain lists: {', '.join(ENABLED_LISTS)}")
    for name in ENABLED_LISTS:
        file_path = ROUTER_FILES_DIR / f"{name}.lst"
        if not file_path.exists():
            log(f"File not found: {file_path}", "warning")
            continue
        
        content = file_path.read_text(encoding='utf-8')
        # Regex to match: ipset=/domain.com/
        matches = re.findall(r'(?:ipset|nftset)=/\.?([^/]+)/', content)
        domains.update(matches)
        
    # 2. Fetch external sources
    log("Fetching external domain sources...")
    for url in PAC_EXTRA_SOURCES:
        try:
            with urllib.request.urlopen(url) as response:
                content = response.read().decode('utf-8')
                matches = re.findall(r'(?:ipset|nftset)=/\.?([^/]+)/', content)
                domains.update(matches)
                log(f"Fetched {len(matches)} domains from {url}")
        except Exception as e:
            log(f"Failed to fetch {url}: {e}", "warning")

    sorted_domains = sorted(list(domains))
    log(f"Total unique domains: {len(sorted_domains)}", "success")
    return sorted_domains

def get_user_input(prompt, default=None):
    if default:
        user_input = input(f"{Colors.BOLD}{prompt} [{default}]: {Colors.ENDC}")
        return user_input.strip() or default
    else:
        while True:
            user_input = input(f"{Colors.BOLD}{prompt}: {Colors.ENDC}")
            if user_input.strip():
                return user_input.strip()

# ============================================================================
# Templates
# ============================================================================

def generate_files(domains, vpn_config):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    
    # 1. Generate config.json
    config_template = {
        "log": {
            "level": "info",
            "output": str(Path.home() / "Library/Logs/sing-box.log"),
            "timestamp": True
        },
        "dns": {
            "servers": [
                {"tag": "bootstrap", "type": "udp", "server": "8.8.8.8"},
                {"tag": "google-doh", "type": "https", "server": "dns.google", "server_port": 443, "domain_resolver": "bootstrap"},
                {"tag": "cloudflare-doh", "type": "https", "server": "cloudflare-dns.com", "server_port": 443, "domain_resolver": "bootstrap"}
            ],
            "rules": [
                {"domain_suffix": domains, "server": "google-doh"}
            ],
            "final": "cloudflare-doh"
        },
        "inbounds": [
            {
                "type": "mixed",
                "tag": "mixed-in",
                "listen": "127.0.0.1",
                "listen_port": 2080,
                "sniff": True,
                "sniff_override_destination": True
            }
        ],
        "outbounds": [
            {
                "tag": "vpn-out",
                "type": "vless",
                "server": vpn_config['server'],
                "server_port": int(vpn_config['port']),
                "uuid": vpn_config['uuid'],
                "flow": "xtls-rprx-vision",
                "tls": {
                    "enabled": True,
                    "insecure": False,
                    "server_name": vpn_config['sni'],
                    "utls": {"enabled": True, "fingerprint": "random"},
                    "reality": {
                        "enabled": True,
                        "public_key": vpn_config['public_key'],
                        "short_id": vpn_config['short_id']
                    }
                }
            },
            {"tag": "direct", "type": "direct"}
        ],
        "route": {
            "rules": [
                {"protocol": "dns", "action": "hijack-dns"},
                {"domain_suffix": domains, "outbound": "vpn-out"},
                {"ip_is_private": True, "outbound": "direct"}
            ],
            "final": "direct",
            "auto_detect_interface": True
        }
    }
    
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config_template, f, indent=2)
    log(f"Generated config: {CONFIG_FILE}", "success")

    # 2. Generate PAC file
    pac_content = f"""function FindProxyForURL(url, host) {{
    // Localhost and private IPs direct
    if (isPlainHostName(host) ||
        shExpMatch(host, "localhost") ||
        shExpMatch(host, "127.0.0.*") ||
        shExpMatch(host, "192.168.*") ||
        shExpMatch(host, "10.*") ||
        shExpMatch(host, "172.16.*") ||
        shExpMatch(host, "*.local")) {{
        return "DIRECT";
    }}

    var vpnDomains = {json.dumps(domains)};

    for (var i = 0; i < vpnDomains.length; i++) {{
        if (dnsDomainIs(host, vpnDomains[i]) ||
            dnsDomainIs(host, "." + vpnDomains[i]) ||
            host === vpnDomains[i]) {{
            return "PROXY 127.0.0.1:2080";
        }}
    }}

    return "DIRECT";
}}
"""
    PAC_FILE.write_text(pac_content)
    log(f"Generated PAC: {PAC_FILE}", "success")

    # 3. Generate Run Script
    script_content = f"""#!/bin/bash
exec /opt/homebrew/bin/sing-box run -c "{CONFIG_FILE}"
"""
    RUN_SCRIPT.write_text(script_content)
    RUN_SCRIPT.chmod(0o755)
    log(f"Generated run script: {RUN_SCRIPT}", "success")

# ============================================================================
# Main
# ============================================================================

def main():
    print(f"{Colors.HEADER}=== Sing-box Local Setup (No-Ansible) ==={Colors.ENDC}")
    
    check_brew()
    install_singbox()
    
    print(f"\n{Colors.BOLD}VPN Configuration Required:{Colors.ENDC}")
    vpn_config = {
        'server': get_user_input("VPN Server IP"),
        'port': get_user_input("VPN Server Port", "443"),
        'uuid': get_user_input("VLESS UUID"),
        'sni': get_user_input("TLS SNI (Server Name)"),
        'public_key': get_user_input("Reality Public Key"),
        'short_id': get_user_input("Reality Short ID", "")
    }
    
    domains = parse_domains()
    generate_files(domains, vpn_config)
    
    print(f"\n{Colors.HEADER}=== Setup Complete! ==={Colors.ENDC}")
    print(f"1. Start sing-box:  {Colors.BOLD}{RUN_SCRIPT}{Colors.ENDC}")
    print(f"2. PAC File URL:    {Colors.BOLD}file://{PAC_FILE}{Colors.ENDC}")
    print(f"3. Proxy Address:   {Colors.BOLD}127.0.0.1:2080{Colors.ENDC}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nSetup cancelled.")
        sys.exit(0)
