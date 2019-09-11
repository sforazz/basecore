import nipype
import glob
import os
from nipype.interfaces import fsl
from nipype.interfaces.ants import ApplyTransforms
from basecore.interfaces.ants import AntsRegSyn, ResampleImage
from nipype.interfaces.utility import Merge, Split


contrasts = ['T1KM']
base_dir = '/nfs/extra_hd/Cinderella_FU_bet/preprocessing/T1KM/'
cache_dir = '/mnt/hdd/seg_reg_cache'
result_dir = '/mnt/hdd/Cinderella_FU_seg_reg2'
sub_list = [os.path.join(base_dir,x) for x in sorted(os.listdir(base_dir)) if os.path.isdir(os.path.join(base_dir,x))]
sub_list = [x for x in sub_list if x.split('/')[-1] not in ['40E3HNPG', '0ELEU3HF', '5AKETE27', '5XD8G652',
                                                            '80H0W2L7', 'CTLH9GXW', 'E4A57N7T', 'E9PWKTRN']]
# sub_list = [x for x in sub_list if x.split('/')[-1] in ['40E3HNPG', '']]

for n, sub in enumerate(sub_list):
    for contrast in contrasts:
        sub_name = sub.split('/')[-1]
        sessions = [x.split('/')[-1] for x in sorted(glob.glob(os.path.join(sub, '*'))) if 'reference_tp' not in x]
        ref_tp = [x.split('/')[-1] for x in sorted(glob.glob(os.path.join(sub, '*'))) if 'reference_tp' in x][0]
        datasource = nipype.Node(
            interface=nipype.DataGrabber(infields=['contrasts', 'sub_id', 'sessions', 'ref_tp'],
                                         outfields=['reference', 'to_reg']), name='datasource')  
        datasource.inputs.base_directory = base_dir
        datasource.inputs.template = '*'
        datasource.inputs.sort_filelist = True
        datasource.inputs.field_template = dict(reference='%s/%s/%s_bet.nii.gz',
                                                to_reg='%s/%s/%s_bet.nii.gz')
        datasource.inputs.template_args = dict(to_reg=[['sub_id', 'sessions', 'contrasts']],
                                               reference=[['sub_id', 'ref_tp', 'contrasts']])
        datasource.inputs.raise_on_empty = False
        datasource.inputs.contrasts = contrast
        datasource.inputs.sub_id = sub.split('/')[-1]
        datasource.inputs.sessions = sessions
        datasource.inputs.ref_tp = ref_tp
        
        rs_ref = nipype.Node(interface=ResampleImage(), name='rs_ref')
        rs_ref.inputs.new_size = '1x1x1'
        rs_ref.inputs.mode = 0
        rs_ref.inputs.interpolation = 0
        rs_ref.inputs.dimensions = 3

        merge_1 = nipype.MapNode(interface=Merge(2), iterfield=['in1', 'in2'], name='merge_1')
        merge_1.inputs.ravel_inputs = True
        
        split_1 = nipype.MapNode(interface=Split(), iterfield=['inlist'], name='split_1')
        split_1.inputs.squeeze = True
        split_1.inputs.splits = [1, 2]

        fast_1 = nipype.MapNode(interface=fsl.FAST(), iterfield=['in_files'], name='fast_1')
        fast_1.inputs.img_type = 1
        fast_1.inputs.segments = True
        
        fast_ref = nipype.Node(interface=fsl.FAST(), name='fast_ref')
        fast_ref.inputs.img_type = 1
        fast_ref.inputs.segments = True
        
        reg = nipype.MapNode(interface=AntsRegSyn(), iterfield=['input_file'], name='ants_reg')
        reg.inputs.transformation = 's'
        reg.inputs.num_dimensions = 3
        reg.inputs.num_threads = 4
        
        apply_ts = nipype.MapNode(interface=ApplyTransforms(),
                                  iterfield=['input_image', 'transforms'], name='apply_ts')
        apply_ts.inputs.dimension = 3
        apply_ts.inputs.interpolation = 'NearestNeighbor'
        
        datasink = nipype.Node(nipype.DataSink(base_directory=result_dir), "datasink")
        substitutions = [('contrast', contrast), ('sub', sub.split('/')[-1]), ('session', ref_tp+'_reference_tp'),
                         ('seg_0.', 'CSF.'), ('seg_0_trans', 'CSF_mapped'), ('seg_1', 'GM'), ('seg_2', 'WM'),
                         ('antsreg0GenericAffine.mat', 'Affine_mat.mat'), ('antsreg1Warp', 'Warp_field'),
                         ('antsreg1InverseWarp', 'Inverse_warp_field'),
                         ('antsregWarped', '{}_bet_mapped'.format(contrast))]
        for i, session in enumerate(sessions):
            substitutions += [('_fast_1{}/'.format(i), session+'/')]
            substitutions += [('_ants_reg{}/'.format(i), session+'/')]
            substitutions += [('_apply_ts{}/'.format(i), session+'/')]
        datasink.inputs.substitutions =substitutions
        
        workflow = nipype.Workflow('seg_reg_workflow',
                                   base_dir=os.path.join(cache_dir, sub_name+'_'+contrast))
        workflow.connect(datasource, 'reference', rs_ref, 'in_file')
        workflow.connect(datasource, 'to_reg', fast_1, 'in_files')
        workflow.connect(datasource, 'to_reg', reg, 'input_file')
        workflow.connect(rs_ref, 'out_file', fast_ref, 'in_files')
        workflow.connect(rs_ref, 'out_file', reg, 'ref_file')
        workflow.connect(fast_1, 'tissue_class_files', datasink, 'seg_reg_preprocessing.contrast.sub.@fast_file')
        workflow.connect(fast_ref, 'tissue_class_files', datasink,
                         'seg_reg_preprocessing.contrast.sub.reference_tp.@fast_ref_file')
        workflow.connect(fast_1, 'tissue_class_files', split_1, 'inlist')
        workflow.connect(reg, 'warp_file', merge_1, 'in1')
        workflow.connect(reg, 'regmat', merge_1, 'in2')
        workflow.connect(merge_1, 'out', apply_ts, 'transforms')
        workflow.connect(split_1, 'out1', apply_ts, 'input_image')
        workflow.connect(rs_ref, 'out_file', apply_ts, 'reference_image')
        workflow.connect(reg, 'reg_file', datasink, 'seg_reg_preprocessing.contrast.sub.@reg_image')
        workflow.connect(reg, 'regmat', datasink, 'seg_reg_preprocessing.contrast.sub.@affine_mat')
        workflow.connect(reg, 'warp_file', datasink, 'seg_reg_preprocessing.contrast.sub.@warp_file')
        workflow.connect(reg, 'inv_warp', datasink, 'seg_reg_preprocessing.contrast.sub.@inverse_warp')
        workflow.connect(apply_ts, 'output_image', datasink, 'seg_reg_preprocessing.contrast.sub.@warped_fast')
        workflow.connect(rs_ref, 'out_file', datasink, 'seg_reg_preprocessing.contrast.sub.reference_tp.@reference')
        
#         workflow.run()
        workflow.run('MultiProc', plugin_args={'n_procs': 6})

print('Done!')
