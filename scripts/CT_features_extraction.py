import os
import nipype
from basecore.interfaces.mitk import Voxelizer
from basecore.interfaces.pyradiomics import FeatureExtraction
import re
import pydicom as pd
import glob


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
    for root, _, files in os.walk(basedir):
        for name in files:
            if 'RTCT.nii.gz' in name and os.path.isdir(os.path.join(root, 'RTSTRUCT')):
                rts = glob.glob(os.path.join(root, 'RTSTRUCT', '1-*', '*.dcm'))[0]
                matching = check_rts(rts, regex)
                if matching:
                    sub_name = root.split('/')[-2]
                    current_tp = root.split('/')[-1]
                    data.append(os.path.join(sub_name, current_tp))
    return data


def check_rts(rts, regex):

    ds = pd.read_file(rts)
    reg_expression = re.compile(regex)
    matching_regex = False
    for i in range(len(ds.StructureSetROISequence)):
        match = reg_expression.match(ds.StructureSetROISequence[i].ROIName)
        if match is not None:
            matching_regex = True
            break
    return matching_regex


base_dir = '/mnt/sdb/anal_coverted_dose'
cache_dir = '/mnt/sdb/anal_CA_features_cache'
result_dir = '/mnt/sdb/anal_CA_features'
regex = '.*(G|g)(T|t)(V|v).*|.*PTV.*|.*(B|b)osst.*|.*CTV.*'

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

features = nipype.MapNode(interface=FeatureExtraction(),
                          iterfield=['input_image', 'rois'],
                          name='features_extraction')
features.inputs.parameter_file = '/home/fsforazz/Downloads/Params.yaml'

datasink = nipype.Node(nipype.DataSink(base_directory=result_dir), "datasink")
substitutions = []
for i, sub in enumerate(sub_list):
    substitutions += [('_features_extraction{}/'.format(i), sub+'/')]
    substitutions += [('_voxelizer{}/'.format(i), sub+'/')]
datasink.inputs.substitutions =substitutions

workflow = nipype.Workflow('features_extraction_workflow', base_dir=cache_dir)
workflow.connect(datasource, 'ct', voxelizer, 'reference')
workflow.connect(datasource, 'rtstruct', voxelizer, 'struct_file')
workflow.connect(datasource, 'ct', features, 'input_image')
workflow.connect(voxelizer, 'out_files', features, 'rois')
workflow.connect(features, 'feature_files', datasink, 'features_extraction.@csv_file')
workflow.connect(voxelizer, 'out_files', datasink, 'features_extraction.@masks')

workflow.run()
# workflow.run('MultiProc', plugin_args={'n_procs': 4})
print('Done!')

