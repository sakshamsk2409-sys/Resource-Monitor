"""Unit tests for HardwareMonitor and LibreHardwareMonitor integration."""

import unittest
from hardware_monitor import HardwareMonitorService, get_hardware_monitor
from telemetry_logger import TelemetrySampler, TelemetryLogger


class TestHardwareMonitor(unittest.TestCase):
    """Test suite for HardwareMonitorService and LHM telemetry extraction."""

    def setUp(self):
        self.monitor = get_hardware_monitor()

    def test_singleton_instance(self):
        mon2 = get_hardware_monitor()
        self.assertIs(self.monitor, mon2)

    def test_get_cpu_load_range(self):
        load = self.monitor.get_cpu_load()
        self.assertIsInstance(load, (int, float))
        self.assertGreaterEqual(load, 0.0)
        self.assertLessEqual(load, 100.0)

    def test_get_cpu_temperature_type_or_none(self):
        temp = self.monitor.get_cpu_temperature()
        if temp is not None:
            self.assertIsInstance(temp, (int, float))
            self.assertGreater(temp, 0.0)
            self.assertLess(temp, 150.0)

    def test_json_tree_parsing(self):
        sample_lhm_tree = {
            "id": 0,
            "Text": "Sensor",
            "Children": [
                {
                    "id": 1,
                    "Text": "DESKTOP-TEST",
                    "Children": [
                        {
                            "id": 2,
                            "Text": "Intel Core i7-11850H",
                            "ImageURL": "images_icon/cpu.png",
                            "Children": [
                                {
                                    "id": 3,
                                    "Text": "Load",
                                    "Children": [
                                        {
                                            "id": 4,
                                            "Text": "CPU Total",
                                            "Value": "33.7 %",
                                            "RawValue": "33.7",
                                            "SensorId": "/intelcpu/0/load/0",
                                            "Type": "Load"
                                        }
                                    ]
                                },
                                {
                                    "id": 5,
                                    "Text": "Temperatures",
                                    "Children": [
                                        {
                                            "id": 6,
                                            "Text": "CPU Package",
                                            "Value": "54.0 °C",
                                            "RawValue": "54.0",
                                            "SensorId": "/intelcpu/0/temperature/10",
                                            "Type": "Temperature"
                                        }
                                    ]
                                }
                            ]
                        }
                    ]
                }
            ]
        }

        # Mock the cached tree
        orig_cached = self.monitor._lhm_tree_cached
        orig_cached_at = self.monitor._lhm_tree_cached_at
        try:
            self.monitor._lhm_tree_cached = sample_lhm_tree
            self.monitor._lhm_tree_cached_at = 9999999999.0

            web_load, web_temp = self.monitor.get_lhm_web_cpu()
            self.assertEqual(web_load, 33.7)
            self.assertEqual(web_temp, 54.0)
        finally:
            self.monitor._lhm_tree_cached = orig_cached
            self.monitor._lhm_tree_cached_at = orig_cached_at

    def test_sampler_with_cpu_provider(self):
        sampler = TelemetrySampler(cpu_provider=lambda: 42.5)
        rec = sampler.sample()
        self.assertEqual(rec["cpu_usage_percent"], 42.5)


if __name__ == "__main__":
    unittest.main()

