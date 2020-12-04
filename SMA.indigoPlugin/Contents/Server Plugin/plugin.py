import indigo
import socket
from struct import pack
from binascii import b2a_hex
from pymodbus.client.sync import ModbusTcpClient as ModbusClient
from pymodbus.payload import BinaryPayloadDecoder
from pymodbus.constants import Endian

DISPLAY_NAME = 'Energy Meter'


class Plugin(indigo.PluginBase):

    class Inverter:

        def __init__(self, dev, host, port):
            self.device = dev
            self.states = list()
            self.host = host
            self.port = port
            self.client = None
            self.connect()

        def insertState(self, state, value):
            self.states.append( {'key':state, 'value':value} )

        def updateStates(self):
            self.device.updateStatesOnServer(self.states)
            self.states = list()  # Reload states

        def connect(self):
            self.client = ModbusClient(host=self.host, port=self.port)
            return self.client.connect()

        def close(self):
            self.client.close()

    class InverterBundle:

        def __init__(self, bundle):
            self.bundle = bundle
            self.device = list()
            self.states = dict()

        def insertInverter(self, dev):
            self.device.append(dev)

        def insertState(self, state, value):
            self.states[state] += value

        def updateBundleStates(self):
            pass

        def reconnectAll(self):
            pass

    class HomeManager:

        def __init__(self, mcastGroup, mcastPort):
            self.mcastGroup = mcastGroup
            self.mcastPort = mcastPort
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
            powerFromGrid = self.hex2dec(info_ascii[64:72])/10
            totalPowerFromGrid = self.hex2dec(info_ascii[80:96])/3600000
            powerToGrid = self.hex2dec(info_ascii[104:112])/10
            totalPowerToGrid = self.hex2dec(info_ascii[120:136])/3600000
            return {{'powerFromGrid': powerFromGrid},
                    {'totalPowerFromGrid': totalPowerFromGrid},
                    {'powerToGrid': powerToGrid},
                    {'totalPowerToGrid': totalPowerToGrid}}

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
        self.bundles = list()

        """
        Stores all Device objects in the system.
        """
        self.inverters = list()

    def startup(self):
        pass

    def shutdown(self):
        # Close connection to all inverters
        for inv in self.inverters:
            inv.client.close()

    def runConcurrentThread(self):
        try:

            """while True:
                for reg in self.registers:
                    for bundle in self.bundles:
                        state = self.registers.get(reg)[3]
                        sumValues = 0
                        for dev in self.bundles[bundle]:
                            value = self.getReading(self.devices[dev], reg)
                            sumValues += value
                            dev.updateStateOnServer(state, value)
                        self.updateStateOnBundle(state, sumValues)"""

            while True:
                for inv in self.inverters:
                    try:
                        for reg in self.registers:
                                state = self.registers.get(reg)[3]
                                value = self.getInverterRegister(inv.client, reg)
                                inv.insertState(state, value)
                        inv.updateStates()

                    except ConnectionError:
                        inv.connect()  # Reconnect inverter

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
                self.inverters.append(inverter)

                if inverter.connect():
                    indigo.server.log('Started communication with inverter device: '+inverter.device.name,
                                      type=DISPLAY_NAME)
                    dev.updateStateImageOnServer(indigo.EnergyMeterOn)

                else:
                    indigo.server.log('Failed to establish connection to inverter.',
                                      type=DISPLAY_NAME)

        elif dev.deviceTypeId == 'inverterBundle':
            bundle = self.InverterBundle(dev)
            for inverterId in props['inverterList']:
                inverter = indigo.devices[inverterId]
                bundle.insertInverter(inverter)
            self.bundles.append(bundle)

        elif dev.deviceTypeId == 'homeManager':
            pass

        else:
            indigo.server.log('Unknown device type id.', type=DISPLAY_NAME)

    def deviceStopComm(self, dev):

        if dev.deviceTypeId == 'solarInverter' and dev in self.devices:
            del self.devices[dev]

    ###########################

    def getInverterRegister(self, client, register):
        received = client.read_input_registers(address=int(register),
                                               count=self.registers.get(register)[0],
                                               unit=3)
        message = BinaryPayloadDecoder.fromRegisters(received.registers,
                                                     byteorder=Endian.Big,
                                                     wordorder=Endian.Big)

        dataType = self.registers.get(register)[1]

        if dataType == "S32":
            interpreted = message.decode_32bit_int()
            if interpreted == -2147483648:
                interpreted = 0
        elif dataType == "U32":
            interpreted = message.decode_32bit_uint()
            if interpreted == 0xFFFFFFFF:
                interpreted = 0
        elif dataType == "U64":
            interpreted = message.decode_64bit_uint()
            if interpreted == 0xFFFFFFFFFFFFFFFF:
                interpreted = 0
        elif dataType == "STR32":
            interpreted = message.decode_string(32).decode("utf-8").strip("\x00")
            if interpreted == 0:
                interpreted = 0
        elif dataType == 'S16':
            interpreted = message.decode_16bit_int()
            if interpreted == 0x8000:
                interpreted = 0
        elif dataType == 'U16':
            interpreted = message.decode_16bit_uint()
            if interpreted == 0xFFFF:
                interpreted = 0
        else:
            interpreted = message.decode_16bit_uint()

        fix = self.registers.get(register)[2]

        if fix == "FIX3":
            displayData = float(interpreted) / 1000
        elif fix == "FIX2":
            displayData = float(interpreted) / 100
        elif fix == "FIX1":
            displayData = float(interpreted) / 10
        else:
            displayData = interpreted

        return displayData

    def getHomeManagerData(self):
        pass

    def reconnectAll(self):
        indigo.server.log('Reconnecting all devices........%d devices' % len(self.devices))
        for inv in self.inverters:
            if inv.connect():
                indigo.server.log('    - %s --- OK' % inv.device.name, type=DISPLAY_NAME)
            else:
                indigo.server.log('    - %s --- FAILED' % inv.device.name, type=DISPLAY_NAME)

    def reconnectDevice(self, valuesDict, typeId):
        indigo.server.log('Not yet implemented', type=DISPLAY_NAME)


    def reconnectBundle(self, valuesDict, typeId):
        bundle = indigo.devices[valuesDict['targetBundle']]
        bundle.reconnectAll()
