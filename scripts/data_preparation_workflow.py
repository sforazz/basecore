from core.interfaces.utils import DicomCheck, ConversionCheck
import nipype
import nipype.interfaces.utility as util
from nipype.interfaces.dcm2nii import Dcm2niix


contrasts = ['CT', 'T1', 'T2', 'T1KM', 'ADC', 'SWI', 'FLAIR', 'T2KM']
base_dir = '/mnt/sdb/sorted_data/Data_cinderella_MR_CLass'
result_dir = '/mnt/sdb/Cinderella_sorted_nipype/'
cache_dir = '/mnt/sdb/sorted_data/sorting_cache/'

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
workflow.connect(dc, 'outdir', converter, 'source_dir')
workflow.connect(dc, 'scan_name', converter, 'out_filename')
workflow.connect(dc, 'base_dir', converter, 'output_dir')
workflow.connect(dc, 'scan_name', check, 'file_name')
workflow.connect(converter, 'converted_files', check, 'in_file')

# workflow.run()
workflow.run('MultiProc', plugin_args={'n_procs': 8})

print('Done!')
