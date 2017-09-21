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
        (not _is_bit31_set(data_stream, start+1))):
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
        byte_length={0x11:1, 0x04:4, 0x05:8, 0x16: 4, 0x00: 0}[data_type]
    except KeyError:
        raise TypeError('Unknown data type 0x%02x in block 0xEE at 0x%x.' % (data_type, start))
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
    byte_lengths={0x11:1, 0x04:4, 0x05:8, 0x16: 4, 0x00: 0}
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

    if sub_type == 0x04: # 0x0004 is single precision floats
        interpreted_data=[_s2d(_unpack1('f',item)) for item in items]
    elif sub_type == 0x05: # 0x0005 is double precision float
        interpreted_data=[_unpack1('d',item) for item in items]
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
# Byte unsigned B signed b
# Word unsigned H signed h
# Long unsigned L signed l
# single f
# double d
# list of (tuples):   (...)
# string S
#
# shorthand:
# 2S2(LH) expands to SS(LH)(LH)(LH)
# 2S2(LH)B=3 evaluates successfully if the last value is equal to 3
# B=3:BH=4 evaluates successfully if B==3 AND the H==4
# B=3:BH=4:BHS will evaluate data as BHS only if B==3 and H==4

def expand_format(fmt):
    """Expand a format including multiple applications of a token
       into a sequence without multiplication.
       Also works with lists and nested lists."""
    # this function may be of broader interest to those interpreting format string and data
    if fmt.count('(') != fmt.count(')'): raise ValueError('Brackets do not balance in %r' % fmt)
    if fmt.find(')') < fmt.find('('): raise ValueError('Closing bracket before opening in %r' % fmt)
    out, fmt_idx, times = '', 0, None
    while fmt_idx < len(fmt):
        char = fmt[fmt_idx]
        if char>='0' and char<='9':
            times = (times or 0) * 10 + (ord(char)-ord('0'))
            fmt_idx += 1
        elif char == '(':
            close_idx, nesting = fmt_idx + 1, 0
            while fmt[close_idx] != ')' or nesting>0:
                if fmt[close_idx] == '(': nesting += 1
                elif fmt[close_idx] == ')': nesting -= 1
                close_idx += 1
            out += ('(%s)' % expand_format(fmt[fmt_idx+1:close_idx]))*(times if times is not None else 1)
            times = None
            fmt_idx = close_idx + 1
        else:
            out += char*(times if times is not None else 1)
            times = None
            fmt_idx += 1
    return out

def _get_next_token_compact(fmt, fmt_idx):
    """Helper for _compact_format() to find next token, compacting
       stuff in brackets on the fly."""
    if fmt[fmt_idx] != '(':
        token = fmt[fmt_idx]
        close_idx = fmt_idx
    else:
        close_idx, nesting = fmt_idx + 1, 0
        while fmt[close_idx] != ')' or nesting>0:
            if fmt[close_idx] == '(': nesting += 1
            elif fmt[close_idx] == ')': nesting -= 1
            close_idx += 1
        token = '(%s)' % _compact_format(fmt[fmt_idx+1:close_idx])
    return token, close_idx + 1

def _compact_format(fmt):
    """Consolidate repeated tokens into their number followed by a single token,
       also works with lists and nested lists"""
    if not len(fmt): return fmt
    if fmt.count('(') != fmt.count(')'): raise ValueError('Brackets do not balance in %r' % fmt)
    if fmt.find(')') < fmt.find('('): raise ValueError('Closing bracket before opening in %r' % fmt)
    # ensure format is in its expanded form
    if any(check in fmt for check in '0123456789'): fmt = expand_format(fmt)
    out, fmt_idx, times, last_token = '', 0, None, ''
    while fmt_idx < len(fmt):
        token, next_idx = _get_next_token_compact(fmt, fmt_idx)
        if (token == last_token) or (last_token == ''):
            times = (times or 0) + 1
        else:
            if (times or 0) > 1:
                out += '%i%s' % (times, last_token)
            else:
                out += '%s' % (last_token)
            times = 1
        fmt_idx = next_idx
        last_token = token
    if (times or 0) > 1:
        out += '%i%s' % (times, token)
    else:
        out += '%s' % (token)
    return out

