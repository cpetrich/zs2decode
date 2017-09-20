"""Output functions for parsed zs2 chunks."""
import json
from xml.dom import minidom
import zs2decode.parser as parser
# Author: Chris Petrich
# Copyright: Copyright 2015-2017, Chris Petrich
# License: MIT

def _XML_entities():
    crange = lambda a,b: ['%c' % parser._chr(v) for v in range(ord(a), ord(b)+1)]
    vrange = lambda a,b: ['%c' % parser._chr(v) for v in range(a,b+1)]
    NameStartChar = (crange('A','Z')+crange('a','z')+[':','_']+
                     vrange(0xC0,0xD6)+vrange(0xD8,0xF6)+vrange(0xF8,0xFF))
    # Python xml.etree.ElementTree rejects ':' in entity names
    NameStartChar.remove(':')
    NameChar = NameStartChar + crange('0','9') +['-','.',u'\xB7']
    return NameStartChar, NameChar

_xml_name_start_char, _xml_name_char = _XML_entities()

def _xml_sanitized_ASCII_name(name):
    """Ensure that name is a legal XML entity name, assuming input 'name' is ASCII
       Current solution: Replace all illegal characters with ':'."""
    sub = '_'
    if name == '': return sub
    if name[0] not in _xml_name_start_char:
        name = ':'+name[1:]
    for idx in range(1,len(name)):
        if name[idx] not in _xml_name_char:
            name = name[:idx]+sub+name[idx+1:]
    return name

def _add_xml_element(doc, current, name, attributes):
    """Add XML element to tree. Uses 'current' to keep track of nesting."""
    if attributes['type'] != 'end':
        elem = doc.createElement(_xml_sanitized_ASCII_name(name))
        for attr in attributes:
            # ugly but works with Py2 and Py3:
            elem.setAttribute(attr, attributes[attr])
        if len(current) == 0:
            doc.appendChild(elem)
        else:
            current[-1].appendChild(elem)
        if attributes['type']=='DD':
            current.append(elem)
    else:
        current.pop(-1)

def chunks_to_XML(chunks, with_address=False):
    """Produces an XML representation of the chunks."""
    if chunks[0][2] != 'DD':
        raise ValueError('First chunk is not of data type 0xDD: %r' % chunks[0])

    data_types = [chunk[2] for chunk in chunks]
    if data_types.count('DD') != data_types.count('end'):
        raise ValueError('Cannot generate XML file since section start and end do not balance. Output as text file instead to debug.')

    doc = minidom.Document()
    current = []
    for chunk in chunks:
        address, name, data_type, data = chunk
        if isinstance(data,(int,float,list)):
            # note that 'bool' is derived from 'int'.
            # note that json uses 'true' rather than 'True'
            display=json.dumps(data, ensure_ascii=False)
        else:
            # create escaped string enclosed in double quotes,
            #  then strip the double quotes
            display = json.dumps(data, ensure_ascii=False)[1:-1]

        attrib = {}
        if with_address:
            attrib['address']='%0.6x' % address
        attrib['type'] = data_type
        attrib['value'] = display

        _add_xml_element(doc, current, name, attrib)

    return doc.toprettyxml(indent="  ",encoding='UTF-8')


def chunks_to_text_dump(chunks):
    """Produces a string representation."""
    out=[]
    DD_names = []
    level = 0

    data_types = [chunk[2] for chunk in chunks]
    if data_types.count('DD') != data_types.count('end'):
        # do not indent since there's obviously something wrong
        indent = None
    else:
        indent = '  '

    for chunk in chunks:
        address, name, data_type, data = chunk
        if data_type == 'end': level-=1

        _space = indent*level if indent is not None else ''

        comment = '' if data_type != 'end' else './'+'/'.join(DD_names)
        if data_type == 'end': DD_names.pop()

        data_string = repr(data) # Python 2: this escapes unicode characters
        line = u' '.join([u'%.6x:'%address, _space+name, '[%s]'%data_type, data_string, comment])

        if data_type == 'DD':
            DD_names.append(name)
            level+=1
        out.append(line)
    return bytearray(u'\n'.join(out), encoding='UTF-8')
