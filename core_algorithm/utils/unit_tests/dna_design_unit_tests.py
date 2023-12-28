import unittest
from core_algorithm.utils.dna_design import *


# Test Dataclasses
class TestDataClasses(unittest.TestCase):
    pass


# Test Auxiliary Functions
class AuxFuncsTests(unittest.TestCase):
    def hex_to_rgb_test(self, first, second):
        with self.subTest():
            self.assertEqual(first, second)


class RunAuxFuncsTest(AuxFuncsTests):
    def test_hex_to_rgb(self):
        self.hex_to_rgb_test(hex_to_rgb('000000'), '0.0;0.0;0.0')     # rgb: 0;0;0
        self.hex_to_rgb_test(hex_to_rgb('FFFFFF'), '1.0;1.0;1.0')     # rgb: 255;255;255
        self.hex_to_rgb_test(hex_to_rgb('3badb8'), '0.23;0.68;0.72')  # rgb: 59;173;184
        with self.assertWarns(Warning):
            self.hex_to_rgb_test(hex_to_rgb(''), '0.0;0.0;0.0')
        with self.assertWarns(Warning):
            self.hex_to_rgb_test(hex_to_rgb('blah'), '0.0;0.0;0.0')
        with self.assertWarns(Warning):
            self.hex_to_rgb_test(hex_to_rgb(123456), '0.0;0.0;0.0')


# Test DNADesign Methods
class TestDNADesignMethods(unittest.TestCase):
    pass


if __name__ == '__main__':
    unittest.main()
