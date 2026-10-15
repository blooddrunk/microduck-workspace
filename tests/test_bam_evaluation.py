import math
import unittest

from scripts.evaluate_bam import MODEL_FIELDS, validate_payload


def valid_m1():
    return {
        "kt": 0.5816025731865149,
        "R": 4.330539590324882,
        "armature": 0.0018977343913586006,
        "q_offset": 0.014707540074810413,
        "command_delay": 0.0016779766143564852,
        "friction_base": 0.015408138028970004,
        "friction_viscous": 0.005726261275213136,
        "model": "m1",
        "actuator": "hd1910",
    }


class BamPayloadTests(unittest.TestCase):
    def test_valid_m1_payload(self):
        validate_payload(valid_m1(), "m1")

    def test_all_six_model_schemas(self):
        for variant, optional_fields in MODEL_FIELDS.items():
            with self.subTest(variant=variant):
                payload = {**valid_m1(), "model": variant}
                for name in optional_fields:
                    payload[name] = 0.5 if name not in {"dtheta_stribeck", "alpha"} else 1.0
                validate_payload(payload, variant)

    def test_non_finite_values_fail(self):
        for value in (math.nan, math.inf, -math.inf):
            with self.subTest(value=value):
                payload = valid_m1()
                payload["kt"] = value
                with self.assertRaisesRegex(ValueError, "finite"):
                    validate_payload(payload, "m1")

    def test_boolean_and_string_parameters_fail(self):
        for value in (True, "0.5"):
            with self.subTest(value=value):
                payload = valid_m1()
                payload["kt"] = value
                with self.assertRaisesRegex(ValueError, "JSON number"):
                    validate_payload(payload, "m1")

    def test_invalid_physical_ranges_fail(self):
        for key, value in (("kt", 0.0), ("R", -1.0), ("armature", 0.0),
                           ("command_delay", -0.001), ("q_offset", 0.101),
                           ("friction_base", -0.01)):
            with self.subTest(key=key):
                payload = valid_m1()
                payload[key] = value
                with self.assertRaises(ValueError):
                    validate_payload(payload, "m1")
        payload = valid_m1()
        payload["command_delay"] = 0.051
        with self.assertRaisesRegex(ValueError, "command_delay"):
            validate_payload(payload, "m1")

    def test_wrong_model_actuator_and_fields_fail(self):
        payload = valid_m1()
        payload["model"] = "m2"
        with self.assertRaisesRegex(ValueError, "model field"):
            validate_payload(payload, "m1")
        payload = valid_m1()
        payload["actuator"] = "HD1910"
        with self.assertRaisesRegex(ValueError, "lowercase"):
            validate_payload(payload, "m1")
        payload = valid_m1()
        payload["surprise"] = 1.0
        with self.assertRaisesRegex(ValueError, "field mismatch"):
            validate_payload(payload, "m1")
        payload = valid_m1()
        del payload["R"]
        with self.assertRaisesRegex(ValueError, "field mismatch"):
            validate_payload(payload, "m1")

    def test_stribeck_fields_must_be_positive(self):
        payload = {
            **valid_m1(),
            "model": "m2",
            "friction_stribeck": 0.01,
            "dtheta_stribeck": 0.0,
            "alpha": 2.0,
        }
        with self.assertRaisesRegex(ValueError, "dtheta_stribeck"):
            validate_payload(payload, "m2")


if __name__ == "__main__":
    unittest.main()
