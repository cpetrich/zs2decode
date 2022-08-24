import json as _json
import io as _io
import hashlib as _hashlib
import sys as _sys
import struct as _struct
import gzip as _gzip
import xml.dom.minidom as _xml_minidom

import zs2decode.parser as _parser
import zs2decode.util as _util

# Author: Chris Petrich
# Copyright 2017-2022, Chris Petrich
# License: MIT

######################################
#
#    Python 2/3 compatibility
#

def _join(head, tail):
    if _sys.version_info.major < 3:
        return sum(tail, head)
    else:
        return head+b''.join(tail)
    
def save_zs2(filename, raw_data_stream):
    if _sys.version_info.major < 3:
        result = _write_TE2(filename, str(raw_data_stream))
    else:
        result = _write_TE2(filename, raw_data_stream)
    return result

######################################
#
#     Helper function for zs2 output
#

def _write_TE2(filename, data):
    """Write data compressed similarly to TestExpert II. There
       may still be small implementation differences between the encoders."""
    with _io.BytesIO() as fp:
        with _gzip.GzipFile(fileobj = fp, filename='', mode='wb', compresslevel=6, mtime=0) as f:
            f.write(data)
            f.flush()
        buffer = bytearray(fp.getvalue())
    buffer[8] = 0x00 # XFL as set in TestExpert II files (afaik)
    buffer[9] = 0x0b # OS (NTFS)

    if filename is not None:
        with open(filename, 'wb') as fp:
            fp.write(buffer)

    return buffer    
    
#########################################
#
#       Encoding functions
#

def make_chunk_list(root):
    """Generate list of chunks identical to the list passed to the dump function"""
    # generate interpreted chunk list
    # add attributes to list    
    if 'name' in root.attributes.keys():
        chunk_name = root.attributes['name'].value
    else:
        chunk_name = root.nodeName
    data_type = root.attributes['type'].value
    data_value_str = root.attributes['value'].value
    if data_type.upper() in ('AA','00','DD'):
        data_value = _json.loads('"%s"' % data_value_str)        
    else:        
        data_value = _json.loads(data_value_str)        
                
    # note that originally, the last element is supposed to be 
    chunks = [[None, chunk_name, data_type, data_value]]

    # there may be empty DD sections which would not have an explicit closing element in XML
    has_child = False or (data_type.upper() == 'DD' and not len(root.childNodes))
    for node in root.childNodes:
        # do not consider node values (i.e. the text between tags)
        if node.nodeType == node.ELEMENT_NODE:
            has_child = True
            chunks += make_chunk_list(node)
    if has_child:
        chunks.append([None, '', 'end', []])
        
    return chunks

def make_raw_chunks(chunks, address = 4):
    raw_chunks = []
    for _, name, type, value in chunks:
        if name == '' and type == 'end':
            raw_chunks.append([address, None, value])
            address += 1
        else:
            data = _encode_data(type, value)
            raw_chunks.append([address, name, data])
            address += len(name)+1 + len(data)
    return raw_chunks

def make_datastream(raw_chunks):
    header = bytearray(b'\xaf\xbe\xad\xde')    
    # doing the following in a list comprehension is incredibly slow in Python 2
    stream = header
    for _, name, data in raw_chunks:
        stream += _make_ASCII_string(name)+data if name is not None else bytearray(b'\xff')
    return stream

#########################################
#
#       Helper functions for encoding
#

def _make_ASCII_string(value):
    payload = bytearray(value, encoding='ASCII')
    return bytearray((len(payload),))+ payload

def _make_Unicode_string(value):
    try:
        payload = bytearray(value, encoding='UTF-16LE')
    except TypeError:
        print(repr(value))
        raise
    length = len(value)+ 0x80000000
    return bytearray(_pack1('L',length)) + payload

_ord= lambda x: x if isinstance(x,int) else ord(x)

