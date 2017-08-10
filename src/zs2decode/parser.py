"""Module to import and decode zs2 files."""

import gzip as _gzip
import struct as _struct

# Author: Chris Petrich
# Copyright: Copyright 2015,2016,2017, Chris Petrich
# License: MIT

#####################################
#
#       Python 2/3 compatibility
#

# turn byte/str/int/unicode character into ordinal value
_ord= lambda x: x if isinstance(x,int) else ord(x)
# turn byte/str/int/unicode into unicode character(s)
_chr= lambda x: u'%c'%x if isinstance(x,int) else u'%c'%_ord(x)
_to_string= lambda data: u''.join([_chr(elem) for elem in data])

######## convenience function
_unpack1= lambda fmt, data: _struct.unpack('<'+fmt,data)[0]

#####################################
#
#       File functions
#

def load(filename, debug=False):
    """Open file and return data stream"""
    # returns Bytes in Py3 and Str in Py2
    # note that in Py3 type(data[0])==int while type(data[:1])==bytes
    # while in Py2 type(data[0])==str, and type(data[:1])==str
    with _gzip.open(filename, 'rb') as f:
        data_stream = bytearray( f.read() )        
    if len(data_stream)<4:
        raise ValueError('Data stream is too short.')        
    if not debug and not _has_file_marker(data_stream):
        raise ValueError('File marker is missing. Found 0x%X, expected 0xDEADBEAF.' % _unpack1('L',data_stream[:4]))
    if not debug and _has_extended_header(data_stream):
        raise ValueError('File has unexpected, extended binary header. Try processing file in debug mode.')
    return data_stream

#####################################
#
#       Data stream functions
#

def data_stream_to_chunks(data_stream, start=0, debug=False):
    """Get all elements and associated data without decoding data beyond length information.
       Parameter "start" is the beginning of the file marker."""
    # we need to find the beginning of the file.    
    #  (We expect 'start' to be at index 4, but it doesn't matter here.)

    if debug: return _data_stream_to_chunks_debug(data_stream, start)
        
    chunks=[]
    next_start = start+4 # skip byte header
    while next_start < len(data_stream):
        # get start index of this element
        start = next_start

        if _ord(data_stream[start]) == 0xFF:
            # indicator ending a 0xDD section
            chunks.append([start, None, []])
            next_start += 1
            continue
        
        # get element name
        #   and place of continuation (either data block or next element)
        name, cont = _get_byte_str(data_stream, start)

        # skip associated data block, if any
        if cont >= len(data_stream):
            # end of file
            next_start = len(data_stream)
        else:
            data_type = _ord(data_stream[cont])
            if data_type == 0xee:
                next_start = _skip_past_data_ee(data_stream, cont)
            elif data_type == 0xaa:
                next_start = _skip_past_data_aa(data_stream, cont)
            elif data_type == 0xdd:
                next_start = _skip_past_data_dd(data_stream, cont)
            else:
                next_start = _skip_past_number_type(data_stream, cont)
                if next_start is None:
                    # presumably, that was a chunk type without data.
                    next_start = cont                    

        chunks.append([start, name, data_stream[cont:next_start]])
        
    return chunks

def _data_stream_to_chunks_debug(data_stream, start=0):
    """Use this function if unknown chunk types appear.
       This function is not robust and may identify 
       spurious chunks in data segments."""       
    chunks = []
    
    next_start = _find_next_parameter(data_stream, start)
    if next_start > 4+start:
        chunks.append([4+start,' * extended header * ', data_stream[4+start,:next_start]])
    
    while next_start < len(data_stream):
        start = next_start
        name, cont = _get_byte_str(data_stream, start)
        next_start = _find_next_parameter(data_stream, cont)
                
        chunks.append([start, name, data_stream[cont:next_start]])

    return chunks

