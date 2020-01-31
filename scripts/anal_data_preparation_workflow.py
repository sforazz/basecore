from basecore.interfaces.utils import DicomCheck, ConversionCheck
import os
import nipype
import nipype.interfaces.utility as util
from nipype.interfaces.dcm2nii import Dcm2niix
from basecore.interfaces.plastimatch import DoseConverter


rt_files = ['RTSTRUCT', 'RTPLAN']
ct_files = ['RTCT']
base_dir = '/mnt/sdb/anal-ca_SORTED_RT/'
result_dir = '/mnt/sdb/anal_coverted_dose/'
cache_dir = '/mnt/sdb/anal_converted_cache'

if not os.path.isdir(result_dir):
    os.mkdir(result_dir)

datasource_ct = nipype.Node(
    interface=nipype.DataGrabber(infields=['name'], outfields=['directory']),
    name='datasource_ct')
datasource_ct.inputs.base_directory = base_dir
datasource_ct.inputs.template = '*'
datasource_ct.inputs.sort_filelist = True
datasource_ct.inputs.field_template = dict(directory='*/*/%s/1-*')
datasource_ct.inputs.name = 'RTCT'

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
datasource_rt.inputs.field_template = dict(directory='*/*/%s')

datasource_dose = nipype.Node(
    interface=nipype.DataGrabber(infields=['name'], outfields=['directory']),
    name='datasource_dose')
datasource_dose.inputs.base_directory = base_dir
datasource_dose.inputs.template = '*'
datasource_dose.inputs.sort_filelist = True
datasource_dose.inputs.field_template = dict(directory='*/*/%s/1-*')
datasource_dose.inputs.name = 'RTDOSE'

dc_rt = nipype.MapNode(interface=DicomCheck(), iterfield=['dicom_dir'], name='dc_rt')
dc_rt.inputs.working_dir = result_dir

dc_ct = nipype.MapNode(interface=DicomCheck(), iterfield=['dicom_dir'], name='dc_ct')
dc_ct.inputs.working_dir = result_dir

dc_dose = nipype.MapNode(interface=DicomCheck(), iterfield=['dicom_dir'], name='dc_dose')
dc_dose.inputs.working_dir = result_dir

converter_ct = nipype.MapNode(interface=Dcm2niix(),
                           iterfield=['source_dir', 'out_filename', 'output_dir'],
                           name='converter_ct')
converter_ct.inputs.compress = 'y'
converter_ct.inputs.philips_float = False
converter_ct.inputs.merge_imgs = True

converter_dose = nipype.MapNode(interface=DoseConverter(),
                                iterfield=['input_dose', 'out_name'],
                                name='coverter_dose')

check_ct = nipype.MapNode(interface=ConversionCheck(),
                          iterfield=['in_file', 'file_name'],
                          name='check_conversion_ct')

workflow = nipype.Workflow('data_preparation_workflow', base_dir=cache_dir)
workflow.connect(inputnode_rt, 'rt_files', datasource_rt, 'rt_files')
workflow.connect(datasource_rt, 'directory', dc_rt, 'dicom_dir')
workflow.connect(datasource_ct, 'directory', dc_ct, 'dicom_dir')
workflow.connect(datasource_dose, 'directory', dc_dose, 'dicom_dir')
workflow.connect(dc_dose, 'dose_file', converter_dose, 'input_dose')
workflow.connect(dc_dose, 'dose_output', converter_dose, 'out_name')
workflow.connect(dc_ct, 'outdir', converter_ct, 'source_dir')
workflow.connect(dc_ct, 'scan_name', converter_ct, 'out_filename')
workflow.connect(dc_ct, 'base_dir', converter_ct, 'output_dir')
workflow.connect(dc_ct, 'scan_name', check_ct, 'file_name')
workflow.connect(converter_ct, 'converted_files', check_ct, 'in_file')

# workflow.run()
workflow.run('MultiProc', plugin_args={'n_procs': 8})

print('Done!')
