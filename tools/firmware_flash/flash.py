# download.py — MC602P 固件烧录

import os
import struct
import time
from pathlib import Path

import serial

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

FLASH_BASE = 0x8000000

SLOTS = {
    "RunA": FLASH_BASE + (384 * 1024),
    "RunB": FLASH_BASE + (512 * 1024),
    "RunC": FLASH_BASE + (612 * 1024),
    "RunD": FLASH_BASE + (712 * 1024),
    "RunE": FLASH_BASE + (812 * 1024),
    "RunF": FLASH_BASE + (912 * 1024),
}
PROGRAM_GCC = FLASH_BASE + (52 * 1024)

BUFFER_SIZE = 4096
BAUDRATE    = 1_000_000

H2D_HEAD = bytes.fromhex("55 AA")
D2H_HEAD = bytes.fromhex("66 BB")

CMD_PING         = 0x01
CMD_WRITE_BUFFER = 0x10
CMD_RAM2FLASH    = 0x20
CMD_RAM2FLASH_OK = 0x21
CMD_RUNCODE      = 0x40
CMD_RUNCODE_OK   = 0x41

PING_SEND_SIZE = 8
PING_RECV_SIZE = 10
DW_SEND_SIZE   = BUFFER_SIZE + 8
DW_RECV_SIZE   = 8
RF_SEND_SIZE   = 11
RF_RECV_SIZE   = 11
RC_SEND_SIZE   = 11
RC_RECV_SIZE   = 11


# ---------------------------------------------------------------------------
# 校验
# ---------------------------------------------------------------------------

def _checksum(data: bytes) -> int:
    s = sum(data[:-1]) & 0xFF
    return (~s) & 0xFF


def _check(data: bytes) -> bool:
    return data[-1] == _checksum(data)


# ---------------------------------------------------------------------------
# 帧
# ---------------------------------------------------------------------------

def _ping_frame() -> bytes:
    buf = bytearray(PING_SEND_SIZE)
    buf[0] = 0x55
    buf[1] = 0xAA
    buf[2] = 0x00
    buf[3] = CMD_PING
    buf[4] = PING_SEND_SIZE & 0xFF
    buf[5] = (PING_SEND_SIZE >> 8) & 0xFF
    buf[6] = 0x00
    buf[7] = _checksum(buf)
    return bytes(buf)


def _write_buffer_frame(chunk: bytes) -> bytes:
    buf = bytearray(DW_SEND_SIZE)
    buf[0] = 0x55
    buf[1] = 0xAA
    buf[2] = 0x00
    buf[3] = CMD_WRITE_BUFFER
    buf[4] = DW_SEND_SIZE & 0xFF
    buf[5] = (DW_SEND_SIZE >> 8) & 0xFF
    buf[6] = 0x00
    for i in range(BUFFER_SIZE):
        buf[7 + i] = chunk[i]
    buf[DW_SEND_SIZE - 1] = _checksum(buf)
    return bytes(buf)


def _ram2flash_frame(addr: int) -> bytes:
    buf = bytearray(RF_SEND_SIZE)
    buf[0] = 0x55
    buf[1] = 0xAA
    buf[2] = 0x00
    buf[3] = CMD_RAM2FLASH
    buf[4] = RF_SEND_SIZE & 0xFF
    buf[5] = (RF_SEND_SIZE >> 8) & 0xFF
    buf[6] = addr & 0xFF
    buf[7] = (addr >> 8) & 0xFF
    buf[8] = (addr >> 16) & 0xFF
    buf[9] = (addr >> 24) & 0xFF
    buf[10] = _checksum(buf)
    return bytes(buf)


def _runcode_frame(addr: int) -> bytes:
    buf = bytearray(RC_SEND_SIZE)
    buf[0] = 0x55
    buf[1] = 0xAA
    buf[2] = 0x00
    buf[3] = CMD_RUNCODE
    buf[4] = RC_SEND_SIZE & 0xFF
    buf[5] = (RC_SEND_SIZE >> 8) & 0xFF
    buf[6] = addr & 0xFF
    buf[7] = (addr >> 8) & 0xFF
    buf[8] = (addr >> 16) & 0xFF
    buf[9] = (addr >> 24) & 0xFF
    buf[10] = _checksum(buf)
    return bytes(buf)


# ---------------------------------------------------------------------------
# 烧录
# ---------------------------------------------------------------------------

