"Script to run HD-BET on sorted data"
import glob
import os
from nipype.interfaces import fsl
import nipype
from basecore.interfaces.mic import HDBet


def find_subs(basedir):
    "Function to find the subjects with at least two time-points"
    subs = sorted(glob.glob(os.path.join(basedir, '*')))
    ct_images = []
    to_exclude = []

    for subject in subs:
        try:
            ct_im = glob.glob(subject+'/*/CT.nii.gz')
            ct_images.append(ct_im[0].split('/')[-2])
            if len(ct_im) > 1:
                print('Subject {0} has {1} CT images'.format(subject, len(ct_im)))
                to_exclude.append(subject)
                ct_images.remove(ct_im[0].split('/')[-2])
        except IndexError:
            print('No CT for subject: {}'.format(subject))
            to_exclude.append(subject)
    for fname in to_exclude:
        subs.remove(fname)

    return ct_images, subs


CONTRASTS = ['T1KM']
BASE_DIR = '/mnt/sdb/Cinderella_FU_sorted_all/'
CACHE_DIR = '/mnt/sdb/bet_cache'
RESULT_DIR = '/mnt/sdb/Cinderella_FU_bet'
CTS, SUB_LIST = find_subs(BASE_DIR)

for n, sub in enumerate(SUB_LIST):
    for contrast in CONTRASTS:
        sub_name = sub.split('/')[-1]
        sessions = [x for x in sorted(glob.glob(os.path.join(sub, '*')))]
        ct_tp = [i for i, s in enumerate(sessions) if CTS[n] in s]
        sessions = [x for x in sessions[ct_tp[0]+1:] if glob.glob(x+'/{}.nii.gz'.format(contrast))]
        if len(sessions) > 1:
            ref_tp = sessions[0].split('/')[-1]
            sessions.remove(sessions[0])
            sessions = [x.split('/')[-1] for x in sessions]
            datasource = nipype.Node(
                interface=nipype.DataGrabber(infields=['contrasts', 'sub_id', 'sessions', 'ref_tp'],
                                             outfields=['reference', 'to_reg']), name='datasource')
            datasource.inputs.base_directory = BASE_DIR
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

            datasink = nipype.Node(nipype.DataSink(base_directory=RESULT_DIR), "datasink")
            substitutions = [('contrast', contrast), ('sub', sub.split('/')[-1]),
                             ('session', ref_tp+'_reference_tp')]
            for i, session in enumerate(sessions):
                substitutions += [('_bet_1{}/'.format(i), session+'/')]
            datasink.inputs.substitutions =substitutions

            workflow = nipype.Workflow('temporal_analysis_preproc_workflow',
                                       base_dir=os.path.join(CACHE_DIR, sub_name+'_'+contrast))
            workflow.connect(datasource, 'reference', rf_ref, 'in_file')
            workflow.connect(datasource, 'to_reg', rf_1, 'in_file')
            workflow.connect(rf_1, 'out_roi', bet_1, 'input_file')
            workflow.connect(rf_ref, 'out_roi', bet_ref, 'input_file')
            workflow.connect(bet_1, 'out_file', datasink, 'preprocessing.contrast.sub.@bet_file')
            workflow.connect(bet_1, 'out_mask', datasink, 'preprocessing.contrast.sub.@bet_mask')
            workflow.connect(bet_ref, 'out_file', datasink,
                             'preprocessing.contrast.sub.session.@bet_ref_file')
            workflow.connect(bet_ref, 'out_mask', datasink,
                             'preprocessing.contrast.sub.session.@bet_ref_mask')

            workflow.run()
#             workflow.run('MultiProc', plugin_args={'n_procs': 4})

print('Done!')
