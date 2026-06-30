#!/usr/bin/env python3

import subprocess
import re

# Processes that are essential macOS system components — never suggest killing these
SYSTEM_PROCESSES = {
    'windowserver', 'kernel_task', 'launchd', 'loginwindow', 'windowmanager',
    'sysmond', 'logd', 'powerd', 'bluetoothd', 'locationd', 'cfprefsd',
    'runningboardd', 'launchservicesd', 'corespotlightd', 'spotlightknowled',
    'applecentaurialp', 'cursoruiviewserv', 'com.apple.appkit',
    'corebrightnessd', 'distnoted', 'notifyd', 'configd', 'diskarbitrationd',
    'opendirectoryd', 'trustd', 'securityd', 'syspolicyd', 'mdworker',
    'mds', 'mds_stores', 'hidd', 'sharingd', 'usbd', 'kernelmanagerd',
    'perfpowerservices', 'perfpowerserviced', 'thermalmonitord',
    'mediaanalysisd', 'photolibraryd', 'cloudd', 'bird', 'nsurlsessiond',
    # Transient sampling tools — they exit on their own
    'top',
}

def get_battery_info():
    """
    Executes a shell command to get battery information and parses the output.
    
    Returns a dictionary with all raw and parsed battery data.
    """
    try:
        command = "ioreg -l -w0"
        output = subprocess.check_output(command, shell=True, text=True)

        # Updated regex to capture multiple statistics.
        pattern = re.compile(r'"(AppleRawMaxCapacity|DesignCapacity|AppleRawCurrentCapacity|NominalChargeCapacity|CurrentCapacity|MaxCapacity|CycleCount|TotalCycleCount|TimeRemaining|AvgTimeToEmpty|AvgTimeToFull|IsCharging|ExternalConnected)"\s*=\s*(\w+)')
        
        matches = dict(pattern.findall(output))
        
        battery_data = {
            'AppleRawMaxCapacity': int(matches.get('AppleRawMaxCapacity', 0)),
            'AppleRawCurrentCapacity': int(matches.get('AppleRawCurrentCapacity', 0)),
            'NominalChargeCapacity': int(matches.get('NominalChargeCapacity', 0)),
            'CurrentCapacity': int(matches.get('CurrentCapacity', 0)),
            'MaxCapacity': int(matches.get('MaxCapacity', 100)),
            'DesignCapacity': int(matches.get('DesignCapacity', 0)),
            'CycleCount': int(matches.get('CycleCount', 0)),
            'TotalCycleCount': int(matches.get('TotalCycleCount', 0)),
            'IsCharging': matches.get('IsCharging', 'No') == 'Yes',
            'ExternalConnected': matches.get('ExternalConnected', 'No') == 'Yes',
            'TimeRemaining': int(matches.get('TimeRemaining', 0)),
            'AvgTimeToFull': int(matches.get('AvgTimeToFull', 65535)),
        }
        
        # Add additional calculated values
        if battery_data['DesignCapacity'] > 0 and battery_data['NominalChargeCapacity'] > 0:
            # Battery health: NominalChargeCapacity is what macOS treats as full charge
            battery_data['BatteryHealthPercent'] = (battery_data['NominalChargeCapacity'] / battery_data['DesignCapacity']) * 100
            # Battery life: CurrentCapacity/MaxCapacity matches what macOS shows in the menu bar
            battery_data['BatteryLifePercent'] = (battery_data['CurrentCapacity'] / battery_data['MaxCapacity']) * 100
        
        return battery_data
    except (subprocess.CalledProcessError, FileNotFoundError, ValueError) as e:
        print(f"Error executing command or parsing output: {e}")
        return None


def parse_mem(mem_str):
    """Convert top memory string like '249M+', '1280M+', '6528K' to MB float."""
    mem_str = mem_str.rstrip('+-')
    if mem_str.endswith('G'):
        return float(mem_str[:-1]) * 1024
    elif mem_str.endswith('M'):
        return float(mem_str[:-1])
    elif mem_str.endswith('K'):
        return float(mem_str[:-1]) / 1024
    try:
        return float(mem_str) / (1024 * 1024)
    except ValueError:
        return 0.0


def get_top_processes(n=15):
    """
    Samples top twice (so first idle sample is discarded) and returns the
    top n processes sorted by energy impact (POWER column).
    """
    try:
        # -l 2: two samples; we use the second for accurate CPU/power readings
        # -o power: sort by energy impact
        # -stats: only the columns we need
        output = subprocess.check_output(
            ['top', '-l', '2', '-o', 'power', '-n', str(n), '-stats', 'pid,command,cpu,mem,power'],
            text=True, stderr=subprocess.DEVNULL
        )
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"Error running top: {e}")
        return []

    # top -l 2 prints two full blocks; grab lines after the second "PID" header
    blocks = re.split(r'(?m)^PID\s+COMMAND', output)
    if len(blocks) < 3:
        # Fall back to whatever we got
        data_block = blocks[-1]
    else:
        data_block = blocks[-1]

    processes = []
    for line in data_block.strip().splitlines():
        parts = line.split()
        if len(parts) < 5:
            continue
        pid, command, cpu_str, mem_str, power_str = parts[0], parts[1], parts[2], parts[3], parts[4]
        try:
            processes.append({
                'pid': int(pid),
                'command': command,
                'cpu': float(cpu_str),
                'mem_mb': parse_mem(mem_str),
                'power': float(power_str),
            })
        except ValueError:
            continue

    processes.sort(key=lambda p: p['power'], reverse=True)
    return processes[:n]