def _ping(ser) -> bool:
    frame = _ping_frame()
    for _ in range(5):
        for b in frame:
            ser.write(bytes([b]))
            time.sleep(0.001)
        time.sleep(0.005)
        resp = ser.read(PING_RECV_SIZE)
        if len(resp) == PING_RECV_SIZE and resp[:2] == D2H_HEAD and resp[3] == CMD_PING and _check(resp):
            return True
        time.sleep(0.05)
    return False


def _download(ser, code: bytearray, addr: int) -> bool:
    offset = 0
    while offset < len(code):
        chunk = code[offset:offset + BUFFER_SIZE]
        if len(chunk) < BUFFER_SIZE:
            chunk += b"\xFF" * (BUFFER_SIZE - len(chunk))

        for _ in range(5):
            ser.write(_write_buffer_frame(chunk))
            time.sleep(0.005)
            resp = ser.read(DW_RECV_SIZE)
            if len(resp) == DW_RECV_SIZE and resp[:2] == D2H_HEAD and resp[3] == CMD_WRITE_BUFFER:
                break
        else:
            print(f"  写缓冲区失败 @ 0x{addr + offset:08X}")
            return False

        for _ in range(5):
            ser.write(_ram2flash_frame(addr + offset))
            time.sleep(0.1)
            resp = ser.read(RF_RECV_SIZE)
            if len(resp) == RF_RECV_SIZE and resp[:2] == D2H_HEAD and resp[3] == CMD_RAM2FLASH_OK:
                break
        else:
            print(f"  写 Flash 失败 @ 0x{addr + offset:08X}")
            return False

        offset += BUFFER_SIZE
        print(f"  {offset // 1024}/{len(code) // 1024} KB")

    return True


def _runcode(ser, addr: int) -> bool:
    frame = _runcode_frame(addr)
    for _ in range(10):
        for b in frame:
            ser.write(bytes([b]))
            time.sleep(0.001)
        time.sleep(0.05)
        resp = ser.read(RC_RECV_SIZE)
        if len(resp) == RC_RECV_SIZE and resp[:2] == D2H_HEAD and resp[3] == CMD_RUNCODE_OK:
            return True
    return False


def flash(port: str, bin_path: str = None, slot: str = "debug",
          run: bool = True, baudrate: int = BAUDRATE) -> bool:
    if bin_path is None:
        # 始终以 download.py 所在目录为锚点，跟调用方 CWD 无关
        bin_path = str(Path(__file__).resolve().parent / "firmware.bin")

    with open(bin_path, "rb") as f:
        code = bytearray(f.read())

    addr = SLOTS.get(slot, PROGRAM_GCC)

    print(f"烧录 {bin_path} ({len(code) // 1024} KB) → 0x{addr:08X}")

    ser = serial.Serial(port=port, baudrate=baudrate, timeout=0.2,
                        bytesize=8, parity=serial.PARITY_NONE, stopbits=1)

    try:
        # 握手
        ser.write(bytes.fromhex("55 AA 00 01 08 00 00 F7"))
        time.sleep(0.02)
        resp = ser.read(10)

        if resp == bytes.fromhex("66 BB 01 01 0A 00 5A 02 00 76"):
            t0 = time.time()
            while time.time() - t0 < 2:
                ser.reset_input_buffer()
                ser.reset_output_buffer()
                ser.write(bytes.fromhex("55 AA 00 40 0B 00 00 D0 00 08 DD"))
                time.sleep(0.01)
                if ser.read(11) == bytes.fromhex("66 BB 01 41 0B 00 00 D0 00 08 B9"):
                    break
            ser.close()
            ser.open()
            time.sleep(0.3)

        print("ping ...")
        if not _ping(ser):
            print("设备未在 bootloader 模式，请断电重插后重试")
            return False

        print("下载 ...")
        if not _download(ser, code, addr):
            return False

        if run:
            print("运行 ...")
            if not _runcode(ser, addr):
                print("启动失败")
                return False

        print("完成")
        return True
    finally:
        ser.close()


# ---------------------------------------------------------------------------
# __main__
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from serial.tools import list_ports

    ports = [p.device for p in list_ports.comports()]
    if not ports:
        print("未找到串口")
        exit(1)
    for i, p in enumerate(ports):
        print(f"  [{i}] {p}")

    try:
        port = ports[int(input("> ").strip())]
    except (ValueError, IndexError):
        print("无效")
        exit(1)

    while True:
        ok = flash(port)
        if ok:
            break
        input("断电重插后回车重试...")
