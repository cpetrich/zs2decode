zs2decode
#########

.. image:: https://travis-ci.org/cpetrich/zs2decode.svg?branch=master
    :target: https://travis-ci.org/cpetrich/zs2decode

zs2decode is a Python (2.7, 3.3, 3.4, 3.5, 3.6) implementation of a
decoder for Zwick ``zs2`` files.

``zs2`` files contain measurements and meta data. zs2decode is able to
parse these files. It contains support functions to output the result as
text file or XML for further processing.
The following script converts a ``zs2`` file into XML::

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
    # output as text file
    with open(xml_dump_file, 'wb') as f:
        f.write( zs2decode.util.chunks_to_XML(chunks) )


An example script to extract measurement time series from the XML is
provided in the ``examples`` folder.

Documentation is available at `<http://zs2decode.readthedocs.org/>`_
and source code at `<https://github.com/cpetrich/zs2decode.git>`_.
