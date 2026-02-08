# Virtual Hardware Board

## Example

```bash
python examples/run_led_blink.py
```

## GUI

```bash
# install GUI dependencies
pip install PySide6 psutil
# or
pip install -r requirements-gui.txt

# run GUI (TM4C123 + LED blink firmware)
python examples/run_gui.py

# or run directly
python -m simulator_gui --board tm4c123 --firmware firmware/led_blink/tm4c/firmware.bin
```
