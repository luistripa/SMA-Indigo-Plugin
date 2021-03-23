import indigo
import socket
from struct import pack
from binascii import b2a_hex
from pymodbus.client.sync import ModbusTcpClient as ModbusClient
from pymodbus.payload import BinaryPayloadDecoder
from pymodbus.constants import Endian

from objects import Inverter, InverterBundle
from typing import Dict, List, Union
import traceback

DISPLAY_NAME = 'Energy Meter'


class Plugin(indigo.PluginBase):

    class HomeManager:
        """
        Output values are not correct
        """

        def __init__(self, device):
            self.device = device
            self.mcastGroup = device.pluginProps['multicastGroup']
            self.mcastPort = int(device.pluginProps['multicastPort'])
            self.setup()

        def hex2dec(self, s):
            return int(s, 16)

        def setup(self):
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock.bind(('', self.mcastPort))
            mreq = pack("4sl", socket.inet_aton(self.mcastGroup), socket.INADDR_ANY)
            self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

        def getReading(self):
            info = self.sock.recv(600)
            info_ascii = b2a_hex(info)
            powerFromGrid = self.hex2dec(info_ascii[64:72]) / 10
            totalPowerFromGrid = self.hex2dec(info_ascii[80:96]) / 3600000
            powerToGrid = self.hex2dec(info_ascii[104:112]) / 10
            totalPowerToGrid = self.hex2dec(info_ascii[120:136]) / 3600000
            return [{'key': 'powerFromGrid', 'value': powerFromGrid},
                    {'key': 'totalPowerFromGrid', 'value': totalPowerFromGrid},
                    {'key': 'powerToGrid', 'value': powerToGrid},
                    {'key': 'totalPowerToGrid', 'value': totalPowerToGrid}]

        def close(self):
            self.sock.close()

    def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
        indigo.PluginBase.__init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs)

        self.registers = {
            '30057': [2, 'U32', 'RAW', 'serialNumber'],  # Serial number
            '30775': [2, 'S32', 'FIX0', 'acPower'],  # AC Power (W)
            '30813': [2, 'S32', 'FIX0', 'acApparentPower'],  # AC Apparent Power (VA)
            '30977': [2, 'S32', 'FIX3', 'acCurrent'],  # AC Current (A)
            '30783': [2, 'S32', 'FIX2', 'acVoltage'],  # AC Voltage (V)
            '30803': [2, 'U32', 'FIX2', 'gridFreq'],  # Grid Freq (Hz)
            '30773': [2, 'S32', 'FIX0', 'dcPower'],  # DC Power (W)
            '30771': [2, 'S32', 'FIX2', 'dcInputVoltage'],  # DC Input Voltage (V)
            '30953': [2, 'S32', 'FIX1', 'deviceTemperature'],  # Device Temp (degrees Celsius)
            '30517': [4, 'U64', 'FIX0', 'dailyYield'],  # Daily Yield (Wh)
            '30513': [4, 'U64', 'FIX0', 'totalYield'],  # Total Yield (Wh)
            '30521': [4, 'U64', 'FIX0', 'totalOperationTime'],  # Operation Time (S)
            '30525': [4, 'U64', 'FIX0', 'feedinTime'],  # Feed-In Time (S)
            '30975': [2, 'S32', 'FIX2', 'intermediateVoltage'],  # Intermediate Voltage (V)
            '30225': [2, 'S32', 'FIX0', 'isolationResistance'],  # Isolation Resistance (Ohm) (u'\u03a9')
            '30581': [2, 'U32', 'FIX0', 'totalEnergyFromGrid'],  # Energy from Grid (Wh)
            '30583': [2, 'U32', 'FIX0', 'totalEnergyToGrid'],  # Energy to Grid (Wh)
            '30865': [2, 'S32', 'FIX0', 'powerFromGrid'],  # Power from Grid (W)
            '30867': [2, 'S32', 'FIX0', 'powerToGrid'],  # Power to Grid (W)
        }

        """
        Stores all bundles. A bundle is a group of devices. Each bundle is a specific device that stores the average
        and total values of all inverters in the bundle.
        """
        self.bundles: Dict[str, InverterBundle] = dict()

        """
        Stores all Inverter objects in the system.
        """
        self.inverters: Dict[str, Inverter] = dict()

        """
        Stores all HomeManager objects in the system
        """
        self.homeManagers = dict()

    def startup(self):
        pass

    def shutdown(self):
        # Close connection to all inverters
        for inv in self.inverters.values():
            inv.client.close()
        for hm in self.homeManagers.values():
            hm.close()

    def runConcurrentThread(self):
        try:
            while True:
                self.update_inverters()
                self.update_inverter_bundles()
                self.update_home_managers()
                self.sleep(10)

        except self.StopThread:
            self.shutdown()

    def closedPrefsConfigUi(self, valuesDict, userCancelled):
        if not userCancelled:
            pass

    def deviceStartComm(self, dev):
        props = dev.pluginProps

        if dev.deviceTypeId == 'solarInverter':
            inverter = self.Inverter(dev, props['inverterAddress'], int(props['inverterPort']))

            if inverter.connect():
                self.inverters[dev.name] = inverter
                indigo.server.log('Started communication with inverter device: ' + inverter.device.name,
                                  type=DISPLAY_NAME)

            else:
                indigo.server.log('Failed to establish connection to inverter: ' + inverter.device.name,
                                  type=DISPLAY_NAME)

        elif dev.deviceTypeId == 'inverterBundle':
            bundle = InverterBundle(dev)
            for inverterId in props['inverterList']:
                inverter = indigo.devices[inverterId]
                bundle.add_inverter(inverter)
            self.bundles[dev.name] = bundle

        elif dev.deviceTypeId == 'homeManager':
            home_manager = self.HomeManager(dev)
            self.homeManagers[dev.name] = home_manager

        else:
            indigo.server.log('Unknown device type id.', type=DISPLAY_NAME)

    def deviceStopComm(self, dev):
        if dev.deviceTypeId == 'solarInverter' and dev.name in self.inverters.keys():
            self.inverters[dev.name].disconnect()
            del self.inverters[dev.name]

        elif dev.deviceTypeId == 'homeManager' and dev in self.homeManagers.keys():
            self.homeManagers[dev.name].close()
            del self.homeManagers[dev.name]

    ###########################

    def update_inverters(self):
        for inv in self.inverters.values():
            try:
                for reg in self.registers:
                    state = self.registers.get(reg)[3]
                    value = self.getInverterRegister(inv.client, reg)
                    inv.update_state(state, value)
                inv.update_states_on_server()

            except ConnectionError:
                indigo.server.log('Lost connection to inverter: ' + inv.device.name + ". Reconnecting...",
                                  type=DISPLAY_NAME)
                inv.connect()  # Reconnect inverter

    def update_inverter_bundles(self):
        for bundle in self.bundles.values():
            bundle.update_all_states()

    def update_home_managers(self):
        for hm in self.homeManagers.values():
            try:
                states = hm.getReading()
                hm.device.updateStatesOnServer(states)
            except Exception as e:
                indigo.server.log(traceback.print_exc(), type=DISPLAY_NAME)

    def getInverterRegister(self, client, register):
        received = client.read_input_registers(address=int(register),
                                               count=self.registers.get(register)[0],
                                               unit=3)
        data = BinaryPayloadDecoder.fromRegisters(received.registers,
                                                  byteorder=Endian.Big,
                                                  wordorder=Endian.Big)

        data_type = self.registers.get(register)[1]
        fix = self.registers.get(register)[2]

        data = self._decode_data(data, data_type)
        data = self._unfix_data(data, fix)

        return data

    @staticmethod
    def _decode_data(data, data_type):
        if data_type == "S32":
            data_decoded = data.decode_32bit_int()

        elif data_type == "U32":
            data_decoded = data.decode_32bit_uint()

        elif data_type == "U64":
            data_decoded = data.decode_64bit_uint()

        elif data_type == "STR32":
            data_decoded = data.decode_string(32).decode("utf-8").strip("\x00")

        elif data_type == 'S16':
            data_decoded = data.decode_16bit_int()

        elif data_type == 'U16':
            data_decoded = data.decode_16bit_uint()

        else:
            data_decoded = data.decode_16bit_uint()

        # When solar inverters are not generating, the output values are a fixed value.
        # The following if compensates those values and turns them to zero
        if data_decoded in [-2147483648, 0xFFFFFFFF, 0xFFFFFFFFFFFFFFFF, 0x8000, 0xFFFF]:
            data_decoded = 0

        return data_decoded

    @staticmethod
    def _unfix_data(data, fix):
        if fix == "FIX3":
            data = float(data) / 1000
        elif fix == "FIX2":
            data = float(data) / 100
        elif fix == "FIX1":
            data = float(data) / 10
        else:
            data = data

        return data

    def reconnect_all(self):
        indigo.server.log('Reconnecting all devices........%d devices' % len(self.devices))
        for inv in self.inverters.values():
            if inv.connect():
                indigo.server.log('    - %s --- OK' % inv.device.name, type=DISPLAY_NAME)
            else:
                indigo.server.log('    - %s --- FAILED' % inv.device.name, type=DISPLAY_NAME)

    def reconnect_device(self, valuesDict, typeId):
        indigo.server.log('Not yet implemented', type=DISPLAY_NAME)

    def reconnect_bundle(self, valuesDict, typeId):
        bundle = indigo.devices[valuesDict['targetBundle']]
        bundle.reconnectAll()
