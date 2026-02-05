from simulator.interfaces.peripheral import BasePeripherals

from typing import override

class Periphral(BasePeripherals):
    
    @override
    def reset():
        ...