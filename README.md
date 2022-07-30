# SMA Energy Plugin

A plugin for integration with indigo domotics to get
information directly from SMA Solar inverters.

**This is a beta version!**
It may or may not work on your system

**The current version has been tested on Indigo 7+**

**This plugin was tested with Sunny Boy 1.5 and 2.5**

**Inverters need to have Modbus enabled**

## How to install
- Download the SMA.indigoPlugin file
- Double-click on the file to install it on your system OR move it to the plugins folder
- You may need to reboot your system

## Device types
- **Inverter**: A normal solar inverter. This is what you need when configuring a new inverter.
- **Aggregation**: Used to aggregate values from two or more inverters or other aggregations

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


## Aggregation Device

An Aggregation is a device type that allows you to aggregate values in many ways.
They may be used, for example, to sum all the power outputs from all inverters to get a total power
output value.
Aggregations support aggregating a list of inverters using a single state, a list of other aggregations by their values
or by applying a simple mathematical operation to two inverters' states or two aggregations' values.

- List of inverters (`sum` and `average` only)
- List of aggregations (`sum` and `average` only)
- Two inverters (`sum`, `subtraction`, `division`, `multiplication`, `average`, `min` and `max` supported)
- Two aggregations (`sum`, `subtraction`, `division`, `multiplication`, `average`, `min` and `max` supported)


### To reconfigure a device
- Head to the devices section and select the 
  device you wish to reconfigure
- Click *Edit Device Settings...*
- Reconfigure the device and click *Save*


