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
# output as XML file
with io.open(xml_output_file, 'wt', encoding='utf-8') as f:
    f.write( zs2decode.util.chunks_to_XML(chunks) )
