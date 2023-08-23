from typing import Dict

import indigo

from comms import InverterClient, HomeManagerClientThread
from objects import *
from pymodbus.exceptions import ModbusException


class Plugin(indigo.PluginBase):

    inverters: Dict[int, InverterClient] = dict()
    """
    Stores all the Inverter objects used in the plugin.
    keys: device ids
    values: Client objects (see comms.py)
    """

    home_manager_thread: Optional[HomeManagerClientThread] = None
    """Represents a HomeManagerClientThread object used to communicate with an Home Manager unit.
    The first position holds the current device id.
    The second position holds the HomeManagerClientThread object."""

    logicalMeter: Optional[LogicalMeter] = None
    """Represents a LogicalMeter object.
    This object stores two important values:
        - The total energy being produced in all inverters (this is a simple sum of the values of all inverters)
        - The total power consumption of the system, which includes the energy produced by inverters and consumed by the system and the energy consumed from the grid.
    """

    state_update_time: int = 10
    """Represents the time interval in seconds between each state update."""

    def __init__(self, pluginId: str, pluginDisplayName: str, pluginVersion: str, pluginPrefs: dict):
        super().__init__(pluginId, pluginDisplayName, pluginVersion, pluginPrefs)
        self.state_update_time = self._validate_state_update_time(pluginPrefs)

    def startup(self):
        pass

    def shutdown(self):
        # Close connection to all inverters
        for client in self.inverters.values():
            client.close()

    def closedPrefsConfigUi(self, valuesDict: dict, userCancelled: bool) -> None:
        if not userCancelled:

            self.state_update_time = self._validate_state_update_time(valuesDict)

    def _validate_state_update_time(self, valuesDict: dict) -> int:
        try:
            state_update_time = int(valuesDict.get('stateUpdateTime', 'invalid value'))
        except ValueError:
            self.logger.error(f"Invalid value for state update time: {valuesDict.get('stateUpdateTime', None)}. Using default value of 10 seconds.")
            state_update_time = 10
        return state_update_time

    def runConcurrentThread(self):
        try:
            while True:
                self.fetch_inverters_data()
                self.fetch_home_manager_data()
                self.update_logic_meter()
                self.sleep(self.state_update_time)

        except self.StopThread:
            self.shutdown()

    def deviceStartComm(self, dev: indigo.Device) -> None:
        properties = dev.pluginProps

        if dev.deviceTypeId == 'smaIndigoInverter':
            client = InverterClient(properties['inverterAddress'], int(properties['inverterPort']))

            if not client.connect():
                self.logger.error(f"Failed to establish communication to inverter: {dev.name}")
                return

            self.inverters[dev.id] = client

        elif dev.deviceTypeId == 'smaIndigoHomeManager':
            if self.home_manager_thread:
                self.logger.error(f"Home Manager already exists. Only one Home Manager is allowed for now. Device '{dev.name}' will be ignored.")
                return

            self.home_manager_thread = HomeManagerClientThread(dev.id)
            self.home_manager_thread.start()

            # Wait 5 seconds for the thread to get the Home Manager object
            self.home_manager_thread.home_manager_present_event.wait(5)

            home_manager = self.home_manager_thread.get_home_manager()

            if home_manager is None:
                self.logger.error(f"Failed to establish communication to Home Manager: {dev.name}")
                self.home_manager_thread.stop()
                self.home_manager_thread.join()
                return

        elif dev.deviceTypeId == 'smaIndigoLogicalMeter':
            if self.logicalMeter:
                self.logger.error(f"Logical Meter already exists. Only on Logical Meter is allowed for now. Device '{dev.name}' will be ignored.")
                return

            if not self.home_manager_thread:
                self.logger.warning(f"Logical Meter requires a Home Manager to account for the total consumed power. This state will not be updated unless a Home Manager is configured.")

            self.logicalMeter = LogicalMeter(
                device_id=dev.id,
                totalProduction=0,
                totalConsumption=0,
                solarConsumption=0,
                solarConsumptionPercentage=0
            )

        else:
            self.logger.warning(f"Unknown device type id: {dev.deviceTypeId}")
            return

        self.logger.info(f'Successfully started device {dev.name}.')

    def deviceStopComm(self, dev: indigo.Device) -> None:
        if dev.deviceTypeId == "smaIndigoInverter" and dev.id in self.inverters.keys():
            client = self.inverters.get(dev.id)
            client.close()
            del self.inverters[dev.id]

        elif dev.deviceTypeId == "smaIndigoHomeManager" and self.home_manager_thread.device_id == dev.id:
            self.home_manager_thread.stop()
            self.home_manager_thread.join()
            self.home_manager_thread = None

        elif dev.deviceTypeId == "smaIndigoLogicalMeter" and self.logicalMeter.device_id == dev.id:
            self.logicalMeter = None

        else:
            self.logger.warning(f"Unknown device type id: {dev.deviceTypeId}")
            return

        self.logger.info(f'Successfully stopped device {dev.name}.')

    ###########################

    def fetch_inverters_data(self):
        """Fetches the data from all registered inverters and updates the states in indigo.
        Will attempt to reconnect the inverter if a ConnectionError is found"""
        for device_id, client in self.inverters.items():
            try:
                inverter = client.get_inverter_data()
                indigo.devices[device_id].updateStatesOnServer([
                    {'key': 'serialNumber', 'value': inverter.serialNumber, 'uiValue': inverter.serialNumber},
                    {'key': 'acPower', 'value': inverter.acPower, 'uiValue': f'{inverter.acPower} W'},
                    {'key': 'acCurrent', 'value': inverter.acCurrent, 'uiValue': f'{inverter.acCurrent} A'},
                    {'key': 'acVoltage', 'value': inverter.acVoltage, 'uiValue': f'{inverter.acVoltage} V'},
                    {'key': 'gridFreq', 'value': inverter.gridFreq, 'uiValue': f'{inverter.gridFreq} Hz'},
                    {'key': 'deviceTemperature', 'value': inverter.deviceTemperature, 'uiValue': f'{inverter.deviceTemperature} \u00b0C'},
                    {'key': 'totalOperationTime', 'value': inverter.totalOperationTime, 'uiValue': f'{inverter.totalOperationTime} s'},
                    {'key': 'feedInTime', 'value': inverter.feedInTime, 'uiValue': f'{inverter.feedInTime} s'},
                    {'key': 'dailyYield', 'value': inverter.dailyYield, 'uiValue': f'{inverter.dailyYield} Wh'},
                    {'key': 'totalYield', 'value': inverter.totalYield, 'uiValue': f'{inverter.totalYield} Wh'},
                ])

            except ModbusException:
                self.logger.error(f"Lost connection to inverter: {device_id}. Reconnecting...")
                client.reconnect()

            except AttributeError as e:
                self.logger.error(f"Lost connection to inverter: {device_id}. Reconnecting...")
                client.reconnect()

    def fetch_home_manager_data(self):
        if not self.home_manager_thread:
            return

        home_manager = self.home_manager_thread.get_home_manager()

        if home_manager is None:
            self.logger.error(f"Lost connection to Home Manager. Reconnecting...")

            self._restart_home_manager_client_thread()

            return

        indigo.devices[self.home_manager_thread.device_id].updateStatesOnServer([
            {'key': 'totalPowerFromGrid', 'value': home_manager.totalPowerFromGrid, 'uiValue': f'{home_manager.totalPowerFromGrid} W'},
            {'key': 'totalPowerToGrid', 'value': home_manager.totalPowerToGrid, 'uiValue': f'{home_manager.totalPowerToGrid} W'},
            {'key': 'phase1PowerFromGrid', 'value': home_manager.phase1PowerFromGrid, 'uiValue': f'{home_manager.phase1PowerFromGrid} W'},
            {'key': 'phase1PowerToGrid', 'value': home_manager.phase1PowerToGrid, 'uiValue': f'{home_manager.phase1PowerToGrid} W'},
            {'key': 'phase2PowerFromGrid', 'value': home_manager.phase2PowerFromGrid, 'uiValue': f'{home_manager.phase2PowerFromGrid} W'},
            {'key': 'phase2PowerToGrid', 'value': home_manager.phase2PowerToGrid, 'uiValue': f'{home_manager.phase2PowerToGrid} W'},
            {'key': 'phase3PowerFromGrid', 'value': home_manager.phase3PowerFromGrid, 'uiValue': f'{home_manager.phase3PowerFromGrid} W'},
            {'key': 'phase3PowerToGrid', 'value': home_manager.phase3PowerToGrid, 'uiValue': f'{home_manager.phase3PowerToGrid} W'},
        ])

    def update_logic_meter(self):
        if self.logicalMeter is None:
            return

        total_production = sum([indigo.devices[device_id].states['acPower'] for device_id in self.inverters.keys()])
        total_consumption = 0  # Only calculated if a Home Manager is configured
        solar_consumption = 0  # Only calculated if a Home Manager is configured
        solar_consumption_percentage = 0  # Only calculated if a Home Manager is configured

        if self.home_manager_thread:
            power_from_grid = indigo.devices[self.home_manager_thread.device_id].states['totalPowerFromGrid']
            power_to_grid = indigo.devices[self.home_manager_thread.device_id].states['totalPowerToGrid']

            total_consumption = total_production + power_from_grid - power_to_grid

            solar_consumption = total_production - power_to_grid
            if total_production == 0:
                solar_consumption_percentage = 0
            else:
                solar_consumption_percentage = solar_consumption / total_production * 100

        self.logicalMeter.totalProduction = total_production
        self.logicalMeter.totalConsumption = total_consumption
        self.logicalMeter.solarConsumption = solar_consumption
        self.logicalMeter.solarConsumptionPercentage = solar_consumption_percentage

        indigo.devices[self.logicalMeter.device_id].updateStatesOnServer([
            {'key': 'totalProduction', 'value': self.logicalMeter.totalProduction, 'uiValue': f'{self.logicalMeter.totalProduction} W'},
            {'key': 'totalConsumption', 'value': self.logicalMeter.totalConsumption, 'uiValue': f'{self.logicalMeter.totalConsumption} W'},
            {'key': 'solarConsumption', 'value': self.logicalMeter.solarConsumption, 'uiValue': f'{self.logicalMeter.solarConsumption} W'},
            {'key': 'solarConsumptionPercentage', 'value': self.logicalMeter.solarConsumptionPercentage, 'uiValue': f'{self.logicalMeter.solarConsumptionPercentage} %'},
        ])

    def reconnect_all(self):
        """Reconnects all devices registered in the system"""
        self.logger.info(f'Reconnecting inverters... {len(self.inverters)} devices')
        for device_id, client in self.inverters.items():
            dev = indigo.devices[device_id]
            if client.reconnect():
                self.logger.info(f'    - {dev.name} --- OK')
            else:
                self.logger.error(f'    - {dev.name} --- FAILED')

        if self.home_manager_thread:
            self.logger.info(f'Reconnecting Home Manager')
            dev = indigo.devices[self.home_manager_thread.device_id]
            if self._restart_home_manager_client_thread():
                self.logger.info(f'    - {dev.name} --- OK')
            else:
                self.logger.error(f'    - {dev.name} --- FAILED')

    def reconnect_device(self, valuesDict, typeId):
        """Reconnects a specific device"""
        device = indigo.devices[int(valuesDict['targetDevice'])]

        if device.deviceTypeId == 'smaIndigoInverter':
            client = self.inverters.get(device.id)
            if client.reconnect():
                self.logger.info(f'Successfully reconnected device {device.name}.')
            else:
                self.logger.error(f'Failed to reconnect device {device.name}.')

        elif device.deviceTypeId == 'smaIndigoHomeManager':
            if self._restart_home_manager_client_thread():
                self.logger.info(f'Successfully reconnected device {device.name}.')
            else:
                self.logger.error(f'Failed to reconnect device {device.name}.')

        else:
            self.logger.warning(f'Device reconnection not supported for that device.')
            errorsDict = indigo.Dict()
            errorsDict['targetDevice'] = "Device reconnection not supported for this device."
            errorsDict['showAlertText'] = "Device reconnection not supported for that device."
            return False, valuesDict, errorsDict

        return True, valuesDict, indigo.Dict()

    def _restart_home_manager_client_thread(self):
        if not self.home_manager_thread:
            return False

        self.home_manager_thread.stop()
        self.home_manager_thread.join()

        self.home_manager_thread = HomeManagerClientThread(self.home_manager_thread.device_id)
        self.home_manager_thread.start()
        self.home_manager_thread.home_manager_present_event.wait(5)

        return self.home_manager_thread.get_home_manager() is not None
