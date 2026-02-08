from simulator.core.sysctl import SysCtl, _infer_size
from simulator.utils.config_loader import SysCtlConfig, load_config


def test_sysctl_read_write_reset_tm4c():
    cfg = load_config("tm4c123", path="simulator/tm4c/config.yaml").sysctl
    sysctl = SysCtl(cfg, base_addr=cfg.base)

    reg = cfg.registers["rcgcgpio"]
    assert sysctl.read(reg, 4) == 0

    sysctl.write(reg, 4, 0xA5A5A5A5)
    assert sysctl.read(reg, 4) == 0xA5A5A5A5
    assert sysctl.read(reg, 1) == 0xA5

    sysctl.write(0x123, 4, 0xDEADBEEF)  # unknown offset ignored
    assert sysctl.read(0x123, 4) == 0

    sysctl.reset()
    assert sysctl.read(reg, 4) == 0


def test_sysctl_infer_size_and_empty_registers():
    assert _infer_size({}) == 0x100

    cfg = load_config("stm32f4", path="simulator/stm32/config.yaml").sysctl
    sysctl = SysCtl(cfg, base_addr=cfg.base)

    max_offset = max(cfg.registers.values())
    assert sysctl.size >= max_offset + 4

    empty_cfg = SysCtlConfig(base=0x40000000, registers={})
    empty_sysctl = SysCtl(empty_cfg, base_addr=empty_cfg.base)
    assert empty_sysctl.size == 0x100
    assert empty_sysctl.read(0x0, 4) == 0
