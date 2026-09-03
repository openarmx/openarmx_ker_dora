import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from openarmx_ker_dora.ker_stream import CMD_PING, KERStream


class TestKerStream(unittest.TestCase):
    def test_usb_composite_device_claims_only_vendor_interface(self):
        import usb.core
        import usb.util

        class Interface(list):
            def __init__(self, number, interface_class, endpoints):
                super().__init__(endpoints)
                self.bInterfaceNumber = number
                self.bInterfaceClass = interface_class

        endpoint_out = SimpleNamespace(bEndpointAddress=0x01)
        endpoint_in = SimpleNamespace(bEndpointAddress=0x81)
        configuration = [
            Interface(0, 0xFF, [endpoint_out, endpoint_in]),
            Interface(1, 0x02, []),
            Interface(2, 0x0A, []),
        ]
        device = MagicMock()
        device.get_active_configuration.return_value = configuration
        device.is_kernel_driver_active.return_value = False

        stream = KERStream(transport='usb')
        with (
            patch.object(usb.core, 'find', return_value=device),
            patch.object(usb.util, 'claim_interface') as claim_interface,
            patch.object(usb.util, 'release_interface') as release_interface,
            patch.object(usb.util, 'dispose_resources'),
        ):
            stream._connect_usb()
            device.set_configuration.assert_not_called()
            claim_interface.assert_called_once_with(device, 0)
            device.write.assert_called_once_with(0x01, b'\x01')

            stream.close()
            release_interface.assert_called_once_with(device, 0)

    def test_wifi_command_frame_pads_payload_and_adds_checksum(self):
        self.assertEqual(
            KERStream.encode_wifi_command(CMD_PING),
            bytes([0xA5, 0x43, 0x00, 0x00, 0x00, 0x00]),
        )

    def test_wifi_command_frame_preserves_zero_mask_arguments(self):
        self.assertEqual(
            KERStream.encode_wifi_command(bytes([0x04, 0x12, 0x34])),
            bytes([0xA5, 0x43, 0x04, 0x12, 0x34, 0x22]),
        )

    def test_wifi_command_rejects_invalid_payload_length(self):
        for payload in (b'', b'\x00\x01\x02\x03'):
            with self.subTest(payload=payload):
                with self.assertRaises(ValueError):
                    KERStream.encode_wifi_command(payload)

    def test_endpoint_descriptions(self):
        self.assertEqual(
            KERStream(transport='usb').endpoint,
            'USB 0x303a:0x4002',
        )
        self.assertEqual(
            KERStream(transport='serial', port='/dev/ttyUSB1', baud=115200).endpoint,
            '/dev/ttyUSB1 @ 115200',
        )
        self.assertEqual(
            KERStream(transport='wifi', wifi_host='192.168.10.20', wifi_port=19090).endpoint,
            '192.168.10.20:19090',
        )


if __name__ == '__main__':
    unittest.main()
