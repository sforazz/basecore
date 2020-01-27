import glob
import os
import nipype
from basecore.interfaces.mitk import Voxelizer, CLGlobalFeatures
from nipype.interfaces.utility import Select

tgggggg
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

base_dir = '/mnt/sdb/anal_sorted/'
cache_dir = '/mnt/sdb/feat_cache1'
result_dir = '/mnt/sdb/anal_fe1'
sub_list = creste_sub_list(base_dir)

datasource = nipype.Node(
    interface=nipype.DataGrabber(infields=['sub_id'],
                                 outfields=['ct', 'rtstruct']), name='datasource')
datasource.inputs.base_directory = base_dir
datasource.inputs.template = '*'
datasource.inputs.sort_filelist = True
datasource.inputs.field_template = dict(ct='%s/CT.nii.gz',
                                        rtstruct='%s/RTSTRUCT/*.dcm')
datasource.inputs.template_args = dict(ct=[['sub_id']],
                                       rtstruct=[['sub_id']])
datasource.inputs.raise_on_empty = False
datasource.inputs.sub_id = sub_list

voxelizer = nipype.MapNode(interface=Voxelizer(), iterfield=['reference', 'struct_file'],
                           name='voxelizer')
voxelizer.inputs.regular_expression = '.*PTV.*'
voxelizer.inputs.multi_structs = True
voxelizer.inputs.binarization = True

select = nipype.MapNode(interface=Select(), iterfield=['inlist'], name='select')
select.inputs.index = 0

features = nipype.MapNode(interface=CLGlobalFeatures(), iterfield=['in_file', 'mask'],
                           name='features_extraction')
features.inputs.first_order = True
features.inputs.cooccurence = True
features.inputs.run_length = True
features.inputs.int_vol_hist = True
features.inputs.local_intensity = True
features.inputs.volume = True
features.inputs.id = True
# features.inputs.ngld = True
features.inputs.ngtd = True
features.inputs.use_header = True

datasink = nipype.Node(nipype.DataSink(base_directory=result_dir), "datasink")
substitutions = []
for i, sub in enumerate(sub_list):
    substitutions += [('_features_extraction{}/'.format(i), sub+'/')]
datasink.inputs.substitutions =substitutions

workflow = nipype.Workflow('features_extraction_workflow', base_dir=cache_dir)
workflow.connect(datasource, 'ct', voxelizer, 'reference')
workflow.connect(datasource, 'rtstruct', voxelizer, 'struct_file')
workflow.connect(datasource, 'ct', features, 'in_file')
workflow.connect(voxelizer, 'out_files', select, 'inlist')
workflow.connect(select, 'out', features, 'mask')
workflow.connect(features, 'out_file', datasink, 'features_extraction.@csv_file')

workflow.run()
# workflow.run('MultiProc', plugin_args={'n_procs': 4})
print('Done!')

