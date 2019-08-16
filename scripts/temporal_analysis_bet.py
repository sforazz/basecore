import nipype
from basecore.interfaces.mic import HDBet
from _operator import sub
import glob
import os
from nipype.interfaces import fsl


def find_subs(basedir):

    subs = sorted(glob.glob(os.path.join(basedir, '*')))
    cts = []
    to_exclude = []

    for sub in subs:
        try: 
            ct = glob.glob(sub+'/*/CT.nii.gz') 
            cts.append(ct[0].split('/')[-2]) 
            if len(ct) > 1: 
                print('Subject {0} has {1} CT images'.format(sub, len(ct))) 
                to_exclude.append(sub) 
                cts.remove(ct[0].split('/')[-2]) 
        except: 
            print('No CT for subject: {}'.format(sub)) 
            to_exclude.append(sub)
    for s in to_exclude:
        subs.remove(s)

    return cts, subs


contrasts = ['T1KM']
base_dir = '/mnt/sdb/Cinderella_FU_sorted_all/'
cache_dir = '/mnt/sdb/bet_cache'
result_dir = '/mnt/sdb/Cinderella_FU_bet'
cts, sub_list = find_subs(base_dir)

for n, sub in enumerate(sub_list):
    for contrast in contrasts:
        sessions = [x for x in sorted(glob.glob(os.path.join(sub, '*')))]
        ct_tp = [i for i, s in enumerate(sessions) if cts[n] in s]
        sessions = [x for x in sessions[ct_tp[0]+1:] if glob.glob(x+'/{}.nii.gz'.format(contrast))]
        if len(sessions) > 1:
            ref_tp = sessions[0].split('/')[-1]
            sessions.remove(sessions[0])
            sessions = [x.split('/')[-1] for x in sessions]
            datasource = nipype.Node(
                interface=nipype.DataGrabber(infields=['contrasts', 'sub_id', 'sessions', 'ref_tp'],
                                             outfields=['reference', 'to_reg']), name='datasource')  
            datasource.inputs.base_directory = base_dir
            datasource.inputs.template = '*'
            datasource.inputs.sort_filelist = True
            datasource.inputs.field_template = dict(reference='%s/%s/%s.nii.gz',
                                                    to_reg='%s/%s/%s.nii.gz')
            datasource.inputs.template_args = dict(to_reg=[['sub_id', 'sessions', 'contrasts']],
                                                   reference=[['sub_id', 'ref_tp', 'contrasts']])
            datasource.inputs.raise_on_empty = False
            datasource.inputs.contrasts = contrast
            datasource.inputs.sub_id = sub.split('/')[-1]
            datasource.inputs.sessions = sessions
            datasource.inputs.ref_tp = ref_tp
            
            rf_1 = nipype.MapNode(interface=fsl.RobustFOV(), iterfield=['in_file'], name='rf_1')
            rf_ref = nipype.Node(interface=fsl.RobustFOV(), name='rf_ref')

            bet_1 = nipype.MapNode(interface=HDBet(), iterfield=['input_file'], name='bet_1')
            bet_1.inputs.save_mask = 1
            bet_1.inputs.out_file = '{}_bet'.format(contrast)
            bet_ref = nipype.Node(interface=HDBet(), name='bet_ref')
            bet_ref.inputs.save_mask = 1
            bet_ref.inputs.out_file = '{}_bet'.format(contrast)
            
#             fast_1 = nipype.MapNode(interface=fsl.FAST(), iterfield=['in_files'], name='fast_1')
#             fast_1.inputs.img_type = 1
#             fast_1.inputs.segments = True
#             
#             fast_ref = nipype.Node(interface=fsl.FAST(), name='fast_ref')
#             fast_ref.inputs.img_type = 1
#             fast_ref.inputs.segments = True
            
            datasink = nipype.Node(nipype.DataSink(base_directory=result_dir), "datasink")
            substitutions = [('contrast', contrast), ('sub', sub.split('/')[-1]), ('session', ref_tp+'_reference_tp')]
            for i, session in enumerate(sessions):
                substitutions += [('_bet_1{}/'.format(i), session+'/')]
#                 substitutions += [('_fast_1{}/'.format(i), session+'/')]
            datasink.inputs.substitutions =substitutions
            
            workflow = nipype.Workflow('temporal_analysis_preproc_workflow', base_dir=cache_dir)
            workflow.connect(datasource, 'reference', rf_ref, 'in_file')
            workflow.connect(datasource, 'to_reg', rf_1, 'in_file')
            workflow.connect(rf_1, 'out_roi', bet_1, 'input_file')
            workflow.connect(rf_ref, 'out_roi', bet_ref, 'input_file')
            workflow.connect(bet_1, 'out_file', datasink, 'preprocessing.contrast.sub.@bet_file')
            workflow.connect(bet_1, 'out_mask', datasink, 'preprocessing.contrast.sub.@bet_mask')
            workflow.connect(bet_ref, 'out_file', datasink, 'preprocessing.contrast.sub.session.@bet_ref_file')
            workflow.connect(bet_ref, 'out_mask', datasink, 'preprocessing.contrast.sub.session.@bet_ref_mask')
#             workflow.connect(fast_1, 'tissue_class_files', datasink, 'preprocessing.contrast.sub.@fast_file')
#             workflow.connect(fast_ref, 'tissue_class_files', datasink, 'preprocessing.contrast.sub.@fast_ref_file')
            
            workflow.run()
#             workflow.run('MultiProc', plugin_args={'n_procs': 4})

print('Done!')
