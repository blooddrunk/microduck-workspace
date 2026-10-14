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
if __name__=="__main__": unittest.main()