def is_system_process(name):
    return name.lower() in SYSTEM_PROCESSES


def print_process_recommendations(processes):
    print("\n--- Top Energy Consumers ⚡ ---")
    print(f"{'PID':<8} {'Command':<24} {'CPU%':>6} {'Mem(MB)':>9} {'Power':>7}")
    print("-" * 58)

    killable = []
    for p in processes:
        flag = "  [system]" if is_system_process(p['command']) else ""
        print(f"{p['pid']:<8} {p['command']:<24} {p['cpu']:>5.1f}% {p['mem_mb']:>8.0f}M {p['power']:>6.1f}{flag}")
        if not is_system_process(p['command']) and p['power'] >= 1.0:
            killable.append(p)

    if not killable:
        print("\nNo obvious energy-hungry user processes found.")
        return

    print("\n--- Recommendations 💡 ---")

    # Group browser helpers
    browser_helpers = [p for p in killable if any(
        b in p['command'].lower() for b in ['brave', 'chrome', 'firefox', 'safari', 'webkit']
    )]
    other = [p for p in killable if p not in browser_helpers]

    if browser_helpers:
        total_browser_power = sum(p['power'] for p in browser_helpers)
        total_browser_mem = sum(p['mem_mb'] for p in browser_helpers)
        pids = ', '.join(str(p['pid']) for p in browser_helpers)
        print(f"\n🌐 Browser helper processes ({len(browser_helpers)} workers, "
              f"~{total_browser_power:.1f} power, ~{total_browser_mem:.0f}MB)")
        print(f"   PIDs: {pids}")
        print(f"   → Close unused tabs or quit the browser to reclaim energy and memory.")
        print(f"   → To kill all:  kill {pids}")

    for p in other:
        tip = ""
        cmd_lower = p['command'].lower()
        if 'whatsapp' in cmd_lower or 'telegram' in cmd_lower or 'signal' in cmd_lower:
            tip = "Messaging app running in background. Quit if not needed."
        elif 'vpn' in cmd_lower or 'expressvpn' in cmd_lower or 'nordvpn' in cmd_lower:
            tip = "VPN adds constant CPU overhead. Disconnect when not needed."
        elif 'iterm' in cmd_lower or 'terminal' in cmd_lower or 'alacritty' in cmd_lower:
            tip = "Terminal with active processes. Close idle sessions."
        elif 'activity monitor' in cmd_lower or 'activitymonitor' in cmd_lower:
            tip = "Activity Monitor itself consumes energy while open."
        elif 'vscodium' in cmd_lower or 'vscode' in cmd_lower or 'code' in cmd_lower or 'kilo' in cmd_lower:
            tip = "Editor/IDE helper process. Close unused projects or extensions."
        else:
            tip = "Consider quitting if not actively needed."

        print(f"\n🔴 {p['command']} (PID {p['pid']}, power {p['power']:.1f}, "
              f"CPU {p['cpu']:.1f}%, mem {p['mem_mb']:.0f}MB)")
        print(f"   → {tip}")
        print(f"   → To kill:  kill {p['pid']}")


def main():
    """
    Main function to get and display battery information.
    """
    print("Hello from macos-battery! 🔋")
    battery_info = get_battery_info()
    
    if not battery_info:
        print("Failed to retrieve battery information. 🔴")
        return

    # Check if necessary data is available before proceeding
    if battery_info['DesignCapacity'] > 0 and battery_info['NominalChargeCapacity'] > 0 and 'BatteryHealthPercent' in battery_info:
        
        print("\n--- Battery Statistics 🔌 ---")
        print(f"Original Design Capacity: {battery_info['DesignCapacity']} mAh")
        print(f"Current Max Capacity: {battery_info['NominalChargeCapacity']} mAh")
        print(f"Current Charge: {battery_info['AppleRawCurrentCapacity']} mAh ({battery_info['BatteryLifePercent']:.2f}%)")
        
        print("\n--- Usage Statistics 📊 ---")
        print(f"Current Cycle Count: {battery_info['CycleCount']}")
        
        print("\n🔋 Battery Health: {:.2f}%".format(battery_info['BatteryHealthPercent']))
        print(f"🔋 Battery Life: {battery_info['BatteryLifePercent']:.2f}%")

        if battery_info['IsCharging'] or battery_info['ExternalConnected']:
            time_to_full = battery_info['AvgTimeToFull']
            if time_to_full > 0 and time_to_full < 65535:
                hh, mm = divmod(time_to_full, 60)
                print(f"⚡ Charging — full in {hh}h {mm:02d}m")
            else:
                print("⚡ Charging")
        else:
            mins = battery_info['TimeRemaining']
            if mins > 0 and mins < 65535:
                hh, mm = divmod(mins, 60)
                print(f"⏱️  Time remaining: {hh}h {mm:02d}m")
        
        print("\n--- Interpretation 💡 ---")
        print("Battery Health indicates the long-term condition of your battery,")
        print("representing its maximum charge capacity relative to its original")
        print("design capacity. 🔬")
        print("A lower health percentage means your battery can't hold as much")
        print("charge as it could when it was new.")
        print("\nBattery Life indicates the current charge level of your battery.")
        print("It's the percentage you see in the menu bar and shows how much")
        print("power you have available right now. ⚡")
        print("Think of it like a fuel gauge.")
        
    else:
        print("Could not retrieve valid battery data. Make sure you are on a compatible system. ⚠️")

    print("\n⏳ Sampling processes (2s)...")
    processes = get_top_processes(n=20)
    if processes:
        print_process_recommendations(processes)

if __name__ == "__main__":
    main()
