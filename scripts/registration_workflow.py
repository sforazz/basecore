import nipype
from core.interfaces.ants import AntsRegSyn
from _operator import sub
import glob
import os


contrasts = ['T1', 'T2', 'T1KM', 'ADC', 'SWI', 'FLAIR', 'T2KM']
base_dir = '/mnt/sdb/Cinderella_sorted_nipype/'
cache_dir = '/mnt/sdb/nipype_reg_cache'
result_dir = '/mnt/sdb/Cinderella_reg'
sub_list = [x for x in sorted(os.listdir(base_dir)) if os.path.isdir(os.path.join(base_dir,x))
            and glob.glob(os.path.join(base_dir,x,'*/CT.nii.gz'))]

for sub in sub_list:
    for contrast in contrasts:
        sessions = [x.split('/')[-2] for x in sorted(glob.glob(os.path.join(base_dir, sub, '*', '{}.nii.gz'.format(contrast))))]
        ref_tp = [x.split('/')[-2] for x in sorted(glob.glob(os.path.join(base_dir, sub, '*', 'CT.nii.gz')))]
        if sessions and ref_tp:
            ref_tp = ref_tp[-1]
            datasource = nipype.Node(
                interface=nipype.DataGrabber(infields=['contrasts', 'sub_id', 'sessions', 'ref_tp'],
                                             outfields=['reference', 'to_reg']), name='datasource')  
            datasource.inputs.base_directory = base_dir
            datasource.inputs.template = '*'
            datasource.inputs.sort_filelist = True
            datasource.inputs.field_template = dict(reference='%s/%s/%sCT.nii.gz',
                                                    to_reg='%s/%s/%s.nii.gz')
            datasource.inputs.template_args = dict(to_reg=[['sub_id', 'sessions', 'contrasts']],
                                                   reference=[['sub_id', 'ref_tp', '']])
            datasource.inputs.raise_on_empty = False
            datasource.inputs.contrasts = contrast
            datasource.inputs.sub_id = sub
            datasource.inputs.sessions = sessions
            datasource.inputs.ref_tp = ref_tp
            
            
            reg = nipype.MapNode(interface=AntsRegSyn(), iterfield=['input_file'], name='ants_reg')
            reg.inputs.transformation = 'r'
            reg.inputs.num_dimensions = 3
            reg.inputs.num_threads = 6
            
            datasink = nipype.Node(nipype.DataSink(base_directory=result_dir), "datasink")
            substitutions = [('contrast', contrast), ('sub', sub)]
            for i, session in enumerate(sessions):
                substitutions += [('_ants_reg{}'.format(i), session)]
            datasink.inputs.substitutions =substitutions
            
            workflow = nipype.Workflow('registration_workflow', base_dir=cache_dir)
            workflow.connect(datasource, 'reference', reg, 'ref_file')
            workflow.connect(datasource, 'to_reg', reg, 'input_file')
            workflow.connect(reg, 'reg_file', datasink, 'registration.contrast.sub.@reg_image')
            workflow.connect(reg, 'regmat', datasink, 'registration.contrast.sub.@affine_mat')
            workflow.connect(datasource, 'reference', datasink, 'registration.contrast.sub.@reference')
            
            workflow.run()
            # workflow.run('MultiProc', plugin_args={'n_procs': 4})

print('Done!')
