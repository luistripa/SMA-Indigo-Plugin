import indigo

from objects import *
from services import IndigoService
from pymodbus.exceptions import ModbusException

from comms import Client


DISPLAY_NAME = 'SMA Energy'


class Plugin(indigo.PluginBase):
    def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
        indigo.PluginBase.__init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs)

        """
        Stores all Inverter objects in the system.
        Key is device id
        Value is Client object
        """
        self.inverters = dict()

        """
        Stores all aggregations.
        Key is device id, Value is Aggregation Subclass object
        """
        self.aggregations = dict()

        """
        Defines dependencies between devices.
        Key is device id
        Value is device dependencies
        """
        self.dependencies = dict()

    def startup(self):
        pass

    def shutdown(self):
        # Close connection to all inverters
        for client in self.inverters.values():
            client.close()

    def runConcurrentThread(self):
        try:
            while True:
                self.update_inverters()
                self.update_aggregations()
                self.sleep(10)

        except self.StopThread:
            self.shutdown()

    def closedPrefsConfigUi(self, valuesDict, userCancelled):
        if not userCancelled:
            pass

    def deviceStartComm(self, device):
        properties = device.pluginProps

        if device.deviceTypeId == 'smaIndigoInverter':
            client = Client(properties['inverterAddress'], int(properties['inverterPort']))
            if client.connect():
                self.inverters[device.id] = client
                indigo.server.log('Started communication with inverter device: {}'.format(device.name),
                                  type=DISPLAY_NAME)
            else:
                indigo.server.log('Failed to establish connection to inverter: {}'.format(device.name),
                                  type=DISPLAY_NAME)

        elif device.deviceTypeId == "smaIndigoAggregation":
            aggregation_type = properties["aggregationType"]

            if aggregation_type == "inverterList":
                aggregation = InverterListAggregation(
                    device,
                    properties['inverterList'],
                    properties['inverterListState'],
                    properties['inverterListOperation']
                )
                self.aggregations[device.id] = aggregation
                self.add_dependencies(device.id, [])

            elif aggregation_type == "aggregationList":
                aggregation = AggregationListAggregation(
                    device,
                    properties['aggregationList'],
                    properties['aggregationListOperation']
                )
                self.aggregations[device.id] = aggregation

                self.add_dependencies(device.id, [int(d) for d in properties['aggregationList']])

            elif aggregation_type == "inverterToInverter":
                aggregation = InverterToInverterAggregation(
                    device,
                    int(properties['inverterToInverter_Inverter1']),
                    properties['inverterToInverter_Inverter1State'],
                    int(properties['inverterToInverter_Inverter2']),
                    properties['inverterToInverter_Inverter2State'],
                    properties['inverterToInverterOperation']
                )
                self.aggregations[device.id] = aggregation
                self.add_dependencies(device.id, [])

            elif aggregation_type == "aggregationToAggregation":
                aggregation = AggregationToAggregationAggregation(
                    device,
                    int(properties['aggregationToAggregation_Aggregation1']),
                    int(properties['aggregationToAggregation_Aggregation2']),
                    properties['aggregationToAggregationOperation']
                )
                self.aggregations[device.id] = aggregation
                self.add_dependencies(
                    device.id,
                    [
                        int(properties['aggregationToAggregation_Aggregation1']),
                        int(properties['aggregationToAggregation_Aggregation2'])
                    ]
                )

            elif aggregation_type == "aggregationToInverter":
                aggregation = AggregationToInverterAggregation(
                    device,
                    int(properties['aggregationToInverter_Aggregation']),
                    int(properties['aggregationToInverter_Inverter']),
                    properties['aggregationToInverter_InverterState'],
                    properties['aggregationToInverterOperation']
                )
                self.aggregations[device.id] = aggregation
                self.add_dependencies(device.id, [int(properties['aggregationToInverter_Aggregation'])])

            elif aggregation_type == "inverterToAggregation":
                aggregation = InverterToAggregationAggregation(
                    device,
                    int(properties['aggregationToInverter_Inverter']),
                    properties['aggregationToInverter_InverterState'],
                    int(properties['aggregationToInverter_Aggregation']),
                    properties['aggregationToInverterOperation']
                )
                self.aggregations[device.id] = aggregation
                self.add_dependencies(device.id, [int(properties['aggregationToInverter_Aggregation'])])

        else:
            indigo.server.log('Unknown device type id: {}'.format(device.deviceTypeId), type=DISPLAY_NAME)

    def deviceStopComm(self, device):
        if device.deviceTypeId == 'smaIndigoInverter' and device.id in self.inverters.keys():
            client = self.inverters.get(device.id)
            client.close()
            del self.inverters[device.id]
            indigo.server.log('Stopped communication with inverter device: {}'.format(device.name),
                              type=DISPLAY_NAME)

        elif device.deviceTypeId == 'smaIndigoAggregation' and device.id in self.aggregations.keys():
            del self.aggregations[device.id]

    ###########################

    def add_dependencies(self, device_id, dependency_list):
        dependency_set = self.dependencies.get(device_id, set())
        for element in dependency_set:
            dependency_set.add(element)
        self.dependencies[device_id] = dependency_set

    def update_inverters(self):
        """
        Updates the states of all Inverters.
        If, for some reason, a ConnectionError is found, it attempts to reconnect the inverter
        """
        for device_id, client in self.inverters.items():
            try:
                states = client.generate_states()
                IndigoService.update_inverter_states(device_id, states)

            except ModbusException:
                indigo.server.log('Lost connection to inverter: {}. Reconnecting...'.format(device_id),
                                  type=DISPLAY_NAME)
                client.close()
                client.connect()
            except AttributeError:
                indigo.server.log('Lost connection to inverter: {}. Reconnecting...'.format(device_id),
                                  type=DISPLAY_NAME)
                client.close()
                client.connect()

    def update_aggregations(self):
        """
        Updates the value state of all aggregations.
        """
        no_dependency_aggregations = set(filter(lambda x: len(self.dependencies[x]) == 0, self.dependencies))

        for aggregation_id in no_dependency_aggregations:
            aggregation = self.aggregations.get(aggregation_id)
            aggregation.calculate_value()
            IndigoService.update_aggregation_states(aggregation)

        aggregations_with_dependencies = set(filter(lambda x: len(self.dependencies[x]) == 0, self.dependencies))

        processed = no_dependency_aggregations

        for aggregation_id in aggregations_with_dependencies:
            if aggregation_id not in processed:
                self._update_aggregations_rec(aggregation_id, processed)

    def _update_aggregations_rec(self, device_id, processed):
        # Process dependencies
        for dependency_id in self.dependencies[device_id]:
            if dependency_id not in processed:
                if not self._update_aggregations_rec(dependency_id, processed):
                    indigo.server.log(
                        'Unable to load device {} dependencies.'.format(device_id) +
                        'Maybe some of them were deleted. Device will be disabled.',
                        type=DISPLAY_NAME
                    )
                    del self.aggregations[device_id]
                    del self.dependencies[device_id]
                    return False

        aggregation = self.aggregations.get(device_id)
        if aggregation is None:
            return False

        aggregation.calculate_value()
        IndigoService.update_aggregation_states(aggregation)

        processed.add(device_id)
        return True

    def reconnect_all(self):
        """
        Reconnects all devices
        """
        indigo.server.log('Reconnecting all devices........%d devices' % len(self.inverters))

        for device_id, client in self.inverters.items():
            client.close()
            if client.connect():
                indigo.server.log('    - {} --- OK'.format(device_id), type=DISPLAY_NAME)
            else:
                indigo.server.log('    - {} --- FAILED'.format(device_id), type=DISPLAY_NAME)

    def reconnect_device(self, valuesDict, typeId):
        """
        Reconnects a specific device
        """
        indigo.server.log('Reconnect Device is not yet implemented', type=DISPLAY_NAME)

    def get_available_inverter_states(self, filter="", valuesDict=None, typeId="", targetId=0):
        return [
            ("serialNumber", "Serial Number"),
            ("acPower", "AC Power"),
            ("acApparentPower", "AC Apparent Power"),
            ("acCurrent", "AC Current"),
            ("acVoltage", "AC Voltage"),
            ("gridFreq", "Grid Frequency"),
            ("dcPower", "DC Power"),
            ("dcInputVoltage", "DC Input Voltage"),
            ("deviceTemperature", "Device Temperature"),
            ("dailyYield", "Daily Yield"),
            ("totalYield", "Total Yield"),
            ("totalOperationTime", "Total Operation Time"),
            ("feedInTime", "Feed-In Time"),
            ("intermediateVoltage", "Intermediate Voltage"),
            ("isolationResistance", "Isolation Resistance"),
            ("totalEnergyFromGrid", "Total Energy From Grid"),
            ("totalEnergyToGrid", "Total Energy To Grid"),
            ("powerFromGrid", "Power From Grid"),
            ("powerToGrid", "Power To Grid"),
        ]
