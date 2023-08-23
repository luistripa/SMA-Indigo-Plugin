from typing import Optional, Any, Tuple, List
from dataclasses import dataclass


@dataclass
class Inverter:
    serialNumber: str = None
    acPower: int = None
    acCurrent: int = None
    acVoltage: int = None
    gridFreq: int = None
    deviceTemperature: int = None
    totalOperationTime: int = None
    feedInTime: int = None
    dailyYield: int = None
    totalYield: int = None

    @classmethod
    def from_registers(cls, registers: List[Tuple['ModbusRegister', Any]]):
        inverter = cls()

        for register, data in registers:
            if hasattr(inverter, register.name):
                setattr(inverter, register.name, data)

        return inverter


@dataclass
class HomeManager:
    totalPowerFromGrid: float
    totalPowerToGrid: float
    phase1PowerFromGrid: float
    phase1PowerToGrid: float
    phase2PowerFromGrid: float
    phase2PowerToGrid: float
    phase3PowerFromGrid: float
    phase3PowerToGrid: float

    @classmethod
    def from_data(cls, data: bytes):
        return cls(
            totalPowerFromGrid=int.from_bytes(data[34:36], byteorder='big') / 10,
            totalPowerToGrid=int.from_bytes(data[54:56], byteorder='big') / 10,
            phase1PowerFromGrid=int.from_bytes(data[170:172], byteorder='big') / 10,
            phase1PowerToGrid=int.from_bytes(data[190:192], byteorder='big') / 10,
            phase2PowerFromGrid=int.from_bytes(data[314:316], byteorder='big') / 10,
            phase2PowerToGrid=int.from_bytes(data[334:336], byteorder='big') / 10,
            phase3PowerFromGrid=int.from_bytes(data[458:460], byteorder='big') / 10,
            phase3PowerToGrid=int.from_bytes(data[478:480], byteorder='big') / 10
        )


@dataclass
class LogicalMeter:
    # TODO: Consider having meters for specific inverters
    device_id: int
    totalProduction: float  # Sum of all inverter acPower states
    totalConsumption: float  # totalProduction + powerFromGrid - powerToGrid
    solarConsumption: float  # totalProduction - powerToGrid
    solarConsumptionPercentage: float  # solarConsumption / totalProduction * 100


@dataclass
class ModbusRegister:
    """Represents a ModBus register."""
    address: int
    size: int
    dataType: str
    format: str
    name: str
    unit: Optional[str]
