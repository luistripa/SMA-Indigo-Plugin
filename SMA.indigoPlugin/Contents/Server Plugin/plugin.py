import indigo

from objects import *
from services import IndigoService, ModBusService

DISPLAY_NAME = 'SMA Energy'


class Plugin(indigo.PluginBase):
    def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
        indigo.PluginBase.__init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs)

        """
        Stores all Inverter objects in the system.
        """
        self.inverters = dict()

        """
        Stores all aggregations.
        Key is device id, Value is Aggregation Subclass object
        """
        self.aggregations = dict()

        self.modBusService = ModBusService()

    def startup(self):
        pass

    def shutdown(self):
        # Close connection to all inverters
        for client in self.modBusService.clients:
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

    def deviceStartComm(self, dev):
        properties = dev.pluginProps

        if dev.deviceTypeId == 'smaIndigoInverter':
            inverter = Inverter(dev)

            if self.modBusService.register_inverter(inverter, properties['inverterAddress'], int(properties['inverterPort'])):
                self.inverters[dev.id] = inverter
                indigo.server.log('Started communication with inverter device: {}'.format(inverter.device.name),
                                  type=DISPLAY_NAME)
            else:
                indigo.server.log('Failed to establish connection to inverter: {}'.format(inverter.device.name),
                                  type=DISPLAY_NAME)

        elif dev.deviceTypeId == "smaIndigoAggregation":
            aggregation_type = properties["aggregationType"]

            if aggregation_type == "inverterList":
                inverters = [self.inverters[str(inverter_id)] for inverter_id in properties["inverterList"]]
                state = properties["inverterListState"]
                operation = properties["inverterListOperation"]
                aggregation = InverterListAggregation(dev, inverters, state, operation)
                self.aggregations[dev.id] = aggregation

            elif aggregation_type == "aggregationList":
                aggregations = [self.aggregations[str(aggregation_id)] for aggregation_id in properties["aggregationList"]]
                operation = properties["aggregationListOperation"]
                aggregation = AggregationListAggregation(dev, aggregations, operation)
                self.aggregations[dev.id] = aggregation

            elif aggregation_type == "inverterToInverter":
                inverter1 = self.inverters.get(str(properties["inverterToInverter_Inverter1"]))
                inverter1_state = properties["inverterToInverter_Inverter1State"]
                inverter2 = self.inverters.get(str(properties["inverterToInverter_Inverter2"]))
                inverter2_state = properties["inverterToInverter_Inverter2State"]
                operation = properties["inverterToInverterOperation"]
                aggregation = InverterToInverterAggregation(
                    dev,
                    inverter1,
                    inverter1_state,
                    inverter2,
                    inverter2_state,
                    operation
                )
                self.aggregations[dev.id] = aggregation

            elif aggregation_type == "aggregationToAggregation":
                aggregation_1 = self.aggregations.get(str(properties["aggregationToAggregation_Aggregation1"]))
                aggregation_2 = self.aggregations.get(str(properties["aggregationToAggregation_Aggregation2"]))
                operation = properties["aggregationToAggregationOperation"]
                aggregation = AggregationToAggregationAggregation(dev, aggregation_1, aggregation_2, operation)
                self.aggregations[dev.id] = aggregation

        else:
            indigo.server.log('Unknown device type id: {}'.format(dev.deviceTypeId), type=DISPLAY_NAME)

    def deviceStopComm(self, dev):
        if dev.deviceTypeId == 'smaIndigoInverter' and dev.id in self.inverters.keys():
            self.inverters[dev.name].disconnect()
            del self.inverters[dev.id]
        elif dev.deviceTypeId == 'smaIndigoAggregation' and dev.id in self.aggregations.keys():
            del self.aggregations[dev.id]

    ###########################

    def update_inverters(self):
        """
        Updates the states of all Inverters.
        If, for some reason, a ConnectionError is found, it attempts to reconnect the inverter
        """
        for inverter in self.inverters.values():
            try:
                states = self.modBusService.get_inverter_states(inverter)
                inverter.update_states(states)
                IndigoService.update_inverter_states(inverter)

            except ConnectionError:
                indigo.server.log('Lost connection to inverter: {}. Reconnecting...'.format(inverter.device.name),
                                  type=DISPLAY_NAME)
                self.modBusService.reconnect_inverter(inverter)
            except AttributeError:
                indigo.server.log('Lost connection to inverter: {}. Reconnecting...'.format(inverter.device.name),
                                  type=DISPLAY_NAME)
                self.modBusService.reconnect_inverter(inverter)

    def update_aggregations(self):
        """
        Updates the value state of all aggregations.
        """
        for aggregation in self.aggregations.values():
            aggregation.calculate_value()
            IndigoService.update_aggregation_states(aggregation)

    def reconnect_all(self):
        """
        Reconnects all devices
        """
        indigo.server.log('Reconnecting all devices........%d devices' % len(self.devices))

        for inverter in self.inverters.values():
            if self.modBusService.reconnect_inverter(inverter):
                indigo.server.log('    - {} --- OK'.format(inverter.device.name), type=DISPLAY_NAME)
            else:
                indigo.server.log('    - {} --- FAILED'.format(inverter.device.name), type=DISPLAY_NAME)

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
