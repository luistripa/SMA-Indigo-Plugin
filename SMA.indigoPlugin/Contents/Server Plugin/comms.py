import socket
from struct import pack
from binascii import b2a_hex
from pymodbus.client.sync import ModbusTcpClient as ModbusClient
from pymodbus.payload import BinaryPayloadDecoder
from pymodbus.constants import Endian


class Client:
    REGISTERS = {
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
        '30525': [4, 'U64', 'FIX0', 'feedInTime'],  # Feed-In Time (S)
        '30975': [2, 'S32', 'FIX2', 'intermediateVoltage'],  # Intermediate Voltage (V)
        '30225': [2, 'S32', 'FIX0', 'isolationResistance'],  # Isolation Resistance (Ohm) (u'\u03a9')
        '30581': [2, 'U32', 'FIX0', 'totalEnergyFromGrid'],  # Energy from Grid (Wh)
        '30583': [2, 'U32', 'FIX0', 'totalEnergyToGrid'],  # Energy to Grid (Wh)
        '30865': [2, 'S32', 'FIX0', 'powerFromGrid'],  # Power from Grid (W)
        '30867': [2, 'S32', 'FIX0', 'powerToGrid'],  # Power to Grid (W)
    }

    def __init__(self, host, port):
        self.client = ModbusClient(host=host, port=port)

    def connect(self):
        return self.client.connect()

    def close(self):
        self.client.close()

    def generate_states(self):
        states = {}
        for register in self.REGISTERS.keys():
            state, value = self._read_register(register)
            states[state] = value
        return states

    def _read_register(self, register):
        state = self.REGISTERS[register][3]
        received = self.client.read_input_registers(address=int(register),
                                                    count=self.REGISTERS.get(register)[0],
                                                    unit=3)
        data = BinaryPayloadDecoder.fromRegisters(received.registers,
                                                  byteorder=Endian.Big,
                                                  wordorder=Endian.Big)

        data_type = self.REGISTERS.get(register)[1]
        fix = self.REGISTERS.get(register)[2]

        data = self._decode_data(data, data_type)
        data = self._unfix_data(data, fix)

        return state, data

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
