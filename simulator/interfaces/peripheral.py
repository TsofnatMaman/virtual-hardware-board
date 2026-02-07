"""Abstract peripheral interface definitions."""

from abc import ABC, abstractmethod


class BasePeripherals(ABC):
    """Abstract interface for memory-mapped peripherals."""

    def write(self, offset: int, size: int, value: int) -> None:
        """Default write implementation that delegates to legacy
        `write_register` if the subclass provides it. Subclasses should
        override this for proper behavior.
        """
        # If subclass implemented legacy write_register, call it
        subclass_write = getattr(self.__class__, "write_register", None)
        if subclass_write is not None and subclass_write is not BasePeripherals.write_register:
            # Call the subclass implementation
            subclass_write(self, offset, value)
            return

        raise NotImplementedError("peripheral must implement write(offset,size,value)")

    def read(self, offset: int, size: int) -> int:
        """Default read implementation that delegates to legacy
        `read_register` if the subclass provides it. Subclasses should
        override this for proper behavior.
        """
        subclass_read = getattr(self.__class__, "read_register", None)
        if subclass_read is not None and subclass_read is not BasePeripherals.read_register:
            return subclass_read(self, offset)

        raise NotImplementedError("peripheral must implement read(offset,size)")

    # Backwards-compatible helpers for older code/tests. These treat the
    # register access as a 32-bit access and delegate to the new API.
    def write_register(self, offset: int, value: int) -> None:
        """Compatibility wrapper: write 32-bit register."""
        self.write(offset, 4, value)

    def read_register(self, offset: int) -> int:
        """Compatibility wrapper: read 32-bit register."""
        return self.read(offset, 4)

    @abstractmethod
    def reset(self) -> None:
        """Reset peripheral to power-on state."""
        raise NotImplementedError