def _parse_data_by_format_helper(fmt, data, strict_unsigned = None):
    """This is the core function for EE11 format string interpretation"""
    # returns data_idx rather than residual data[data_idx:]
    strict_unsigned = True if strict_unsigned is None else strict_unsigned
    fmt_idx, data_idx = 0, 0
    parsed_fmt, parsed_data = '', []
    while fmt_idx < len(fmt):
        token = fmt[fmt_idx]
        if token == '.':
            # interpret everything remaining as bytes
            char = 'B'
            length = _struct.calcsize(char)
            new_data = [_struct.unpack('<%s'%char,data[idx:idx+length])[0] for idx in range(data_idx, len(data))]
            parsed_data += new_data
            parsed_fmt += char*len(new_data)
            data_idx = len(data)
            fmt_idx += 1
        elif token == '*':
            # use heuristic to interpret remaining bytes as
            #  string or bytes
            _, fmt_tail, data_tail, _ = _parse_heuristic_string_byte(data[data_idx:])
            parsed_data += data_tail
            parsed_fmt += fmt_tail
            data_idx = len(data)
            fmt_idx += 1
        elif token == 'S': # string
            string, cont_idx = _get_unicode_string(data, data_idx, check_string_marker=True)
            if string is None:
                return False, parsed_fmt, parsed_data, data_idx
            parsed_data.append(string)
            parsed_fmt += token
            data_idx = cont_idx
            fmt_idx += 1
        elif token == '(': # list
            closing_idx, nesting = fmt_idx+1, 0
            while fmt[closing_idx] != ')' or nesting > 0:
                if fmt[closing_idx] == ')': nesting -= 1
                elif fmt[closing_idx] == '(': nesting += 1
                closing_idx += 1
            sub_fmt = fmt[fmt_idx+1:closing_idx]
            try:
                count = _struct.unpack('<L', data[data_idx:data_idx+4])[0]
            except _struct.error:
                return False, parsed_fmt, parsed_data, data_idx
            list_data = []
            list_data_idx = data_idx+4
            for run in range(count):
                success, new_fmt, new_parsed_data, new_data_idx = (
                    _parse_data_by_format_helper(sub_fmt, data[list_data_idx:], strict_unsigned=strict_unsigned))
                if success:
                    # flatten one-tuples to elements
                    if len(new_parsed_data) == 1: new_parsed_data = new_parsed_data[0]
                    list_data.append(new_parsed_data)
                    list_data_idx += new_data_idx
                else:
                    # return state we had before entering the list
                    return False, parsed_fmt, parsed_data, data_idx
            parsed_data.append(list_data)
            data_idx = list_data_idx
            parsed_fmt += '(%s)' % sub_fmt
            fmt_idx = closing_idx + 1
        else:
            byte_length = _struct.calcsize(token)
            try:
                number_raw = _struct.unpack('<'+token, data[data_idx:data_idx+byte_length])[0]
            except _struct.error:
                return False, parsed_fmt, parsed_data, data_idx

            if not strict_unsigned and token not in 'fd':
                # check if we have to overwrite the highest unsigned number
                #    with signed '-1' (since this is typically a flag)
                max_value = 2**(8*byte_length)-1
                if number_raw == max_value:
                    number = -1
                    parsed_fmt += token.lower() # indicate signed
                else:
                    number = number_raw
                    parsed_fmt += token
            elif token == 'f':
                number = _single_as_double(number_raw)
                parsed_fmt += token
            else:
                number = number_raw
                parsed_fmt += token

            parsed_data.append(number)
            data_idx += byte_length
            fmt_idx += 1
    return True, parsed_fmt, parsed_data, data_idx

def _parse_data_by_format(fmt, data, strict_unsigned = None):
    """Entry point for lowest level of data parsing. Returns success==True if
       the entire format string could had been parsed."""
    # entry point for Level 1 of parsing algorithm
    if any(check in fmt for check in '0123456789'): fmt = expand_format(fmt)
    success, parsed_fmt, parsed_data, data_idx = _parse_data_by_format_helper(fmt, data, strict_unsigned = strict_unsigned)
    return success, _compact_format(parsed_fmt), parsed_data, data[data_idx:]

