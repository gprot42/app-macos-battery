#!/usr/bin/env python3
import objc
from Foundation import NSBundle
IOKit = NSBundle.bundleWithIdentifier_('com.apple.framework.IOKit')
functions = [
    ("IOServiceGetMatchingService", b"II@"),
    ("IOServiceMatching", b"@*"),
    ("IORegistryEntryCreateCFProperties", b"IIo^@@I"),
    ("IOPSCopyPowerSourcesByType", b"@I"),
    ("IOPSCopyPowerSourcesInfo", b"@"),
]
objc.loadBundleFunctions(IOKit, globals(), functions)
# Matches information pulled by: pmset -g rawbatt
def raw_battery_dict():
    # The fix is on this line: "AppleSmartBattery" -> b"AppleSmartBattery"
    battery = IOServiceGetMatchingService(0, IOServiceMatching(b"AppleSmartBattery"))
    if battery != 0:
        # We have a battery
        err, props = IORegistryEntryCreateCFProperties(battery, None, None, 0)
        return props
    return None
# Matches information pulled by: pmset -g batt
def adjusted_battery_dict():
    try:
        # IOPSCopyPowerSourcesByType(0) returns internal batteries
        battery = list(IOPSCopyPowerSourcesByType(0))[0]
    except IndexError:
        return None
    return battery
def raw_battery_percent():
    d = raw_battery_dict()
    if d:
        curc = d['CurrentCapacity']
        maxc = d['MaxCapacity']
        perc = 100.0 * curc / maxc
        return perc
    return None
def adjusted_battery_percent():
    d = adjusted_battery_dict()
    if d:
        return d["Current Capacity"]
    return None
def battery_health():
    d = raw_battery_dict()
    if d:
        design_capacity = d.get('DesignCapacity', 0)
        max_capacity = d.get('AppleRawMaxCapacity', 0)  # Alternatively, use d['BatteryData']['FccComp1']
        if design_capacity > 0:
            health = (max_capacity / design_capacity) * 100
            return health
    return None
if __name__ == "__main__":
    print("Battery Statistics using IOKit via pyObjC on macOS")
    raw_dict = raw_battery_dict()
    if raw_dict:
        print("\nRaw Battery Details (from AppleSmartBattery):")
        for key, value in raw_dict.items():
            print(f"{key}: {value}")
    else:
        print("\nNo raw battery information available.")
    adjusted_dict = adjusted_battery_dict()
    if adjusted_dict:
        print("\nAdjusted Battery Details (from Power Sources):")
        for key, value in adjusted_dict.items():
            print(f"{key}: {value}")
    else:
        print("\nNo adjusted battery information available.")
    raw_perc = raw_battery_percent()
    if raw_perc is not None:
        print(f"\nRaw Battery Percentage: {raw_perc:.2f}%")
    else:
        print("\nNo raw battery percentage available.")
    adj_perc = adjusted_battery_percent()
    if adj_perc is not None:
        print(f"Adjusted Battery Percentage: {adj_perc}%")
    else:
        print("No adjusted battery percentage available.")
    health = battery_health()
    if health is not None:
        print(f"\nBattery Health: {health:.1f}% (based on {raw_dict['AppleRawMaxCapacity']} mAh / {raw_dict['DesignCapacity']} mAh)")
        print(f"Cycle Count: {raw_dict['CycleCount']} out of {raw_dict['DesignCycleCount9C']}")
        if health < 80:
            print("\nWarning: Battery health is below 80%. If you're experiencing reduced runtime, visit an Apple Store for diagnostics. They may replace it under warranty if under 1000 cycles and below 80% capacity.")
        print("\nTips to prolong battery life:")
        print("- Enable Optimized Battery Charging in System Settings > Battery.")
        print("- Avoid extreme temperatures (below 0°C or above 35°C).")
        print("- Try to keep the charge level between 20% and 80% when possible.")
        print("\nFor more details, check System Information > Power in macOS, or use third-party tools like coconutBattery for a GUI view.")
    else:
        print("\nNo battery health information available.")
