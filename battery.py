#!/usr/bin/env python3

import subprocess
import re

def get_battery_info():
    """
    Executes a shell command to get battery information and parses the output.
    
    Returns a dictionary with all raw and parsed battery data.
    """
    try:
        command = "ioreg -l -w0"
        output = subprocess.check_output(command, shell=True, text=True)

        # Updated regex to capture multiple statistics.
        pattern = re.compile(r'"(AppleRawMaxCapacity|DesignCapacity|AppleRawCurrentCapacity|CycleCount|TotalCycleCount)"\s*=\s*(\d+)')
        
        matches = dict(pattern.findall(output))
        
        battery_data = {
            'AppleRawMaxCapacity': int(matches.get('AppleRawMaxCapacity', 0)),
            'AppleRawCurrentCapacity': int(matches.get('AppleRawCurrentCapacity', 0)),
            'DesignCapacity': int(matches.get('DesignCapacity', 0)),
            'CycleCount': int(matches.get('CycleCount', 0)),
            'TotalCycleCount': int(matches.get('TotalCycleCount', 0)),
        }
        
        # Add additional calculated values
        if battery_data['DesignCapacity'] > 0 and battery_data['AppleRawMaxCapacity'] > 0:
            battery_data['BatteryHealthPercent'] = (battery_data['AppleRawMaxCapacity'] / battery_data['DesignCapacity']) * 100
            battery_data['BatteryLifePercent'] = (battery_data['AppleRawCurrentCapacity'] / battery_data['AppleRawMaxCapacity']) * 100
        
        return battery_data
    except (subprocess.CalledProcessError, FileNotFoundError, ValueError) as e:
        print(f"Error executing command or parsing output: {e}")
        return None

def main():
    """
    Main function to get and display battery information.
    """
    print("Hello from macos-battery! üîã")
    battery_info = get_battery_info()
    
    if not battery_info:
        print("Failed to retrieve battery information. üò¢")
        return

    # Check if necessary data is available before proceeding
    if battery_info['DesignCapacity'] > 0 and battery_info['AppleRawMaxCapacity'] > 0 and 'BatteryHealthPercent' in battery_info:
        
        print("\n--- Battery Statistics üìä ---")
        print(f"Original Design Capacity: {battery_info['DesignCapacity']} mAh")
        print(f"Current Max Capacity: {battery_info['AppleRawMaxCapacity']} mAh")
        print(f"Current Charge: {battery_info['AppleRawCurrentCapacity']} mAh ({battery_info['BatteryLifePercent']:.2f}%)")
        
        print("\n--- Usage Statistics üìà ---")
        print(f"Current Cycle Count: {battery_info['CycleCount']}")
        
        print("\nüîã Battery Health: {:.2f}%".format(battery_info['BatteryHealthPercent']))
        print(f"üîã Battery Life: {battery_info['BatteryLifePercent']:.2f}%")
        
        print("\n--- Interpretation üí° ---")
        print("Battery Health indicates the long-term condition of your battery, representing its maximum charge capacity relative to its original design capacity. üìâ")
        print("A lower health percentage means your battery can't hold as much charge as it could when it was new.")
        print("\nBattery Life indicates the current charge level of your battery. It's the percentage you see in the menu bar and shows how much power you have available right now. ‚õΩ")
        print("Think of it like a fuel gauge.")
        
    else:
        print("Could not retrieve valid battery data. Make sure you are on a compatible system. üòî")

if __name__ == "__main__":
    main()
