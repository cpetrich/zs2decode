"""Output functions for parsed zs2 chunks."""

# Author: Chris Petrich
# Copyright: Copyright 2015, Chris Petrich
# License: MIT

    
def chunks_to_XML(chunks, with_address=False):
    """Produces an XML representation of the chunks."""
    # The implementation of this function is not pretty but
    #   requires no dependencies.

    def _xml_attr_escape(string):
        """Escape characters in string"""
        string=string.replace('&','&amp;')
        string=string.replace('>','&gt;')
        string=string.replace('<','&lt;')
        string=string.replace('\\"','&quot;')
        string=string.replace("\\'",'&apos;')
        return string

    data_types = [chunk[2] for chunk in chunks]
    if data_types.count('DD') != data_types.count('end'):
        raise ValueError('Cannot generate XML file since section start and end do not balance. Output as text file instead to debug.')
    
    out=[]
    out.append('<?xml version="1.0" encoding="UTF-8"?>')    
    section_names = []
    level = 0
    for chunk in chunks:
        address, name, data_type, data = chunk
        if data_type == 'end': level-=1
            
        _space = '  '*level
        show_address= "address='%0.6x' "%address if with_address else ''
        if data_type != 'end':
            # here we enclose the value in quotation marks...
            if isinstance(data,int) or isinstance(data,float) or isinstance(data,list):
                # note that 'bool' is sderived from 'int'
                display=repr(str(data))
            else:
                display = repr(data) # introduces character escapes in Python 2
                if display.startswith('u'): # only for Python 2
                    display=display[1:] # granted, this is an ugly way of doing it, but it produces human readable and valid XML                
            # escape XML entities in attributes
            value = _xml_attr_escape(display)
            line = "%s<%s %stype='%s' value=%s %s>" % (_space, name, 
                                                         show_address, 
                                                         data_type, value, 
                                                         '/' if data_type != 'DD' else '')
        else:
            line = '%s</%s>' % (_space, section_names[-1])
            
        if data_type == 'end': section_names.pop()
        elif data_type == 'DD': 
            section_names.append(name)
            level+=1
        out.append(line)
    return u'\n'.join(out)


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
        
        comment = '' if data_type != 'end' else '<-'.join(DD_names[-1::-1])
        if data_type == 'end': DD_names.pop()
        
        line = u' '.join([u'%.6x:'%address, _space+name, '[%s]'%data_type, repr(data), comment])
            
        if data_type == 'DD': 
            DD_names.append(name)
            level+=1
        out.append(line)
    return u'\n'.join(out)
