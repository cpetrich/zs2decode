#! /usr/bin/env python
# -*- coding: utf-8 -*-
import unittest
import struct
import zs2decode.parser as parser

class Test(unittest.TestCase):
    def test_23_compatibility(self):
        self.assertEqual(parser._chr(0x1234),u'\u1234')
        self.assertEqual(parser._chr(b'\xff'),u'\u00ff')
        self.assertEqual(parser._chr(b'\x40'),u'@')
        self.assertEqual(parser._chr('a'),u'a')
        self.assertEqual(parser._chr(u'a'),u'a')
        self.assertEqual(parser._ord(b'\x03'),3)
        self.assertEqual(parser._ord('\x03'),3)
        self.assertEqual(parser._ord(u'\x03'),3)
        self.assertEqual(parser._ord(b'\x03'[0]),3)
    def test_hex_dump(self):
        self.assertEqual(parser.get_data_stream_hex_dump(b'\x01\x02\x03\x04Hello World!!!',1,1,8),
                         u'000001: 02 03 04 48 65 6c 6c 6f    ···Hello')
    def test_get_byte_str(self):
        self.assertEqual(parser._get_byte_str(b'\x01\x02abcdef',0), (u'\x02',2))
        self.assertEqual(parser._get_byte_str(b'\x01\x02abcdef',1), (u'ab',4))
    def test_skip_past_data_ee(self):
        self.assertEqual(parser._skip_past_data_ee(b'xyz\xee\x04\x00\x01\x00\x00\x00abcdefg', 3),14)
        self.assertEqual(parser._skip_past_data_ee(b'xyz\xee\x00\x00\x00\x00\x00\x00\x00abcdefg', 3),10)
        with self.assertRaises(ValueError):
            self.assertEqual(parser._skip_past_data_ee(b'xyz\xee\x00\x00\x01\x00\x00\x00\x00abcdefg', 3),10)

        with self.assertRaises(TypeError):
            parser._skip_past_data_ee(b'xyz\xee\x04\xff\x01\x00\x00\x00abcdefg', 3)
    def test_skip_past_data_aa(self):
        self.assertEqual(parser._skip_past_data_aa(b'xyz\xaa\x01\x00\x00\x80abcdefg', 3),10)
        self.assertEqual(parser._skip_past_data_aa(b'xyz\xaa\x01\x00\x01\x80abcdefg', 3),10+2*0x10000)
        with self.assertRaises(TypeError):
            parser._skip_past_data_aa(b'xyz\xaa\x01\x00\x00\x7fabcdefg', 3)
    def test_skip_past_data_dd(self):
        self.assertEqual(parser._skip_past_data_dd(b'xyz\xdd\x00abcdefg', 3),5)
        self.assertEqual(parser._skip_past_data_dd(b'xyz\xdd\x02abcdefg', 3),7)
    def test_parse_text_and_numbers(self):
        self.assertEqual(parser._parse_data_11(b'\x11\x03\x00\x00\x00'),(3.,'11'))
        self.assertEqual(parser._parse_data_22(b'"\xd8\x9d\x00\x00'),(40408,'22'))
        self.assertEqual(parser._parse_data_33(b'3\x01\x01\x01\x00'),(65793,'33'))
        self.assertEqual(parser._parse_data_44(b'D\xf1\x14\x00\x00'),(5361,'44'))
        self.assertEqual(parser._parse_data_55(b'U\xff\xff'),(-1,'55'))
        self.assertEqual(parser._parse_data_66(b'f\x01\x00'),(1,'66'))
        self.assertEqual(parser._parse_data_88(b'\x88\x04'),(4,'88'))
        self.assertEqual(parser._parse_data_99(b'\x99\x00'),(False,'99'))
        self.assertEqual(parser._parse_data_aa(b'\xaa\n\x00\x00\x80x\x00c\x00t\x000\x005\x004\x00.\x00z\x00p\x002\x00'),(u'xct054.zp2','AA'))
        self.assertEqual(parser._parse_data_bb(b'\xbbffF@'),(3.1,'BB'))
        self.assertEqual(parser._parse_data_bb(b'\xbb\x01\x00\x80?'),(1.0000001,'BB'))
        self.assertEqual(parser._parse_data_cc(b'\xcc\x9a\x99\x99\x99\x99\x99\xb9?'),(0.1,'CC'))
        self.assertEqual(parser._parse_data_dd(b'\xdd\x00'),('','DD'))
        self.assertEqual(parser._parse_data_dd(b'\xdd\x02Hi'),('Hi','DD'))
        self.assertEqual(parser._parse_data_ee(b'\xee\x01\x02\x03\x04'),(b'\x01\x02\x03\x04','EE'))
    def test_parse_data_ee_subtypes(self):
        # make sure we get a result with good data as expected
        self.assertEqual(parser._parse_data_ee_subtypes(b'\x11\x00\x03\x00\x00\x00\x07\x00\x01'),
            ([7,0,1],u'EE11'))
        self.assertEqual(parser._parse_data_ee_subtypes(b'\x04\x00\x02\x00\x00\x00\xd8\xff@\xc3\xd8\xff@\xc3'),
                         ([-192.99939,-192.99939],u'EE04'))
        self.assertEqual(parser._parse_data_ee_subtypes(b'\x16\x00\x02\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00'),
                         ([1,1],u'EE16'))
        self.assertEqual(parser._parse_data_ee_subtypes(b'\x00\x00\x00\x00\x00\x00'),
                         ([],u'EE00'))
        with self.assertRaises(ValueError):
            # make sure we get an error if there are too few or too many bytes
            self.assertEqual(parser._parse_data_ee_subtypes(b'\x04\x00\x02\x00\x00\x00\xd8\xff@\xc3\xd8\xff@'),
                         ([-192.99939,-192.99939],u'EE04'))
            self.assertEqual(parser._parse_data_ee_subtypes(b'\x05\x00\x02\x00\x00\x00\x1b\xde\x83B\xca\xc0\xf3?\x1b\xde\x83B\xca\xc0\xf3?'),
                         ([1.23456789, 1.23456789],u'EE05'))
            self.assertEqual(parser._parse_data_ee_subtypes(b'\x00\x00\x00\x00\x00\x00X'),
                         ([],u'EE00'))
            self.assertEqual(parser._parse_data_ee_subtypes(b'\x00\x00\x00\x00\x00'),
                         ([],u'EE00'))
            self.assertEqual(parser._parse_data_ee_subtypes(b'\x00\x00\x01\x00\x00\x00'),
                         ([],u'EE00'))
            self.assertEqual(parser._parse_data_ee_subtypes(b'\x00\x00\x01\x00\x00\x00AAAA'),
                         ([],u'EE00'))
    def test_QS(self):
        data = b'\x00\x00\x00\x00\x00' #\x00\x00\x00\x00\x00\x00\x80' #\x02\x00\x00\x00\x80\x00\x00\x00\x80\x02\x00\x00\x00\t'#\x00\x00\x80U\x00T\x00_\x00N\x00o\x00U\x00n\x00i\x00t\x00'
        fmt, decoded = 'IB', [0,0] #u'',0,0,0,0,128] #2, u'', u'', 2, 9] #u'UT_NoUnit']
        result = parser._parse_data_by_format_helper(fmt, bytearray(data), strict_unsigned=False)
        expected = True, fmt, decoded, 5
        self.assertEqual(result, expected)

        result = parser._parse_record(fmt, bytearray(data), strict_unsigned=False)
        expected = True, fmt, decoded, bytearray()
        self.assertEqual(result, expected)

        data=b'\x02\x00\x00\x00\x80\x00\x00\x00\x80\x02\x00\x00\x00\t\x00\x00\x80U\x00T\x00_\x00N\x00o\x00U\x00n\x00i\x00t\x00\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x0c\x00\x00\x00\x05\x00\x00\x80%\x00/\x00m\x00i\x00n\x00\x03\x00\x00\x80%\x00/\x00s\x00\x07\x00\x00\x80%\x00L\x000\x00/\x00m\x00i\x00n\x00\x05\x00\x00\x80%\x00L\x000\x00/\x00s\x00\x05\x00\x00\x801\x00/\x00m\x00i\x00n\x00\x03\x00\x00\x801\x00/\x00s\x00\x08\x00\x00\x80k\x00p\x00s\x00i\x00/\x00m\x00i\x00n\x00\x06\x00\x00\x80k\x00p\x00s\x00i\x00/\x00s\x00\x05\x00\x00\x80M\x00P\x00a\x00/\x00s\x00\x06\x00\x00\x80N\x00/\x00m\x00m\x00\xb2\x00s\x00\x07\x00\x00\x80p\x00s\x00i\x00/\x00m\x00i\x00n\x00\x05\x00\x00\x80p\x00s\x00i\x00/\x00s\x00\xfc\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        decoded=[2, u'', u'', 2, u'UT_NoUnit', 1, 1, 0, 0, 0, 0, [], [u'%/min', u'%/s', u'%L0/min', u'%L0/s', u'1/min', u'1/s', u'kpsi/min', u'kpsi/s', u'MPa/s', u'N/mm\xb2s', u'psi/min', u'psi/s'], 252, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        result = parser._parse_record('B2SLS3BH2B(H)(S)11B', bytearray(data), strict_unsigned=False)
        expected = True, 'B2SLS3BH2B(H)(S)11B', decoded, bytearray()
        self.assertEqual(result, expected)

        result=parser._parse_record_data_ee11_formats_QS('QS_ValSetting',data, False)
        expected = (decoded, 'EE11-B2SLS3BH2B(H)(S)11B')
        self.assertEqual(result, expected)
    def test_get_unicode_string(self):
        self.assertEqual(parser._get_unicode_string(b'\xff\x02\x00\x00\x80H\x00i\x00',1),(u'Hi',9))
        self.assertEqual(parser._get_unicode_string(b'\x02\x00\x00\x80H\x00i\x00',0),(u'Hi',8))
        self.assertEqual(parser._get_unicode_string(b'\x02\x00\x00\x80H\x00i\x00!\x00'),(u'Hi',8))
        self.assertEqual(parser._get_unicode_string(b'\x02\x00\x00\x00H\x00i\x00!\x00',0),(None,0))
        self.assertEqual(parser._get_unicode_string(b'\x02\x00\x00\x00H\x00i\x00!\x00',check_string_marker=False),(u'Hi',8))
    def test_get_data_list(self):
        self.assertEqual(parser._is_bit31_set(b'\x00\x00\x00\x00\x00',1), False)
        self.assertEqual(parser._is_bit31_set(b'\x00\x00\x00\x00\x80',1), True)
    def test_get_data_list(self):
        self.assertEqual(parser._get_data_list(b'\xff\x00\x00\x00\x00Hello',2,1),([],5))
        self.assertEqual(parser._get_data_list(b'\xff\x02\x00\x00\x00ABCD',1,1),([b'A',b'B'],7))
        self.assertEqual(parser._get_data_list(b'\xff\x02\x00\x00\x00\x01\x00\xff\xff',2,1),([b'\x01\x00',b'\xff\xff'],9))
        self.assertEqual(parser._get_data_list(b'\xff\x02\x00\x00\x00\x01\x00\xff',2,1),(None,1))
        self.assertEqual(parser._get_data_list(b'\xff\x02\x00\x00\x00\x00\x00\x00\x80\x01\x00\x00\x80X\x00',-1,1),([b'\x00\x00\x00\x80',b'\x01\x00\x00\x80X\x00'],15))
        self.assertEqual(parser._get_data_list(b'\xff\x01\x00\x00\x00\x00\x00\x00\x80\x01\x00\x00\x80X\x00',-2,1),([b'\x00\x00\x00\x80\x01\x00\x00\x80X\x00'],15))
        self.assertEqual(parser._get_data_list(b'\xff\x00\x00\x00\x00ABCD',1,1),([],5))
        self.assertEqual(parser._get_data_list(b'\xff\x02\x00\x00\x00ABCD',0,1),([b'',b''],5))
    def test_single_as_double(self):
        # make sure that the number that comes out is the same that goes
        #   in single-precision.
        # We don't test whether the decimal representation produced is the shortest or "best".
        # (because there is ambiguity, e.g. 0.104521975 and 0.104521974.)
        for test in (0,9,0.9,-0.1, 1.0000001,3.1,-9.9,5.551115e-17, 0.10452197, 0.104521975, 0.10452198, 0.09406288713216782):
            original = struct.pack('<f',test)
            pseudo_double=struct.unpack('<f',original)[0]
            converted = struct.pack('<f',parser._single_as_double(pseudo_double))
            self.assertEqual(converted,original)

if __name__=='__main__':
    unittest.main()
