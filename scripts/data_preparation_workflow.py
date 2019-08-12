from core.interfaces.utils import DicomCheck, ConversionCheck
import nipype
import nipype.interfaces.utility as util
from nipype.interfaces.dcm2nii import Dcm2niix


contrasts = ['T1KM', 'FLAIR', 'CT', 'ADC', 'T1', 'SWI', 'T2', 'T2KM']
rt_files = ['RTSTRUCT', 'RTDOSE', 'RTPLAN']
base_dir = '/media/fsforazz/portable_hdd/data_sorted/test/'
result_dir = '/mnt/sdb/Cinderella_FU_sorted_all_test2/'
cache_dir = '/mnt/sdb/sorted_data/sorting_cache2/'

inputnode = nipype.Node(
    interface=util.IdentityInterface(fields=['contrasts']),
    name='inputnode')
inputnode.iterables = ('contrasts', contrasts)

datasource = nipype.Node(
    interface=nipype.DataGrabber(infields=['contrasts'], outfields=['directory']),
    name='datasource')  
datasource.inputs.base_directory = base_dir
datasource.inputs.template = '*'
datasource.inputs.sort_filelist = True
datasource.inputs.field_template = dict(directory='*/*/%s/1-*')

inputnode_rt = nipype.Node(
    interface=util.IdentityInterface(fields=['rt_files']),
    name='inputnode_rt')
inputnode_rt.iterables = ('rt_files', rt_files)

datasource_rt = nipype.Node(
    interface=nipype.DataGrabber(infields=['rt_files'], outfields=['directory']),
    name='datasource_rt')  
datasource_rt.inputs.base_directory = base_dir
datasource_rt.inputs.template = '*'
datasource_rt.inputs.sort_filelist = True
datasource_rt.inputs.field_template = dict(directory='*/*/%s/1-*')

dc_rt = nipype.MapNode(interface=DicomCheck(), iterfield=['dicom_dir'], name='dc_rt')
dc_rt.inputs.working_dir = result_dir

dc = nipype.MapNode(interface=DicomCheck(), iterfield=['dicom_dir'], name='dc')
dc.inputs.working_dir = result_dir

converter = nipype.MapNode(interface=Dcm2niix(),
                           iterfield=['source_dir', 'out_filename', 'output_dir'],
                           name='converter')
converter.inputs.compress = 'y'
converter.inputs.philips_float = False
converter.inputs.merge_imgs = True

check = nipype.MapNode(interface=ConversionCheck(),
                       iterfield=['in_file', 'file_name'],
                       name='check_conversion')

workflow = nipype.Workflow('data_preparation_workflow', base_dir=cache_dir)
workflow.connect(inputnode, 'contrasts', datasource, 'contrasts')
workflow.connect(datasource, 'directory', dc, 'dicom_dir')
workflow.connect(inputnode_rt, 'rt_files', datasource_rt, 'rt_files')
workflow.connect(datasource_rt, 'directory', dc_rt, 'dicom_dir')
workflow.connect(dc, 'outdir', converter, 'source_dir')
workflow.connect(dc, 'scan_name', converter, 'out_filename')
workflow.connect(dc, 'base_dir', converter, 'output_dir')
workflow.connect(dc, 'scan_name', check, 'file_name')
workflow.connect(converter, 'converted_files', check, 'in_file')

# workflow.run()
workflow.run('MultiProc', plugin_args={'n_procs': 8})

print('Done!')
