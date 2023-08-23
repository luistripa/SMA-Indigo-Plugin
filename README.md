# SMA Energy Plugin

A plugin that integrates SMA Solar Inverters and Home Managers with the Indigo Domotics system.

## Notice

This project has no affiliation whatsoever with SMA Solar Technology AG.
It is a third-party plugin that uses the SMA Modbus protocol to communicate with the inverters.

**This plugin is still vastly untested. Use at your own risk.**

The current version has been developed for the latest indigo version. It is not guarantee to work on previous ones, even
though it should work with any indigo version that supports Python 3.

Inverters **must have** Modbus enabled for the plugin to be able to communicate with them.

**Tested hardware**: Sunny Boy 1.5 and 2.5 and Sunny Home Manager 2.0

## How to install
- Download the SMA.indigoPlugin file
- Double-click on the file to install it on your system OR move it to the plugins folder and enable the plugin through
the Indigo Server UI

## Device types
- **Inverter**: A normal solar inverter. This is what you need when configuring a new inverter.
- **Home Manager**: Connects to a Sunny Home Manager device and retrieves data from it. **Note**: Only one device is supported at the moment.
- **Logical Meter**: A device that aggregates data from the other devices to provide important values that can be used in Indigo's logic. Important information in the sections below.

## Device Creation/Configuration
If you are interested on how to create a new device or
configure a new one, you're in the right section!

### Inverter Device
- Head to the devices section
- Create a new device
- Select *SMA Energy* from the Type dropdown
- Select *Inverter* from the Model dropdown
- Fill in the inverter network address and port (default port 502)
- Click *Save*
- Name your device and insert optional notes
- Close the *Create New Device* menu
- If no errors appear in the log, the device is now created and fully functioning


## Creation of Home Manager and Logical Meter Devices

These devices don't require any configuration whatsoever, just create them normally and they will start working right away.

**Each one of these device types may only have 1 device configured at the same time**

## Important note on Logical Meters

Some states belonging to the logical meter device **may remain with a zero value and never change**. This is because some
of the states are calculated using the Home Manager states. If the Home Manager is not configured, these states will
remain with a zero value until a Home Manager device is successfully configured.

**These states are not designed to work without a Home Manager device:**
- `Total Consumption`
- `Solar Consumption`
- `Solar Consumption Percentage`

The only available state being `Total Production`.

## Device States

### Inverter

- `Serial Number`
- `AC Power` (W)
- `AC Current` (A)
- `AC Voltage` (V)
- `Grid Frequency` (Hz)
- `Device Internal Temperature` (°C)
- `Operation Time` (s)
- `Daily Yield` (Wh)
- `Total Yield` (Wh)

### Home Manager

- `Total Power From Grid` (sum of all phases)
- `Total Power To Grid` (sum of all phases)
- `Phase 1 Power From Grid`
- `Phase 1 Power To Grid`
- `Phase 2 Power From Grid`
- `Phase 2 Power To Grid`
- `Phase 3 Power From Grid`
- `Phase 3 Power To Grid`

**All units are in Watts**

### Logical Meter

- `Total Production` (how much all the inverters are producing)
- `Total Consumption` (`totalProduction + powerFromGrid - powerToGrid`)
- `Solar Consumption` (how much of the total consumption is being produced by the inverters)
- `Solar Consumption Percentage` (`solarConsumption / totalConsumption * 100`)

**All units are in Watts**
