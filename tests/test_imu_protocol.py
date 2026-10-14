import pathlib
import struct
import sys
import unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/"scripts"))
import imu_protocol as imu

class ImuProtocolTests(unittest.TestCase):
    def test_document_vectors(self):
        self.assertEqual(imu.hexd(imu.build_packet(200,1)),"FF FF C8 02 01 34")
        self.assertEqual(imu.hexd(imu.build_packet(200,2,[56,15])),"FF FF C8 04 02 38 0F EA")
        self.assertEqual(imu.hexd(imu.build_packet(254,0x82,[56,15,200])),"FF FF FE 05 82 38 0F C8 6B")
    def test_status_and_read(self):
        data=struct.pack("<3h3eBBB",164,0,0,0,0,0,3,0,0)
        payload=bytes([200,len(data)+2,0])+data
        raw=b"\xff\xff"+payload+bytes([imu.checksum(payload)])
        sample=imu.read15(imu.parse_status(raw,expected_length=15))
        self.assertAlmostEqual(sample["gyro_deg_per_sec_vendor"][0],10.0)
        self.assertAlmostEqual(sample["gyro_deg_per_sec_kissqy_scale"][0],2.87)
        self.assertEqual(sample["sequence"],3)
    def test_bad_checksum_fails(self):
        with self.assertRaisesRegex(ValueError,"checksum"):
            imu.parse_status(bytes.fromhex("FF FF C8 02 00 34"))
    def test_bad_status(self):
        with self.assertRaisesRegex(ValueError,"reserved"):
            imu.read15(struct.pack("<3h3eBBB",0,0,0,0,0,0,1,0x10,0))
    def test_bad_quaternion(self):
        with self.assertRaisesRegex(ValueError,"quaternion"):
            imu.read15(struct.pack("<3h3eBBB",0,0,0,1.0,1.0,0,1,0,0))


class ImuSafetyTests(unittest.TestCase):
    def payload(self,seq=1,status=0,q=.125):
        return struct.pack('<3h3eBBB',-164,32767,-32768,q,0,0,seq,status,0)
    def test_profile_units_and_norm(self):
        s=imu.read15(self.payload(), 'vendor-v1.2')
        self.assertAlmostEqual(s['gyro_rad_per_sec'][0],-10*imu.math.pi/180)
        self.assertAlmostEqual(sum(x*x for x in s['quaternion_wxyz']),1)
        self.assertEqual(s['quaternion_wxyz'][1],s['quaternion_xyzw'][0])
    def test_unknown_profile_status_nan_reserved(self):
        for data,profile in [(self.payload(),'auto'),(self.payload(status=2),'vendor-v1.2'),(self.payload(q=float('nan')),'ft6'),(self.payload()[:-1]+b'\x01','ft6')]:
            with self.assertRaises(ValueError):imu.read15(data,profile)
    def test_frame_failures(self):
        for packet in [b'',bytes.fromhex('FF FF C8 01 00 36'),bytes.fromhex('FF FF C7 02 00 36'),bytes.fromhex('FF FF C8 02 01 34'),bytes.fromhex('FF FF C8 02 00 35 00')]:
            with self.assertRaises(ValueError):imu.parse_status(packet)
        with self.assertRaises(ValueError):imu.parse_status(bytes.fromhex('FF FF C8 02 00 35'),expected_length=15)
        with self.assertRaises(ValueError):imu.build_packet(200,2,bytes(254))
    def test_identity(self):
        with self.assertRaises(ValueError):imu.SampleGuard(expected_identity=b'xxxxx')
        with self.assertRaisesRegex(ValueError,'identity'):imu.SampleGuard().accept(self.payload(),b'xxxxx',0)
    def test_status_bits(self):
        for bit in [1,2,4]:
            with self.assertRaisesRegex(ValueError,'freshness'):imu.SampleGuard().accept(self.payload(status=bit),imu.FT6_IDENTITY,0)
        self.assertTrue(imu.SampleGuard().accept(self.payload(status=8),imu.FT6_IDENTITY,0)['status_ready'])
    def test_freshness_and_wrap(self):
        g=imu.SampleGuard()
        for n in range(25):s=g.accept(self.payload((250+n)%256),imu.FT6_IDENTITY,n*20,20000)
        self.assertTrue(s['orientation_ready'])
        for n in range(2):g.accept(self.payload(18),imu.FT6_IDENTITY,500+n*20)
        with self.assertRaises(ValueError):g.accept(self.payload(18),imu.FT6_IDENTITY,540)
        with self.assertRaises(ValueError):g.accept(self.payload(19),imu.FT6_IDENTITY,600)
        with self.assertRaises(ValueError):imu.SampleGuard().accept(self.payload(),imu.FT6_IDENTITY,0,20001)
        with self.assertRaises(ValueError):imu.SampleGuard().accept(self.payload(q=0),imu.FT6_IDENTITY,0)
    def test_vendor_counter_is_not_age_proof(self):
        g=imu.SampleGuard('vendor-v1.2')
        with self.assertRaisesRegex(ValueError,'unproven'):g.accept(self.payload(),imu.FT6_IDENTITY,0)
        s=g.accept(self.payload(2),imu.FT6_IDENTITY,20,verified_vendor_age_ms=10)
        self.assertFalse(s['orientation_ready'])

class StreamTests(unittest.TestCase):
    def test_split_corrupt_resync_coalesced(self):
        data=struct.pack('<3h3eBBB',-164,0,0,.125,0,0,1,0,0)
        frame=imu.build_packet(200,0,data)
        for split in range(len(frame)+1):
            p=imu.StatusStream()
            self.assertEqual(p.feed(frame[:split])+p.feed(frame[split:]),[data])
        p=imu.StatusStream();bad=frame[:-1]+bytes([frame[-1]^1])
        self.assertEqual(p.feed(b'junk'+bad+frame+frame),[data,data]);self.assertGreater(p.rejected,0)
    def test_identity_fault_resets_readiness(self):
        g=imu.SampleGuard()
        for n in range(25):g.accept(struct.pack('<3h3eBBB',0,0,0,.125,0,0,n,0,0),imu.FT6_IDENTITY,n*20)
        with self.assertRaises(ValueError):g.accept(bytes(15),b'xxxxx',500)
        self.assertEqual(g.live_samples,0)

if __name__ == "__main__":
    unittest.main()
