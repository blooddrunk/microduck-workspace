#!/usr/bin/env python3
"""Offline-only Feetech ID200 IMU contract parser; NO serial or hardware I/O."""
import argparse
import math
import struct

FT6_IDENTITY=bytes.fromhex("06 00 00 00 F2")
PROFILES={"ft6": 0.0175, "vendor-v1.2": 1/16.4}
ID=200
SYNC_ADDRESS=56
SYNC_LENGTH=15

def checksum(payload):
    return (~sum(payload)) & 0xff

def build_packet(device_id, instruction, params=b""):
    if not (0<=device_id<=254):
        raise ValueError("invalid device id")
    if len(params)>253 or not 0<=instruction<=255:
        raise ValueError("invalid instruction or parameter length")
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

class StatusStream:
    """Fragment/coalescence parser for saved READ replies; no serial access."""
    def __init__(self, expected_id=ID, expected_length=15):
        self.buffer=bytearray()
        self.expected_id=expected_id
        self.expected_length=expected_length
        self.rejected=0

    def feed(self, chunk):
        self.buffer.extend(chunk)
        out=[]
        while len(self.buffer)>=2:
            start=self.buffer.find(b"\xff\xff")
            if start<0:
                self.buffer[:]=self.buffer[-1:] if self.buffer[-1]==255 else b""
                break
            del self.buffer[:start]
            if len(self.buffer)<4: break
            if self.buffer[2]!=self.expected_id or self.buffer[3]!=self.expected_length+2:
                self.rejected+=1;del self.buffer[0];continue
            size=self.buffer[3]+4
            if len(self.buffer)<size: break
            try:
                data=parse_status(bytes(self.buffer[:size]),self.expected_id,self.expected_length)
            except ValueError:
                self.rejected+=1;del self.buffer[0];continue
            out.append(data);del self.buffer[:size]
        return out

def read15(data, profile="ft6"):
    if profile not in PROFILES: raise ValueError("unknown IMU profile")
    if len(data)!=15: raise ValueError("IMU sample must be 15 bytes")
    gyro=struct.unpack_from("<3h",data,0)
    qxyz=struct.unpack_from("<3e",data,6)
    seq,status,reserved=data[12:15]
    if reserved!=0 or status & (0xf0 if profile=="ft6" else 0xfe):
        raise ValueError("reserved or undocumented status bits")
    if any(not math.isfinite(v) for v in qxyz):
        raise ValueError("nonfinite quaternion")
    square=sum(v*v for v in qxyz)
    if square>1.02: raise ValueError("invalid quaternion")
    qw=math.sqrt(max(0.0,1-square))
    norm=math.sqrt(square+qw*qw)
    quat=[v/norm for v in (*qxyz,qw)]
    return {"gyro_raw":gyro,"gyro_deg_per_sec_vendor":[round(v/16.4,6) for v in gyro],
        "gyro_deg_per_sec_kissqy_scale":[round(v*.0175,6) for v in gyro],
        "profile":profile,"gyro_rad_per_sec":[v*PROFILES[profile]*math.pi/180 for v in gyro],
        "quaternion_xyzw":quat,"quaternion_wxyz":[quat[3],*quat[:3]],
        "quaternion_live":any(data[6:12]),"status_ready":not bool(status & (7 if profile=="ft6" else 1)),
        "age_upper_bound_ms":30 if profile=="ft6" and status&7==0 else None,"sequence":seq,"status":status,
        "ready_bit0":not bool(status&1),"stale_bit1":bool(status&2),
        "reader_slow_bit3":bool(status&8)}


class SampleGuard:
    """Offline guard. Vendor freshness requires an independently verified age bound.

    No signature fallback, no implied vendor freshness from a changing counter.
    """
    def __init__(self, profile="ft6", expected_identity=FT6_IDENTITY):
        if profile not in PROFILES or not isinstance(expected_identity, bytes) or len(expected_identity)!=5:
            raise ValueError("profile and pinned five-byte identity required")
        if profile=="ft6" and expected_identity!=FT6_IDENTITY:
            raise ValueError("FT6 identity is fixed")
        self.profile=profile
        self.identity=expected_identity
        self.last_seq=None
        self.repeated=0
        self.last_time=None
        self.live_samples=0

    def accept(self, *args, **kwargs):
        try:
            return self._accept(*args, **kwargs)
        except (ValueError, TypeError, OverflowError):
            self.live_samples=0
            raise

    def _accept(self, data, identity, time_ms, transaction_us=0, verified_vendor_age_ms=None):
        if identity!=self.identity: raise ValueError("identity mismatch")
        if not math.isfinite(time_ms) or (self.last_time is not None and time_ms<=self.last_time):
            raise ValueError("timestamps must increase")
        if not isinstance(transaction_us, int) or isinstance(transaction_us, bool) or transaction_us<0:
            raise ValueError("invalid transaction duration")
        sample=read15(data,self.profile)
        gap=self.last_time is not None and time_ms-self.last_time>50
        self.last_time=time_ms
        self.repeated=self.repeated+1 if sample["sequence"]==self.last_seq else 0
        self.last_seq=sample["sequence"]
        age=sample["age_upper_bound_ms"]
        if self.profile=="vendor-v1.2":
            age=verified_vendor_age_ms
            if age is not None and (isinstance(age,bool) or not math.isfinite(age) or age<0):
                raise ValueError("invalid verified age")
        if gap or age is None or age*1000+transaction_us>50000 or self.repeated>=3 or not sample["status_ready"] or not sample["quaternion_live"]:
            self.live_samples=0
            raise ValueError("IMU not ready or freshness unproven/stale")
        self.live_samples+=1
        sample["orientation_ready"]=self.live_samples>=25
        return sample

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
