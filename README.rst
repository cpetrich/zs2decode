zs2decode
#########

zs2decode is a Python (2.7, 3.3, 3.4, 3.5) implementation of a
decoder for Zwick ``zs2`` files.

``zs2`` files contain measurements and meta data. zs2decode is able to
convert these files to XML for further processing. 
The following script converts a ``zs2`` file into XML::

    import io
    import zs2decode.parser
    import zs2decode.util

    zs2_file_name = 'my_data_file.zs2'
    xml_output_file = 'my_data_file.xml'

    # load and decompress file
    data_stream = zs2decode.parser.load(zs2_file_name)
    # separate binary data stream into chunks
    raw_chunks = zs2decode.parser.data_stream_to_chunks(data_stream)
    # convert binary chunk data into lists of Python objects
    chunks = zs2decode.parser.parse_chunks(raw_chunks)
    # output as xml file
    with io.open(xml_output_file, 'wt', encoding='utf-8') as f:
        f.write( zs2decode.util.chunks_to_XML(chunks) )


Documentation is available at `<http://zs2decode.readthedocs.org/>`_
and source code at `<https://github.com/cpetrich/zs2decode.git>`_.