def get_data_stream_hex_dump(data_stream, start, rows=4, bytes_per_row=16):
    """Return hex dump as printable string"""
    display_start_address = True
    step = bytes_per_row
    end = start+rows*bytes_per_row
    sep=' '*4
    out = []
    while start<end:
        if not display_start_address: addr = ''
        else:            
            addr = u'%0.6x: ' % start
            
        line = data_stream[start:start+step]
        hexa = u' '.join(['%0.2x'%_ord(x) for x in line]) # "u" forces unicode output
        prin = u''.join([_chr(x) if (32<=_ord(x)<=127) else u'\u00b7' for x in line])
        out.append(addr+hexa+sep+prin)        
        start += step
        
    return u'\n'.join(out)

# ##############

def _has_file_marker(data_stream):
    """Check data stream for 0xDEADBEAF file marker"""
    file_marker = _struct.pack("<L", 0xdeadbeaf)
    return data_stream.startswith(file_marker)

def _has_extended_header(data_stream):
    """Check if the first chunk does not start at the 4th byte in the data stream."""
    return _find_next_parameter(data_stream, 0) > 4    

def _find_next_parameter(data_stream, start):
    """Find a number followed by at least the same number of printable ASCII characters
       This is a heuristic method to find the beginning of the next chunk.
       Use should be avoided since it may skip data."""
    ASCII_char = lambda x: 32<=_ord(x)<=127
    start -= 1
    while True:
        start += 1

        try: length = _ord(data_stream[start])
        except IndexError: return None
        
        if length == 0: continue            
        string = data_stream[start+1:start+1+length]
        if all([ASCII_char(char) for char in string]): break
        
    return start

def _get_byte_str(data_stream, start=0):
    """Get string according to byte encoding. Does not validate string."""
    length = _ord(data_stream[start])
    string = _to_string(data_stream[start+1: start+1+length])
    return string, start+1+length

def _skip_past_data_dd(data_stream, start):
    """Skip past chunk data"""
    if (_ord(data_stream[start])!=0xDD):
        raise TypeError('Unexpected block format for 0xDD at 0x%x.' % (start))    
    length = _ord(data_stream[start+1])        
    return start+2+length
    
