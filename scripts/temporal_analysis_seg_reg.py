import nipype
from _operator import sub
import glob
import os
from nipype.interfaces import fsl
from basecore.interfaces.ants import AntsRegSyn


contrasts = ['T1KM']
base_dir = '/mnt/sdb/test_temp_ana/'
cache_dir = '/mnt/sdb/temporal_analysis_seg_reg_cache'
result_dir = '/mnt/sdb/Cinderella_FU_temporal_analysis_seg_reg'
sub_list = sub_list = [os.path.join(base_dir,x) for x in sorted(os.listdir(base_dir)) if os.path.isdir(os.path.join(base_dir,x))]

for n, sub in enumerate(sub_list):
    for contrast in contrasts:
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
        
        fast_1 = nipype.MapNode(interface=fsl.FAST(), iterfield=['in_files'], name='fast_1')
        fast_1.inputs.img_type = 1
        fast_1.inputs.segments = True
        
        fast_ref = nipype.Node(interface=fsl.FAST(), name='fast_ref')
        fast_ref.inputs.img_type = 1
        fast_ref.inputs.segments = True
        
        reg = nipype.MapNode(interface=AntsRegSyn(), iterfield=['input_file'], name='ants_reg')
        reg.inputs.transformation = 'r'
        reg.inputs.num_dimensions = 3
        reg.inputs.num_threads = 1
        
        datasink = nipype.Node(nipype.DataSink(base_directory=result_dir), "datasink")
        substitutions = [('contrast', contrast), ('sub', sub.split('/')[-1]), ('session', ref_tp+'_reference_tp')]
        for i, session in enumerate(sessions):
            substitutions += [('_fast_1{}/'.format(i), session+'/')]
            substitutions += [('_ants_reg{}/'.format(i), session+'/')]
        datasink.inputs.substitutions =substitutions
        
        workflow = nipype.Workflow('temporal_analysis_preproc_workflow', base_dir=cache_dir)
        workflow.connect(datasource, 'reference', fast_ref, 'in_files')
        workflow.connect(datasource, 'to_reg', fast_1, 'in_files')
        workflow.connect(datasource, 'reference', reg, 'ref_file')
        workflow.connect(datasource, 'to_reg', reg, 'input_file')
        workflow.connect(fast_1, 'tissue_class_files', datasink, 'preprocessing.contrast.sub.@fast_file')
        workflow.connect(fast_ref, 'tissue_class_files', datasink, 'preprocessing.contrast.sub.@fast_ref_file')
        workflow.connect(reg, 'reg_file', datasink, 'registration.contrast.sub.@reg_image')
        workflow.connect(reg, 'regmat', datasink, 'registration.contrast.sub.@affine_mat')
        workflow.connect(datasource, 'reference', datasink, 'registration.contrast.sub.@reference')
        
        workflow.run()
#             workflow.run('MultiProc', plugin_args={'n_procs': 4})

print('Done!')
