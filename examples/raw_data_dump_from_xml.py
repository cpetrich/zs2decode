"""Extract zs2 time series data from XML file."""

# written by Chris Petrich, 2015-2017
# License: MIT

import xml.etree.ElementTree as ET
import ast

fn_in = 'my_data_file.xml'
fn_out_pattern = 'sample_data_%s.txt'

print('Reading XML')
with open(fn_in,'rt') as f:
    data = f.read()
print('Parsing XML')
root = ET.fromstring(data)
print('Findig data')

def _get_list_elements(root, path, tag='Elem'):
    return [element for element in root.findall(path) if element.tag.startswith(tag)]

def _get_type(root, path):
    return root.find(path).attrib['type']

def _get_value(root, path):
    element = root.find(path)
    if element is None:
        raise ValueError('No path %r' % path)
    string = element.attrib['value']
    dtype=_get_type(root, path)
    if dtype in ('AA','DD'): return u'%s' % string
    if dtype.startswith('EE11'):
        # there seems to have been something gone wrong with xml entity replacement
        string = string.replace("\\'","\'")
    return ast.literal_eval(string)


if __name__=='__main__':
    # get a mapping between channel number IDs and clear-text names
    channel_names = {}
    xml_channels = _get_list_elements(root, './Body/batch/SeriesDef/TestTaskDefs/Elem0/ChannelManager/ChannelManager/')
    for xml_channel in xml_channels:
        ID = _get_value(xml_channel, './ID')
        name = _get_value(xml_channel, './Name/Text')
        channel_names[ID]=name

    if True:
        # check if this file uses "short" paths (i.e., the original implementation)
        xml_data = root.find('./Body/batch/Series')
        xml_samples = _get_list_elements(xml_data, './SeriesElements/')
        try:
            IndexTimeChannel = _get_value(xml_samples[0], './SeriesElements/Elem0/RealTimeCapture/Trs/SingleGroupDataBlock/IndexTimeChannel')
        except ValueError:
            IndexTimeChannel = None

        is_short = IndexTimeChannel is not None

    if is_short:
        xml_data = root.find('./Body/batch/Series')
        data={}
        xml_samples = _get_list_elements(xml_data, './SeriesElements/')
        for sample_idx, xml_sample in enumerate(xml_samples):
            # extract data for each sample contained in the file:
            # get sample parameters, we'll only use this to get the sample name (ID 48154)
            param_data = {}
            xml_parameters = _get_list_elements(xml_sample, './EvalContext/ParamContext/ParameterListe/')
            sample_name = 'no-name-defined-%i' % sample_idx
            for xml_parameter in xml_parameters:
                ID = _get_value(xml_parameter, './ID')
                if ID == 48154:
                    new_sample_name = _get_value(xml_parameter, './QS_TextPar')[0]
                    sample_name = new_sample_name if new_sample_name != '' else sample_name
                    break
            # now get the data
            channel_data = {}
            # nesting is significantly deeper in some files
            IndexTimeChannel = _get_value(xml_sample, './SeriesElements/Elem0/RealTimeCapture/Trs/SingleGroupDataBlock/IndexTimeChannel')
            time_channel_ID = None

            xml_channels = _get_list_elements(xml_sample, './SeriesElements/Elem0/RealTimeCapture/Trs/SingleGroupDataBlock/DataChannels/')
            for idx, xml_channel in enumerate(xml_channels):
                data_array = _get_value(xml_channel, './DataArray')
                ID = _get_value(xml_channel, './TrsChannelId')
                channel_data[ID]={'data':data_array,
                                  'name': channel_names[ID]}

                if idx == IndexTimeChannel: time_channel_ID = ID

            # collect in a dict
            sample_data = {}
            sample_data['channel_data']=channel_data
            sample_data['time_channel_ID']=time_channel_ID
            sample_data['sample_name']=sample_name

            data[sample_name]=sample_data

    else:
        # this is more general but doesn't extract the names
        #    of the respective data series
        data={}
        xml_SingleGroupDataBlocks = root.findall('.//IndexTimeChannel/..')
        for sample_idx, xml_sample in enumerate(xml_SingleGroupDataBlocks):

            # todo: find names associated with data series
            sample_name = 'data_group-%i' % sample_idx

            # now get the data
            channel_data = {}

            IndexTimeChannel = _get_value(xml_sample, './IndexTimeChannel')
            time_channel_ID = None

            xml_channels = _get_list_elements(xml_sample, './DataChannels/')
            for idx, xml_channel in enumerate(xml_channels):
                data_array = _get_value(xml_channel, './DataArray')
                ID = _get_value(xml_channel, './TrsChannelId')
                channel_data[ID]={'data':data_array,
                                  'name': channel_names[ID]}

                if idx == IndexTimeChannel: time_channel_ID = ID

            # collect in a dict
            sample_data = {}
            sample_data['channel_data']=channel_data
            sample_data['time_channel_ID']=time_channel_ID
            sample_data['sample_name']=sample_name

            data[sample_name]=sample_data


    # write one file per sample
    sample_names = list(data.keys())
    sample_names.sort()
    for sample_name in sample_names:
        if sample_name =='': continue
        print(sample_name)
        channels = list(data[sample_name]['channel_data'].keys())
        if len(channels) == 0:
            print('  no data channels --> skipping')
            continue
        channels.sort()
        channels.remove(data[sample_name]['time_channel_ID'])
        channels.insert(0,data[sample_name]['time_channel_ID'])

        N=len(data[sample_name]['channel_data'][data[sample_name]['time_channel_ID']]['data'])

        fn_out = fn_out_pattern % sample_name
        out = []
        line = '\t'.join(['"'+str(channel_names[channel])+'"' for channel in channels])
        out.append(line)
        line = '\t'.join([str(channel) for channel in channels])
        out.append(line)
        for row in range(N):
            line=[]
            for channel in channels:
                line.append('%.9g' % data[sample_name]['channel_data'][channel]['data'][row])
            out.append('\t'.join(line))

        with open(fn_out, 'wt') as f:
            f.write('\n'.join(out))