def _encode_EE11_format_helper(fmt, values, debug=False):
    fmt_idx, values_idx = 0, 0
    data = bytearray()
    while fmt_idx < len(fmt):
        char = fmt[fmt_idx]
        if char == '(': # process list
            close_idx, depth = fmt_idx + 1, 0
            while fmt[close_idx] != ')' or depth > 0:
                if fmt[close_idx] == ')': depth -= 1
                elif fmt[close_idx] == '(': depth += 1
                close_idx += 1

            sub_fmt = fmt[fmt_idx+1:close_idx]
            #print('sub_fmt',sub_fmt,'to run',len(values[values_idx]),'times')

            data += _pack1('L',len(values[values_idx]))
            
            for list_element_tuple in values[values_idx]:
                if not isinstance(list_element_tuple,(list,tuple)):                    
                    list_element_tuple = [list_element_tuple]
                sub_data, sub_remainder = _encode_EE11_format_helper(sub_fmt, list_element_tuple, debug=False)                
                if len(sub_remainder):
                    raise ValueError('Unsuccessful decode of (%s) for %r' % (sub_fmt, values[values_idx]))
                data += sub_data
                        
            values_idx += 1
            fmt_idx = close_idx + 1
        elif char == 'S': # string
            try:
                data += _make_Unicode_string(values[values_idx])
            except TypeError:
                print('Failed unicode of %r' % values[values_idx])
                raise
            values_idx += 1
            fmt_idx += 1
        else: # oridinary number
            value = values[values_idx]
            if value == -1 and char == char.upper():
                # the largest number in an unsigned value may be
                #   stored as -1
                char = char.lower()
            data += _pack1(char, value)
            values_idx += 1
            fmt_idx += 1
    return data, values[values_idx:]

def _encode_EE11_format(fmt, values, debug=False):
    fmt_exp = _parser.expand_format(fmt)
    if fmt_exp.startswith('(') and not isinstance(values[0],(list,tuple)):
        # this is incompatible with parser output and a sign of hand-editing
        raise ValueError('Cannot parse list from non-list first datum: %r %r' % (fmt, values))
        
    data, remainder = _encode_EE11_format_helper(fmt_exp, values, debug)
    
    return data, remainder
    
def _encode_EE11(type, value):
    """Return list of bytes where byte content is interpreted according to format string in 'type'"""
    # catch and explicitly reject pre-0.3.0 format
    if type.count('-') > 1: raise ValueError('Syntax error in type code %r' % type)
    if type == 'EE11' and len(value) != 0: raise ValueError('Type %r without format string cannot encode data %r' % (type, data))
    
    fmt = type.rsplit('-',1)[-1] if '-' in type else ''
    data, values_remaining = _encode_EE11_format(fmt, value)

    if len(values_remaining):
        raise ValueError('unprocessed values %r in %r %r' % (
                values_remaining, type, value))
    
    length = _pack1('L',len(data))
    return length+data

def _encode_EE(type, value):
    length = _pack1('L',len(value))
    if type == 'EE04':
        payload = _join(length,[_pack1('f',v) for v in value])
    elif type == 'EE05':
        payload = _join(length,[_pack1('d',v) for v in value])
    elif type == 'EE00':
        if len(value): raise ValueError('Expected list of length 0 in %r %r' % (type, value))
        payload = length
    elif type == 'EE16':
        payload = _join(length,[_pack1('L',v) for v in value])
    elif type.startswith('EE11'):
        payload = _encode_EE11(type, value)
    else:
        raise NotImplementedError('Cannot decode type %r' % type)
    return bytearray.fromhex(type[2:4])+b'\x00'+payload

_pack1 = lambda f,v: bytearray(_struct.pack('<'+_parser._fmt_map[f],v))
    
def _encode_data(type, value):
    chunk_type = bytearray.fromhex(type[:2])
    if type == '00': payload = _make_Unicode_string(value)
    elif type == '11': payload = _pack1('l',value)
    elif type == '22': payload = _pack1('L',value)
    elif type == '33': payload = _pack1('l',value)
    elif type == '44': payload = _pack1('L',value)
    elif type == '55': payload = _pack1('h',value)
    elif type == '66': payload = _pack1('H',value)
    elif type == '88': payload = _pack1('B',value)
    elif type == '99': payload = _pack1('B',value)
    elif type == 'AA': payload = _make_Unicode_string(value)
    elif type == 'BB': payload = _pack1('f',value)
    elif type == 'CC': payload = _pack1('d',value)        
    elif type == 'DD': payload = _make_ASCII_string(value)
    elif type.startswith('EE'): payload = _encode_EE(type, value)
    else:
        raise ValueError('Cannot encode type %r' % type)
    
    return chunk_type + payload


