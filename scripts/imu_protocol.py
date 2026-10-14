#!/usr/bin/env python3
"""Offline-only Feetech ID200 IMU contract parser; NO serial or hardware I/O."""
import argparse
import math
import struct

ID=200
SYNC_ADDRESS=56
SYNC_LENGTH=15

def checksum(payload):
    return (~sum(payload)) & 0xff

def build_packet(device_id, instruction, params=b""):
    if not (0<=device_id<=254):
        raise ValueError("invalid device id")
    body=bytes([device_id,len(params)+2,instruction])+bytes(params)
    return b"\xff\xff"+body+bytes([checksum(body)])

def parse_status(packet,expected_id=ID,expected_length=None):
    if len(packet)<6 or packet[:2]!=b"\xff\xff":
        raise ValueError("bad status header or length")
    length=packet[3]
    if len(packet)!=length+4 or length<2:
        raise ValueError("bad packet length")
    if packet[2]!=expected_id:
        raise ValueError("unexpected id")
    if checksum(packet[2:-1])!=packet[-1]:
        raise ValueError("bad checksum")
    if packet[4]!=0:
        raise ValueError(f"status error 0x{packet[4]:02x}")
    data=packet[5:-1]
    if expected_length is not None and len(data)!=expected_length:
        raise ValueError("unexpected payload length")
    return data

def read15(data):
    if len(data)!=15: raise ValueError("IMU sample must be 15 bytes")
    gyro=struct.unpack_from("<3h",data,0)
    qxyz=struct.unpack_from("<3e",data,6)
    seq,status,reserved=data[12:15]
    if reserved!=0 or status&0xf0:
        raise ValueError("reserved bits do not match FT6")
    if any(not math.isfinite(v) for v in qxyz):
        raise ValueError("nonfinite quaternion")
    square=sum(v*v for v in qxyz)
    if square>1.04: raise ValueError("invalid quaternion")
    qw=math.sqrt(max(0.0,1-square))
    return {"gyro_raw":gyro,"gyro_deg_per_sec_vendor":[round(v/16.4,6) for v in gyro],
        "gyro_deg_per_sec_kissqy_scale":[round(v*.0175,6) for v in gyro],
        "quaternion_xyzw":[*qxyz,qw],"sequence":seq,"status":status,
        "ready_bit0":not bool(status&1),"stale_bit1":bool(status&2),
        "reader_slow_bit3":bool(status&8)}

def hexd(data): return " ".join(f"{v:02X}" for v in data)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--requests",action="store_true")
    p.add_argument("--demo",action="store_true")
    a=p.parse_args()
    if a.requests or not a.demo:
        for name,blob in [
            ("PING",build_packet(ID,1)),
            ("READ 56/15",build_packet(ID,2,[SYNC_ADDRESS,SYNC_LENGTH])),
            ("SYNC_READ 56/15 ID200",build_packet(254,0x82,[SYNC_ADDRESS,SYNC_LENGTH,ID]))]:
            print(f"{name}: {hexd(blob)}")
    if a.demo:
        q=struct.pack("<3h3eBBB",164,0,0,0.0,0.0,0.0,7,0,0)
        answer=b"\xff\xff"+bytes([ID,len(q)+2,0])+q
        answer+=bytes([checksum(answer[2:])])
        print("SYNTHETIC RX:",hexd(answer))
        print("SYNTHETIC DECODE:",read15(parse_status(answer,expected_length=15)))
        print("NOT HARDWARE DATA; FT6 IDENTITY AND GYRO SCALING ARE STILL UNVERIFIED")

if __name__=="__main__": main()