def _parse_heuristic_string_byte(data):
    data_idx = 0
    data_out, fmt_out = [], ''
    while data_idx < len(data):
        string, cont_idx = _get_unicode_string(data, data_idx, check_string_marker=True)
        if string is None:
            data_out.append(_struct.unpack('<B',data[data_idx:data_idx+1])[0])
            data_idx += 1
            fmt_out += 'B'
        else:
            data_out.append(string)
            data_idx = cont_idx
            fmt_out += 'S'
    return True, fmt_out, data_out, bytearray()

def _parse_data_by_expression(expr, data, strict_unsigned = None):
    """Evaluate a single parser expression"""
    # entry point for Level 2 of parsing algorithm
    fmt = expr.split('=',1)[0]
    l1_success, parsed_fmt, parsed_data, residual = _parse_data_by_format(fmt, data, strict_unsigned = strict_unsigned)
    if '=' not in expr:
        # success means that the string has been parsed on full
        success = l1_success and len(residual) == 0
    else:
        expected = expr.split('=',1)[1]
        if expected == '':
            # matches anything
            success = l1_success
        else:
            # last parameter parsed is equal to whatever is specified
            try:
                # cast to appropriate type
                # NB: eval enables us to test lists
                compared = type(parsed_data[-1])(eval(expected))
            except (ValueError, TypeError):
                # wrong type
                compared = None
            success = l1_success and compared is not None and compared == parsed_data[-1]
    return success, parsed_fmt, parsed_data, residual

def _parse_record(grammar, data, strict_unsigned = None):
    """Evaluate data record according to given grammar."""
    # Main entry point (Level 3) for parsing of data in EE11 records
    if isinstance(grammar,(list,tuple)):
        # within a list of chains, return result of first chain
        #   that evaluates successfully
        for chain in grammar:
            result = _parse_record(chain, data, strict_unsigned = strict_unsigned)
            if result[0]: break # first chain that evaluates successully
    else:
        # within a chain, ALL expressions have to evaluate successfully
        for expr in grammar.split(':'):
            success, parsed_fmt, parsed_data, residual = (
                _parse_data_by_expression(expr, data,
                                          strict_unsigned=strict_unsigned))
            if not success:
                break
        result = success, parsed_fmt, parsed_data, residual
    return result