def _skip_past_data_aa(data_stream, start):
    """Minimal validation and skip past chunk data"""
    if ((_ord(data_stream[start])!=0xAA) or
        (not _is_bit31_set(data_stream, start+1)):
        raise TypeError('Unexpected block format for 0xAA (0x%x) with length and string marker 0x%08x at 0x%x.' % (
            _ord(data_stream[start]), _unpack1('L',data_stream[start+1:start+5]), start))
    char_count = _unpack1('L',data_stream[start+1:start+5]) & 0x7FFFFFFF
    byte_length = char_count * 2
    return start+5+byte_length
        
def _skip_past_data_ee(data_stream, start):
    """Validate and skip past chunk data"""
    if _ord(data_stream[start])!=0xEE:
        raise TypeError('Unexpected block format for 0xEE at 0x%x.' % (start))
    data_type = _unpack1('H',data_stream[start+1:start+3])
    try:
        byte_length={0x11:1, 0x04:4, 0x16: 4, 0x00: 0}[data_type]
    except KeyError:
        raise TypeError('Unknown data type 0x%2x in block 0xEE at 0x%x.' % (data_type, start))
    data_entries = _unpack1('L',data_stream[start+3:start+7])
    if (data_type == 0x00) and (data_entries != 0):
        raise ValueError('Expected empty list with data type EE-00 but found list of %i entries at 0x%x.' % (data_entries, start))
    return start+7+data_entries * byte_length

def _skip_past_number_type(data_stream, start):
    """Validate and skip past chunk data"""
    data_type = _ord(data_stream[start])
    try:
        byte_length = {0x11: 4,
                       0x22: 4,
                       0x33: 4,
                       0x44: 4,
                       0x55: 2,
                       0x66: 2,
                       0x88: 1,
                       0x99: 1,
                       0xbb: 4,
                       0xcc: 8,
                       }[data_type]
    except KeyError:
        # we return None rather than raise an exception
        #   since we call this function to test IF this is a number
        return None
    return start+1+byte_length

def _is_bit31_set(data_stream, start=0):
    """Test bit 31 counting from position "start"."""
    return _unpack1('L',data_stream[start:start+4]) & 0x80000000 != 0
    
def _get_unicode_string(data_stream, start=0, check_string_marker=True):
    """Try to get one unicode string, returns tupe of (string or None, index-after-string)"""
    if len(data_stream)-start<4: return None, start
    if check_string_marker and not _is_bit31_set(data_stream, start): return None, start
    chars, cont = _get_data_list(data_stream, 2, start, raise_error_if_string=False)
    if chars is None: return None, start # probably not enough data for string
    return u''.join([_chr(_unpack1('H',char)) for char in chars]), cont
        
def _get_data_list(data_stream, item_length, start, raise_error_if_string=True):
    """Try to get a list of items of length item_length (or strings: give -number of strings per string tuple), returns tupe of (list of byte-data, index-after-string)"""
    # use item_length<0 to indicate number of strings per list item
    if 4+start>len(data_stream): return None, start # not enough bytes
    length = _unpack1('L',data_stream[start:start+4]) & 0x7FFFFFFF
    if raise_error_if_string and _is_bit31_set(data_stream, start):
        raise ValueError('List of expected item size %i has string marker set.' % (item_length))
    length = length & 0x7FFFFFFF
    unit_length = item_length if item_length>0 else 4*(-item_length)
    if 4+length*unit_length+start>len(data_stream): return None, start # not enough bytes    
    if item_length>=0:
        return [data_stream[start+4+item_length*i:start+4+item_length*(i+1)] for i in range(length)],start+4+length*item_length
    elif item_length<0:
        string_count = (-item_length)
        data_start=start+4
        data_end=data_start
        error=False
        strings=[]
        for j in range(length):
            start_item=data_end
            for i in range(string_count):
                string, data_end = _get_unicode_string(data_stream,data_end)
                error = error or (string is None)
            strings.append(data_stream[start_item:data_end])
        if error: return None, start
        return strings,data_end

#####################################
#
#       Chunk (data) functions
#

def parse_chunks(chunks, level=None, debug=False):
    """Dispatch function to parse chunk data at different levels (default: maximum level)
       Note that format of level 3 is subject to change in the future.
       Set debug to True to disable most sanity checks and try to interpret as
       much as possible. Note that this may return spurious chunks."""
    level = level or 3
    chunks = _parse_chunk_types(chunks) # level 1
    if level >= 2:
        chunks = _parse_chunk_ee_subtypes(chunks, debug) # EE04, EE16, but return raw data for EE11
    if level >= 3:
        chunks = _parse_chunk_ee11_data_records(chunks, debug)

    return chunks

def _parse_chunk_types(chunks):
    """Decode element data"""
    dispatch={            
            0x11: _parse_data_11,
            0x22: _parse_data_22,
            0x33: _parse_data_33,
            0x44: _parse_data_44,
            0x55: _parse_data_55,
            0x66: _parse_data_66,            
            0x88: _parse_data_88,
            0x99: _parse_data_99,
            0xaa: _parse_data_aa,
            0xbb: _parse_data_bb,
            0xcc: _parse_data_cc,
            0xdd: _parse_data_dd,
            0xee: _parse_data_ee, # NB: break out sub-types from this function
            }
    out = []
    for chunk in chunks:
        address, name, raw_data = chunk
        if name is not None:
            # normal chunk
            if len(raw_data)>0:
                data_type = _ord(raw_data[0])
                data, type_code = dispatch[data_type](raw_data)
            else:
                # e.g., txutil.TUnit, CTSingleGroupDataBlock            
                type_code = ''
                data = []
        else:
            # "end" marker
            #  each 0xFF ends one level of nesting
            #   started by a 0xDD chunk
            # now we can give it a name (that would, technically, be legal (ie. 0x00))
            name, type_code, data = '', 'end', []
            
        out.append([address, name, type_code, data])
    return out

def _parse_chunk_ee_subtypes(chunks, debug=False):
    """Check all chunks and extract lists for data type EE."""
    result = chunks[:]
    for index, chunk in enumerate(chunks):
        address, name, data_type, data = chunk
        if data_type !=u'EE': continue
        try: interpreted_data, type_code = _parse_data_ee_subtypes(data, debug)
        except KeyError:
            print('Address: 0x%X' % address)
            print(get_data_stream_hex_dump(data,0))
            raise
        result[index] = [address, name, type_code, interpreted_data]
    return result

def _parse_chunk_ee11_data_records(chunks, debug=False):
    """Check all chunks and extract records for data type EE11."""
    result = chunks[:]
    for index, chunk in enumerate(chunks):
        address, name, data_type, data = chunk
        if data_type !=u'EE11': continue
        if name.startswith(u'QS_'):
            interpreted_data, type_code = _parse_record_data_ee11_formats_QS(name, data, debug)
        elif name==u'Entry':
            interpreted_data, type_code = _parse_record_data_ee11_formats_Entry(data, debug)
        else:
            if not debug: raise ValueError('Unknown data records for chunk type "%s".' % name)
            # i ndebug mode: copy data verbatim
            interpreted_data, type_code = data[:], u'EE11'
        result[index] = [address, name, type_code, interpreted_data]
    return result

#################
#
#   parse data types
#

_parse_data_11 = lambda data: (_unpack1('l',data[1:]),'11') if _ord(data[0])==0x11 else (None, None) # hex number (e.g. color), also can be 0xffffffff for -1 (n.d.), or counter number (decimal), signed index (-1 for not defined)
_parse_data_22 = lambda data: (_unpack1('L',data[1:]),'22') if _ord(data[0])==0x22 else (None, None) # Value
_parse_data_33 = lambda data: (_unpack1('l', data[1:]),'33') if _ord(data[0])==0x33 else (None, None) # prob int -- screen coords, also sometimes negative
_parse_data_44 = lambda data: (_unpack1('L', data[1:]),'44') if _ord(data[0])==0x44 else (None, None) # int 'capabilities', or 0/1 values, color
_parse_data_55 = lambda data: (_unpack1('h', data[1:]),'55') if _ord(data[0])==0x55 else (None, None) # only Flag: 0x0 or 0xffff
_parse_data_66 = lambda data: (_unpack1('H', data[1:]),'66') if _ord(data[0])==0x66 else (None, None) # (ID numbers, basically counters)
_parse_data_88 = lambda data: (_ord(data[1:]),'88') if _ord(data[0])==0x88 else (None, None) # non-binary flag, signed
_parse_data_99 = lambda data: (_ord(data[1:]) != 0,'99') if _ord(data[0])==0x99 else (None, None) # binary flag
_parse_data_aa = lambda data: (_get_unicode_string(data,1)[0],'AA') if _ord(data[0])==0xAA else (None, None)
_parse_data_bb = lambda data: (_s2d(_unpack1('f', data[1:])),'BB') if _ord(data[0])==0xBB else (None, None) # ProgVersion, Percent
_parse_data_cc = lambda data: (_unpack1('d', data[1:]),'CC') if _ord(data[0])==0xCC else (None, None) # ok
_parse_data_dd = lambda data: (len(data[1:]),'DD') if _ord(data[0])==0xDD else (None, None) # number of zero-bytes
_parse_data_dd = lambda data: (_get_byte_str(data[1:])[0],'DD') if _ord(data[0])==0xDD else (None, None) # number of zero-bytes
_parse_data_ee = lambda data: (data[1:],'EE') if _ord(data[0])==0xEE else (None, None) # number of zero-bytes

########################
#
#   parse EE sub-types
#

def _parse_data_ee_subtypes(data, debug=False):
    """Parse known subtypes and be particularly lenient in debug mode.
       In debug mode, "-debug" may be appended to the type code,
       or unparsed data with type code "EE" may be returned."""
    sub_type = _unpack1('H',data[:2])
    byte_lengths={0x11:1, 0x04:4, 0x16: 4, 0x00: 0}
    if (sub_type not in byte_lengths) and debug:
        return data[:], 'EE' # simply return un-interpreted

    type_code = u'EE%0.2X' % (sub_type)
        
    byte_length=byte_lengths[sub_type]    
        
    entries = _unpack1('L',data[2:6])    

    # perform sanity check on length of data
    expected_data_length = byte_length*entries
    if not debug and (len(data) > expected_data_length+6):
        raise ValueError('Too much data in %s: %s' % (
        repr(data), repr(data[7+expected_data_length:])))
    if len(data) < expected_data_length+6:
        if debug: return data[:], 'EE'
        raise ValueError('Not enough data in %s: expected %i bytes for %i entries, got %i bytes.' % 
        (repr(data), expected_data_length, entries, len(data)-6))

    # get list elements        
    items, cont = _get_data_list(data, byte_length, 2)
    extra_data = data[cont:]

    # 0x04 is single precision floats
    if sub_type == 0x04:        
        interpreted_data=[_s2d(_unpack1('f',item)) for item in items]
    elif sub_type == 0x16:
        interpreted_data=[_unpack1('L',item) for item in items]
    elif sub_type == 0x11:
        interpreted_data=[_unpack1('B',item) for item in items]
    elif sub_type == 0x00:
        # probably always an empty list. If not,
        # we return a list of item-length b'', with any data as extra_data
        interpreted_data = items
    else: raise ValueError('Unknown data format or sub-type code 0x%x for EE' % sub_type)

    if len(extra_data)>0: 
        interpreted_data,type_code = [interpreted_data, extra_data], type_code+'-debug'
    return interpreted_data, type_code

#####################
#
#   parse EE11 data records
#

# format string:
# Byte B
# Word H
# Long L
# single f
# double d
# list of (tubles):   (...)
# string s
# not-checked string S
# write like so: 3BLd(Ld)2(SSSS) etc.

# everything up to ( or s/S can be put directly into struct.unpack()
def _get_tokens_from_format_string(fmt):
    direct={'B':1,'b':1,'H':2,'h':2,'L':4,'l':4,'f':4,'d':8}    
    tokens=[]
    acc=''
    times = None
    length = 0
    fmt += ' ' # add a character to flush the accumulator
    while len(fmt)>0:
        c = fmt[0]
        if c in direct:    
            acc+=c * (times if times is not None else 1)            
            length += direct[c]*(times if times is not None else 1)
            times=None            
        else:
            if (len(acc)>0) and not ('0'<=c<='9'):
                tokens.append(['direct',acc, length])
                acc=''
                length=0
            if c in ('s','S'):                
                tokens+=[['string',c=='S'] for i in range(times if times is not None else 1)]
                times = None
            elif c == '(':
                tokens.append(['list','start'])
            elif c == ')':
                tokens.append(['list','end'])
            elif '0'<=c<='9':
                times = 0 if times is None else times*10
                times += _ord(c)-_ord('0')
            elif c not in ('\r','\n','\t',' ',','):
                raise ValueError('Unknown character %s in format string"%s".' % (c, fmt))
        fmt = fmt[1:]
        
    return tokens

def _parse_data_by_tokens(data,tokens):
    max_num={'B':2**8-1,'b':2**8-1,'H':2**16-1,'h':2**16-1,'L':2**32-1,'l':2**32-1,'f':'','d':''}
    list_count = None    
    result = [[]]
    current_list_level=0
    start = 0
    token_idx = 0
    while (token_idx < len(tokens)):
        token = tokens[token_idx]
        prop, value, length = token+[None,]*(3-len(token))
        if prop == 'direct':
            if start+length<=len(data):
                out = list(_struct.unpack('<'+value, data[start:start+length]))
                out = [v if v != max_num[c] else -1 for v, c in zip(out,value)]
                result[-1] += out
            start += length
        elif prop == 'string':            
            string, start = _get_unicode_string(data, start, check_string_marker=value)
            if string is not None: result[-1] += [string]
        elif (prop,value) == ('list','start'):
            if len(data)<start+4: break # end processing, no more data and we are at the lowest level at the moment
            result.append([]) # add data to new layer to group tuples
            if list_count is None:
                result.append([])  # add a new layer to nest the list                
                list_count = _unpack1('L',data[start:start+4])                
                start += 4                   
            if list_count == 0:
                while tokens[token_idx][:2] != ['list','end']:
                    token_idx += 1
                token_idx -= 1
        elif (prop,value) == ('list','end'):
            # store data in list as tuple only if there are at least 2 entries
            # otherwise, store as linear scalars within the list
            result[-2]+=[tuple(result[-1])] if len(result[-1])>=2 else result[-1]
            result.pop()
            list_count -= 1
            if list_count >0:                 
                while tokens[token_idx][:2] != ['list','start']:
                    token_idx -= 1
                token_idx -= 1
            else:
                result[-2]+=[result[-1]] # store list in results, always as list
                result.pop()                
                list_count = None
        else:
            raise ValueError('Unknown token %s.' % repr(token))
        token_idx += 1
    if len(result) != 1:
        raise ValueError('parsing result %s' % repr(result))
    return result[0], start    
    
def _parse_record_data_ee11_formats_QS(name, data, debug=False):
    fmt={'QS_Par':[1,'4B'],
         'QS_ValPar':[1,'dSH9B'],
         'QS_TextPar':[1,'4S'],
         'QS_SelPar':[2,'L(L)4S'],
         'QS_ValArrPar':[2,'SHB(L)'],
         'QS_ValArrParElem':[2,'(Ld)'],
         'QS_ArrPar':[2,'(L)B'],
         'QS_ParProp':[7,'9B1H9S3H5S9BS4B'],
         'QS_ValProp':[1,'4B'],
         'QS_TextProp':[1,'8B'],
         'QS_SelProp':[4,'3B,(SSSS)(SSSS)(S)(S)(H)(L)(S)'],
         'QS_ValArrParProp':[2,'4BH4B'],
         'QS_SkalProp':[2,'2S2B'],
         'QS_ValSetting':[2,'2SLS3BH2B(H)(S)11B'],#[2,'2SLS3BH2B(H)s11B'],
         'QS_NumFmt':[2,'4Bd'],
         'QS_Plaus':[1,'9B6BH6BH6B'],
         'QS_Tol':[1,'9B6BH6BH3B'],
         }
    if name not in fmt: return data[:], 'EE11' # not defined
    sub_type, format_ = fmt[name]
    if sub_type != _ord(data[0]): return data[:], 'EE11' # unknown sub-type
    tokens= _get_tokens_from_format_string(format_)
    output, cont = _parse_data_by_tokens(bytearray(data[1:]),tokens)    
    if cont<len(data)-1: output.append((None,data[1+cont:]))    
    return output, 'EE11-%0.2x-%s'%(sub_type,format_)

    
def _parse_record_data_ee11_formats_Entry(data, debug=False):
    """Provisional decoder for Entry record format. 
    Note that output format is subject to change."""
    if (len(data)<1) or _ord(data[0]) != 0x02: return data, 'EE11' # unknown format
    
    data = bytearray(data)
    format_string = []
    line = []
    start = 0
    # get sub-type
    sub_type = _ord(data[start])    # this is 0x02    
    start += 1
    format_string.append('B')
    # next, there will be the ERFC and a 3-tuple of bytes
    for i in range(4):
        line.append(_ord(data[start]))
        start += 1
        format_string.append('B')
    
    while start < len(data):
        string, start = _get_unicode_string(data, start=start, check_string_marker=True)
        if string is not None: # found a string
            line.append(string)
            format_string.append('S')
            continue
        numbers, cont, fmt = _get_prefixed_data(data, start)
        if numbers is not None:
            if _next_is_prefixed_data_or_string(data, cont):
                line += numbers
                start = cont
                format_string.append(fmt)
                continue
        if _next_is_prefixed_data_or_string(data, start+4) and (len(data)-start>=4):
            line += list(_struct.unpack('<HH',data[start:start+4]))
            start += 4
            format_string.append('HH')
            continue
        if _next_is_prefixed_data_or_string(data, start+2) and (len(data)-start>=2):
            line += list(_struct.unpack('<BB',data[start:start+2]))
            start += 2
            format_string.append('BB')
            continue
        line += list(_struct.unpack('<B',data[start:start+1]))
        start += 1
        format_string.append('B')
        
    return line, u'EE11-%0.2X-%s' % (sub_type, u''.join(format_string))
    
def _get_prefixed_data(data, start):
    """Get a list of numbers introduced by a type prefix specific to Entry record."""
    if len(data)-start < 2: return None, start, None
    prefix = _ord(data[start])
    value, cont, fmt = None, start, None
    if (prefix ==0x07) and (len(data)-start>=9):
        value, cont, fmt = [_unpack1('d',data[start+1:start+9]),], start+9, 'd'
    elif (prefix ==0x64) and (len(data)-start>=5):
        value, cont, fmt = [_unpack1('L',data[start+1:start+5]),], start+5, 'l'
    elif (prefix ==0x01) and (len(data)-start>=5):
        value, cont , fmt = list(_struct.unpack('<BBBB',data[start+1:start+5])), start+5, 'bbbb'
    elif (prefix ==0x04) and (len(data)-start>=2):
        value, cont, fmt = [_ord(data[start+1]),], start+2, '1'
    return value, cont, fmt
        
def _next_is_prefixed_data_or_string(data, start):
    """Next is end of file, prefixed data, or string."""
    if start>=len(data): return True
    string, cont = _get_unicode_string(data, start=start, check_string_marker=True)
    if string is not None: return True
    numbers, cont, fmt = _get_prefixed_data(data, start)
    if numbers is not None: return True
    return False

###########################################
#
#   Single precision conversion
#   helper function
#

def _single_as_double(presumed_single):
    """Convert a double-precision number containing a single-precision number
       into the shortest decimal representation resulting in the same
       single-precision number."""
    mantissa = lambda string: string.lower().split('e')[0]
    exponent = lambda string: 'e'+string.lower().split('e')[1] if 'e' in string.lower() else ''
    fractional = lambda string: (mantissa(string)+'.').split('.')[1]

    start = abs(presumed_single)
    start_code = _struct.pack('<f', start) # this is what we need to keep
    # get the most precise single precision representation
    #  (e.g. 1.0000001)
    start_value = value = '%.9g' % start # example of a number that needs 9 (rather than 8) digits: 0.104521975
    if _struct.pack('<f', float(value)) == start_code:
        good_value = value
    else: raise ValueError('Incorrect assumption on single precision float %s.' % repr(presumed_single))
    while len(fractional(value))>0:
        # if there's no decimal fraction then we're done
        
        # let's round down and see what happens
        # -> remove last digit behind decimal
        m = mantissa(value)[:-1].rstrip('0')
        value = m+exponent(value)

        try:
            float_value = float(value)
        except ValueError:
            # generate output for debug
            print('Attempt failed converting %r to float.' % value)
            raise
        
        if _struct.pack('<f', float(value)) != start_code:
            value = good_value
            # rounding down didn't work, so try
            # rounding up            
            m,e = mantissa(value), exponent(value)            
            decimal=len(m)-1-m.index('.') # keep decimal position from behind
            m=m.replace('.','')            
            rounded='%i'%(int(m)-int(m[-1])+10)
            value=(rounded[:-decimal]+'.'+rounded[-decimal:]).rstrip('0')+e            
            
        if _struct.pack('<f', float(value)) != start_code:
            # rounding up didn't help either
            break
    
        good_value = value

    # the result can now be converted accuractely with
    # shortest = '%.9g'%float(good_value)
    
    return float(good_value) * (-1. if presumed_single<0. else 1.)

_s2d = _single_as_double    