#########################################
#
#   Conversion test
#

def fingerprint(unpacked_data_stream):    
    return _hashlib.sha224(unpacked_data_stream).hexdigest()    

def test_process_cycle(zs2_file_name, verbose=True):
    """This is a test to check if util output changed
       in an incompatible manner. A zs2 file is read, converted to XML,
       and back-converted to a raw datastream."""
    if verbose:
        print('Decoding %s...' % zs2_file_name)
    data_stream = _parser.load(zs2_file_name)
    input_fingerprint = fingerprint(data_stream)
    if verbose:
        print('    Data fingerprint %s' % input_fingerprint)
    xml_data = data_stream_to_xml(data_stream)
    if verbose:
        print('    Length of XML: %.0f kB' % (len(xml_data)/1024.))

    if verbose:
        print('Encoding XML to zs2...')
    enc_data_stream = xml_to_data_stream(xml_data)
    output_fingerprint = fingerprint(enc_data_stream)
    if verbose:
        print('    Data fingerprint: %s' % output_fingerprint)

    if input_fingerprint != output_fingerprint:
        raise ValueError('Decode/Encode cycle of %s is unsuccessful.' % zs2_file_name)
    return input_fingerprint == output_fingerprint

######################################################################
#
#    General conversion operations
#

def xml_to_data_stream(xml_data):
    """xml_data is a bytearray with encoding information in the prolog."""
    with _io.BytesIO(xml_data) as f:
        dom = _xml_minidom.parse(f)
    chunks = make_chunk_list(dom.documentElement)
    raw_chunks = make_raw_chunks(chunks)
    data_stream = make_datastream(raw_chunks)
    return data_stream

def data_stream_to_xml(data_stream):
    """Return a bytearray ready to written to disk."""
    raw_chunks = _parser.data_stream_to_chunks(data_stream)
    chunks = _parser.parse_chunks(raw_chunks)
    xml_data = _util.chunks_to_XML(chunks)
    return xml_data
    
def xml_to_zs2(filename_in, filename_out=-1, verbose=False):
    """Set filename_out to None to suppress output to disk"""
    if filename_out == -1:
        filename_out = filename_in.rsplit('.',1)[0]+'_encoded.zs2'

    if verbose:
        print('Encoding %s' % filename_in)

    with open(filename_in,'rb') as f:
        xml_data = bytearray(f.read())        
    data_stream = xml_to_data_stream(xml_data)
    
    if verbose:        
        print('  Data fingerprint: %s' % fingerprint(data_stream))
    file_data = save_zs2(filename_out, data_stream)    
    return file_data

def zs2_to_xml(filename_in, filename_out=-1, verbose=False):
    """Set filename_out to None to suppress output to disk"""
    if filename_out == -1:
        filename_out = filename_in.rsplit('.',1)[0]+'.xml'
        
    if verbose:
        print('Decoding %s' % filename_in)

    data_stream = _parser.load(filename_in)
    
    if verbose:
        print('  Data fingerprint: %s' % fingerprint(data_stream))

    xml_data = data_stream_to_xml(data_stream)    
    if filename_out is not None:
        with open(filename_out, 'wb') as f:
            f.write( xml_data )
    return xml_data


if __name__ == '__main__':    
    path = './'
    if True:        
        # test the decode / encode cycle on all zs2 files
        print('Testing decode/encode cycle\n')
        import glob
        for fn_zs2 in glob.glob('/'.join([path,'*.zs2'])):
            test_process_cycle(fn_zs2)
    if True:
        # convert a few files and write to disk
        print('Testing conversion and output to disk\n')
        import glob
        fn_zs2 = glob.glob('/'.join([path,'*.zs2']))[0]
        zs2_to_xml(fn_zs2,'_test.xml',verbose=True)
        
        fn_xml = glob.glob('/'.join([path,'*.xml']))[0]
        xml_to_zs2(fn_xml,'_test.zs2',verbose=True)