def _parse_record_data_ee11_formats_QS(name, data, debug=False):
    fmt={'QS_Par':['B=1:B4B'],
         'QS_ValPar':['B=1:BdSH9B'],
         'QS_TextPar':['B=1:B4S'],
         'QS_SelPar':['B=2:BL(L)4S'],
         'QS_ValArrPar':['B=2:BSHB(L)'],
         'QS_ValArrParElem':['B=2:B(Ld)'],
         'QS_ArrPar':['B=2:B(L)B'],
         'QS_ParProp':['B=7:B9BH9S3H5SL=0:B9BH9S3H5SL2HBS4B',
                       'B=7:B9BH9S3H5SL=2:B9BH9S3H5SL2HBLS4B',
                       'B=8:B9BH*'],
         'QS_ValProp':['B=1:B4B'],
         'QS_TextProp':['B=1:B8B'],
         'QS_SelProp':['B=4:B3B2(4S)2(S)(H)(L)(S)','B=4:B3B',
                       'B=5:B3B2(4S)2(S)(H)(L)(S)B','B=5:B4B'],
         'QS_ValArrParProp':['B=2:B4BH4B'],
         'QS_SkalProp':['B=2:B2S2B'],
         'QS_ValSetting':['B=2:B2SLS3BH2B(H)(S)11B'],
         'QS_NumFmt':['B=2:B4Bd'],
         'QS_Plaus':['B=1:B9B6BH6BH6B'],
         'QS_Tol':['B=1:B9B6BH6BH3B'],
         }

    grammar = fmt.get(name,'*') # get specific grammar or use default
    # if all fails, ensure success through linear heuristic interpretation
    if grammar[-1] != '*': grammar.append('*')
    success, parsed_fmt, parsed_data, residual = _parse_record(grammar, bytearray(data), strict_unsigned=False)
    if not success or len(residual):
        # this should never be reached as long as we parse with '*' or '.'
        raise ValueError('Unexpected parse error of EE11 for %r with %r' % (name, data))
    if debug:
        # Raise awareness of application of heuristics
        actual = expand_format(parsed_fmt)
        for option in grammar:
            requested = expand_format(option.split(':')[-1])
            if actual == requested: break
        else:
            print('Applied heuristic format %s for %s with %s' %
                  (parsed_fmt, name, repr(data)[:200]+('...' if len(repr(data))>200 else '')))
    return parsed_data, (('EE11-%s' % parsed_fmt) if len(parsed_fmt) else 'EE11')

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
    """Convert a double-precision number containing a single-precision value
       into a double-precision number with the shortest decimal
       representation that still has the same single-precision value.
       Example: struct.unpack('<f',...) of the single-precision representation
                of 0.1 returns 0.10000000149011612. The current function
                converts the latter value 'back' to 0.1. Note that there
                are cases where the solution is not unique.
       """
    # helper functions
    def tup2int_str(tup):
        """Return positive integer part of tuple (or '0')"""
        if tup[2]<=0:
            return ''.join('%i' % v for v in tup[1][:max((0,len(tup[1])+tup[2]))]) or '0'
        else:
            return ''.join('%i' % v for v in tup[1])+('0'*tup[2])

    def tup2frac_str(tup):
        """Return positive fractional part of tuple (or '')"""
        return '0'*(-len(tup[1])-tup[2])+''.join('%i' % v for v in tup[1][max((0,len(tup[1])+tup[2])):])

    def add_one_in_last(int_str, frac_str):
        """Add 1 to least significant digit in fractional part (or to integer)"""
        if frac_str == '': return (str(int(int_str)+1), '')
        new_frac = ('%%0%ii' % len(frac_str)) % (int(frac_str)+1)
        carry = new_frac[:len(new_frac)-len(frac_str)] or '0'
        return (str(int(int_str)+int(carry)), new_frac[len(new_frac)-len(frac_str):])

    def equal(current, expected):
        """Test expectation, treat overflow as regular failure"""
        try:
            return _struct.pack('<f',current) == expected
        except OverflowError:
            return False

    if presumed_single != presumed_single:
        return presumed_single # NaN
    if presumed_single in (float('inf'), float('-inf'), float('-0')):
        return presumed_single

    # work with positive numbers, recover sign at the end
    value = abs(presumed_single)
    try:
        required = _struct.pack('<f', value) # this is what we want to maintain
    except OverflowError:
        #   value exceeds limit of single-precision floats
        #      this function should not have been called in the first place
        #      --> fail with debug info
        print('Attempted to interpret %r as single.' % presumed_single)
        raise

    # turn float into tuple of format decimal.Decimal().as_tuple()
    # limit to 9 significant digits in keeping with single-precision resolution
    test = (int(presumed_single<0.), [int(v) for v in ('%.9e' % value).split('e')[0].replace('.','')],
            int(('%.9e' % value).split('e')[1])-9)

    # decompose tuple into string components
    integer = tup2int_str(test)
    fraction = tup2frac_str(test).rstrip('0')
    good = (integer, fraction) # last known correct value

    while fraction:
        # round down by truncation and see if we're still good
        fraction = fraction[:-1]
        if not equal(float(integer+'.'+fraction), required):
            # rounding down didn't work, so try
            #   rounding up (i.e., add one to truncated number)
            integer, fraction = add_one_in_last(integer, fraction)
            if not equal(float(integer+'.'+fraction), required):
                # rounding up didn't help either --> we're done
                break
        # new best result
        good = (integer, fraction.rstrip('0'))

    result = float('.'.join(good)) * (-1 if presumed_single<0. else 1)
    # confirm we're good:
    if _struct.pack('<f', result) != _struct.pack('<f', presumed_single):
        raise ValueError('Failed interpretation of %r, obtained %r.' % (
            presumed_single, result))
    return result

_s2d = _single_as_double
