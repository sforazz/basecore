import os
import nipype
from basecore.interfaces.mitk import Voxelizer
from basecore.interfaces.pyradiomics import FeatureExtraction
import re
import pydicom as pd
import glob
from basecore.interfaces.utils import CheckRTStructures


def creste_sub_list(basedir):

    processed_subs = []
    data = []
    for root, _, files in os.walk(basedir):
        for name in files:
            if 'CT.nii.gz' in name and os.path.isdir(os.path.join(root, 'RTSTRUCT')):
                sub_name = root.split('/')[-2]
                current_tp = root.split('/')[-1]
                if sub_name not in processed_subs:
                    processed_subs.append(sub_name)
                    data.append(os.path.join(sub_name, current_tp))
                else:
                    previous = [x for x in data if sub_name in x][0]
                    previous_tp = previous.split('/')[-1]
                    if current_tp > previous_tp:
                        data.remove(previous)
                        data.append(os.path.join(sub_name, current_tp))
    return data


def creste_sub_list_anal(basedir, regex):

    data = []
    no_rt = []
    no_match = []
    for root, _, files in os.walk(basedir):
        for name in files:
            if ('RTCT.nii.gz' in name and os.path.isdir(os.path.join(root, 'RTSTRUCT')) and
                    os.path.isfile(os.path.join(root, 'RTDOSE.nii.gz'))):
                sub_name = root.split('/')[-2]
                current_tp = root.split('/')[-1]
                try:
                    rts = glob.glob(os.path.join(root, 'RTSTRUCT', '1-*', '*.dcm'))[0]
                    matching = check_rts(rts, regex)
                    if matching:
                        data.append(os.path.join(sub_name, current_tp))
                    else:
                        no_match.append(os.path.join(sub_name, current_tp))
                except IndexError:
                    print('No RTSTRUCT for {}'.format(root.split('/')[-2]))
                    no_rt.append(os.path.join(sub_name, current_tp))
    return data


def check_rts(rts, regex):

#     ds = pd.read_file(rts)
# #     ds = pd.read_file(rt_dcm)
#     regex_uf8 = re.compile('[^a-zA-Z]')
#     for i in range(len(ds.StructureSetROISequence)):
#         new_roiname=regex_uf8.sub('', ds.StructureSetROISequence[i].ROIName)
#         ds.StructureSetROISequence[i].ROIName = new_roiname
#     ds.save_as(rts)
    ds = pd.read_file(rts)
    reg_expression = re.compile(regex)
    matching_regex = False
    for i in range(len(ds.StructureSetROISequence)):
        match = reg_expression.match(ds.StructureSetROISequence[i].ROIName)
        if match is not None:
            matching_regex = True
            break
    return matching_regex


base_dir = '/mnt/sdb/debugging_workflow/'
cache_dir = '/mnt/sdb/debugging_workflow_cache'
result_dir = '/mnt/sdb/debugging_workflow'
regex = '.*(G|g)(T|t)(V|v).*|.*(P|p)(T|t)(V|v).*|.*(B|b)osst.*|.*(C|c)(T|t)(V|v).*'

sub_list = creste_sub_list_anal(base_dir, regex)

datasource = nipype.Node(
    interface=nipype.DataGrabber(infields=['sub_id'],
                                 outfields=['ct', 'rtstruct', 'rt_dose']), name='datasource')
datasource.inputs.base_directory = base_dir
datasource.inputs.template = '*'
datasource.inputs.sort_filelist = True
datasource.inputs.field_template = dict(ct='%s/RTCT.nii.gz',
                                        rtstruct='%s/RTSTRUCT/1-*/*.dcm',
                                        rt_dose='%s/RTDOSE.nii.gz')
datasource.inputs.template_args = dict(ct=[['sub_id']],
                                       rtstruct=[['sub_id']],
                                       rt_dose=[['sub_id']])
datasource.inputs.raise_on_empty = False
datasource.inputs.sub_id = sub_list

voxelizer = nipype.MapNode(interface=Voxelizer(), iterfield=['reference', 'struct_file'],
                           name='voxelizer')
voxelizer.inputs.regular_expression = regex
voxelizer.inputs.multi_structs = True
voxelizer.inputs.binarization = True
voxelizer.inputs.no_strict_voxelization = True

select = nipype.MapNode(interface=CheckRTStructures(), iterfield=['rois', 'dose_file'],
                        name='select_gtv')
# 
# features = nipype.MapNode(interface=FeatureExtraction(),
#                           iterfield=['input_image', 'rois'],
#                           name='features_extraction')
# features.inputs.parameter_file = '/home/fsforazz/Downloads/Params.yaml'

datasink = nipype.Node(nipype.DataSink(base_directory=result_dir), "datasink")
substitutions = []
for i, sub in enumerate(sub_list):
    substitutions += [('_features_extraction{}/'.format(i), sub+'/')]
    substitutions += [('_select_gtv{}/'.format(i), sub+'/')]
    substitutions += [('_voxelizer{}/'.format(i), sub+'/')]
datasink.inputs.substitutions =substitutions

workflow = nipype.Workflow('features_extraction_workflow', base_dir=cache_dir)
workflow.connect(datasource, 'ct', voxelizer, 'reference')
workflow.connect(datasource, 'rtstruct', voxelizer, 'struct_file')

workflow.connect(voxelizer, 'out_files', select, 'rois')
workflow.connect(datasource, 'rt_dose', select, 'dose_file')
# workflow.connect(datasource, 'ct', features, 'input_image')
# workflow.connect(voxelizer, 'out_files', features, 'rois')
# workflow.connect(features, 'feature_files', datasink, 'features_extraction.@csv_file')
# workflow.connect(voxelizer, 'out_files', datasink, 'features_extraction.@masks')
workflow.connect(select, 'checked_roi', datasink, '@masks')
# workflow = datasink_base(datasink, datasource, workflow, sessions,
#                          reference, t10=t10)

workflow.run()
# workflow.run('MultiProc', plugin_args={'n_procs': 4})
print('Done!')

