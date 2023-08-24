import threading
from typing import Optional, List, Any, Tuple

import socket
import struct

from pymodbus.client.sync import ModbusTcpClient as ModbusClient
from pymodbus.payload import BinaryPayloadDecoder
from pymodbus.constants import Endian

from objects import Inverter, HomeManager, ModbusRegister


class InverterClient:
    REGISTERS: List[ModbusRegister] = [
        ModbusRegister(30057, 2, 'U32', 'RAW', 'serialNumber', None),           # Serial number
        ModbusRegister(30775, 2, 'S32', 'FIX0', 'acPower', 'W'),                # AC Power (W)
        ModbusRegister(30977, 2, 'S32', 'FIX3', 'acCurrent', 'A'),              # AC Current (A)
        ModbusRegister(30783, 2, 'S32', 'FIX2', 'acVoltage', 'V'),              # AC Voltage (V)
        ModbusRegister(30803, 2, 'U32', 'FIX2', 'gridFreq', 'Hz'),              # Grid Freq (Hz)
        ModbusRegister(30953, 2, 'S32', 'FIX1', 'deviceTemperature', 'C'),      # Device Temp (degrees Celsius)
        ModbusRegister(30517, 4, 'U64', 'FIX0', 'dailyYield', 'Wh'),            # Daily Yield (Wh)
        ModbusRegister(30513, 4, 'U64', 'FIX0', 'totalYield', 'Wh'),            # Total Yield (Wh)
        ModbusRegister(30521, 4, 'U64', 'FIX0', 'totalOperationTime', 'S'),     # Operation Time (S)
        ModbusRegister(30525, 4, 'U64', 'FIX0', 'feedInTime', 'S'),             # Feed-In Time (S)
    ]

    def __init__(self, host: str, port: int):
        self.client = ModbusClient(host=host, port=port)

    def connect(self) -> bool:
        return self.client.connect()

    def close(self):
        self.client.close()

    def reconnect(self) -> bool:
        self.close()
        return self.connect()
    
    def get_inverter_data(self) -> Optional[Inverter]:
        # Check if client is connected
        if not self.client.is_socket_open():
            return None

        registers: List[Tuple[ModbusRegister, Any]] = list()
        for register in self.REGISTERS:
            registers.append(self._read_register(register))

        return Inverter.from_registers(registers)

    def _read_register(self, register: ModbusRegister):
        received = self.client.read_input_registers(
            address=register.address,
            count=register.size,
            unit=3
        )
        data = BinaryPayloadDecoder.fromRegisters(
            received.registers,
            byteorder=Endian.Big,
            wordorder=Endian.Big
        )

        data = self._decode_data(data, register.dataType)
        data = self._unfix_data(data, register.format)

        return register, data

    def _decode_data(self, data: BinaryPayloadDecoder, data_type: str):
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

    def _unfix_data(self, data, fix: str):
        if fix == "FIX3":
            data = float(data) / 1000
        elif fix == "FIX2":
            data = float(data) / 100
        elif fix == "FIX1":
            data = float(data) / 10

        return data


class HomeManagerClientThread(threading.Thread):
    """Thread that listens for HomeManager broadcasts and updates the HomeManager object

    After starting the thread the HomeManager object can be retrieved with the get_home_manager() method.
    However, it may take a few seconds for the HomeManager to be discovered and the object to be updated. It is recommended to use
    the home_manager_present_event to wait for the HomeManager to be discovered. After this event is set, it is
    guaranteed that the HomeManager object is not None and will have values present.
    """

    MULTICAST_IP = "239.12.255.254"
    MULTICAST_PORT = 9522

    home_manager_present_event = threading.Event()
    stop_event = threading.Event()

    def __init__(self, device_id: int) -> None:
        super().__init__()
        self.device_id = device_id
        self._sock = None
        self.home_manager: Optional[HomeManager] = None

        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind(("", self.MULTICAST_PORT))
        mreq = struct.pack("4sl", socket.inet_aton(self.MULTICAST_IP), socket.INADDR_ANY)

        self._sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

    def run(self) -> None:
        while not self.stop_event.is_set():
            data = self._sock.recv(10240)

            if data[0:3] != b'SMA' or data[16:18].hex() != '6069':
                continue

            self.home_manager = HomeManager.from_data(data)
            self.home_manager_present_event.set()

    def get_home_manager(self) -> Optional[HomeManager]:
        return self.home_manager

    def stop(self):
        self.stop_event.set()
        self._sock.close()
