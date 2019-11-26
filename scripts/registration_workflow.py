"Script to run the tumor segmentation using HD-GLIO"
import os
import argparse
import shutil
import nipype
from nipype.interfaces.fsl.maths import ApplyMask
from nipype.interfaces.ants import ApplyTransforms
from nipype.interfaces.utility import Merge
from basecore.interfaces.mic import HDBet
from basecore.interfaces.ants import AntsRegSyn
from scripts.datasource_workflow import gbm_datasource


sequences = ['t1', 'ct1', 't2', 'flair']


def build_registration_workflow(sub_id, datasource, sessions,
                                RESULT_DIR, NIPYPE_CACHE):

    bet = nipype.MapNode(interface=HDBet(), iterfield=['input_file'], name='bet')
    bet.inputs.save_mask = 1
    bet.inputs.out_file = 'T1_bet'

    bet_t10 = nipype.Node(interface=HDBet(), name='t1_0_bet')
    bet_t10.inputs.save_mask = 1
    bet_t10.inputs.out_file = 'T1_0_bet'

    reg2T1 = nipype.MapNode(interface=AntsRegSyn(), iterfield=['input_file'], name='reg2T1')
    reg2T1.inputs.transformation = 's'
    reg2T1.inputs.num_dimensions = 3
    reg2T1.inputs.num_threads = 6

    regT12CT = nipype.MapNode(interface=AntsRegSyn(), iterfield=['input_file'], name='regT12CT')
    regT12CT.inputs.transformation = 'r'
    regT12CT.inputs.num_dimensions = 3
    regT12CT.inputs.num_threads = 4

    reg_nodes = []
    for i in range(3):
        reg = nipype.MapNode(interface=AntsRegSyn(), iterfield=['input_file', 'ref_file'],
                             name='ants_reg{}'.format(i))
        reg.inputs.transformation = 'r'
        reg.inputs.num_dimensions = 3
        reg.inputs.num_threads = 4
        reg.inputs.interpolation = 'BSpline'
        reg_nodes.append(reg)

    apply_mask_nodes = []
    for i in range(3):
        masking = nipype.MapNode(interface=ApplyMask(), iterfield=['in_file', 'mask_file'],
                                 name='masking{}'.format(i))
        apply_mask_nodes.append(masking)

    apply_ts_nodes = []
    for i in range(3):
        apply_ts = nipype.MapNode(interface=ApplyTransforms(),
                                  iterfield=['input_image', 'transforms'],
                                  name='apply_ts{}'.format(i))
        apply_ts_nodes.append(apply_ts)

    apply_ts_t1 = nipype.MapNode(interface=ApplyTransforms(),
                                 iterfield=['input_image', 'transforms'],
                                 name='apply_ts_t1')
    merge_nodes = []
    for i in range(3):
        merge = nipype.MapNode(interface=Merge(4),
                                 iterfield=['in1', 'in2', 'in3', 'in4'],
                                 name='merge{}'.format(i))
        merge.inputs.ravel_inputs = True
        merge_nodes.append(merge)

    merge_ts_t1 = nipype.MapNode(interface=Merge(3),
                                 iterfield=['in1', 'in2', 'in3'],
                                 name='merge_t1')
    merge_ts_t1.inputs.ravel_inputs = True

    # have to create a fake merge of the transformation from t10 to CT in order
    # to have the same number if matrices as input in mapnode
    fake_merge = nipype.Node(interface=Merge(len(sessions)), name='fake_merge')

    datasink = nipype.Node(nipype.DataSink(base_directory=RESULT_DIR), "datasink")
    substitutions = [('T1_bet.nii.gz', 'T1_preproc.nii.gz')]

    substitutions += [('subid', sub_id)]
    for i, session in enumerate(sessions):
        substitutions += [('_bet{}/'.format(i), session+'/')]
        substitutions += [('_masking0{}/antsregWarped_masked.nii.gz'.format(i),
                           session+'/'+'CT1_preproc.nii.gz')]
        substitutions += [('_masking1{}/antsregWarped_masked.nii.gz'.format(i),
                           session+'/'+'T2_preproc.nii.gz')]
        substitutions += [('_masking2{}/antsregWarped_masked.nii.gz'.format(i),
                           session+'/'+'FLAIR_preproc.nii.gz')]
        substitutions += [('_apply_ts0{}/CT1_trans.nii.gz'.format(i),
                           session+'/'+'CT1_reg2CT.nii.gz')]
        substitutions += [('_apply_ts1{}/T2_trans.nii.gz'.format(i),
                           session+'/'+'T2_reg2CT.nii.gz')]
        substitutions += [('_apply_ts2{}/FLAIR_trans.nii.gz'.format(i),
                           session+'/'+'FLAIR_reg2CT.nii.gz')]
        substitutions += [('_apply_ts_t1{}/T1_trans.nii.gz'.format(i),
                           session+'/'+'T1_reg2CT.nii.gz')]

    datasink.inputs.substitutions =substitutions
    # Create Workflow
    workflow = nipype.Workflow('registration_workflow', base_dir=NIPYPE_CACHE)

    for i, reg in enumerate(reg_nodes):
        workflow.connect(datasource, sequences[i+1], reg, 'input_file')
        workflow.connect(datasource, sequences[0], reg, 'ref_file')

    for i, node in enumerate(apply_ts_nodes):
        workflow.connect(datasource, sequences[i+1], node, 'input_image')
        workflow.connect(datasource, 'reference', node, 'reference_image')
        workflow.connect(merge_nodes[i], 'out', node, 'transforms')
        workflow.connect(node, 'output_image', datasink,
                         'results.subid.@{}_reg2CT'.format(sequences[i+1]))

    for i in range(len(sessions)):
        workflow.connect(regT12CT, 'regmat', fake_merge, 'in{}'.format(i+1))

    for i, node in enumerate(merge_nodes):
        workflow.connect(reg_nodes[i], 'regmat', node, 'in4')
        workflow.connect(reg2T1, 'warp_file', node, 'in3')
        workflow.connect(reg2T1, 'regmat', node, 'in2')
        workflow.connect(fake_merge, 'out', node, 'in1')

    for i, mask in enumerate(apply_mask_nodes):
        workflow.connect(reg_nodes[i], 'reg_file', mask, 'in_file')
        workflow.connect(bet, 'out_mask', mask, 'mask_file')
        workflow.connect(mask, 'out_file', datasink,
                         'results.subid.@{}_preproc'.format(sequences[i+1]))
    workflow.connect(datasource, sequences[0], bet, 'input_file')
    workflow.connect(datasource, 't1_0', bet_t10, 'input_file')
    workflow.connect(bet, 'out_file', reg2T1, 'input_file')
    workflow.connect(bet_t10, 'out_file', reg2T1, 'ref_file')
    workflow.connect(datasource, 'reference', regT12CT, 'ref_file')
    workflow.connect(datasource, 't1_0', regT12CT, 'input_file')
    workflow.connect(datasource, 't1', apply_ts_t1, 'input_image')
    workflow.connect(datasource, 'reference', apply_ts_t1,
                     'reference_image')
    workflow.connect(merge_ts_t1, 'out', apply_ts_t1, 'transforms')
    workflow.connect(reg2T1, 'warp_file', merge_ts_t1, 'in3')
    workflow.connect(reg2T1, 'regmat', merge_ts_t1, 'in2')
    workflow.connect(fake_merge, 'out', merge_ts_t1, 'in1')
    workflow.connect(apply_ts_t1, 'output_image', datasink,
                     'results.subid.@T1_reg2CT')
    workflow.connect(bet, 'out_file', datasink,
                     'results.subid.@T1_preproc')
    workflow.connect(datasource, 'reference', datasink,
                     'results.subid.@ref_ct')

    return workflow

if __name__ == "__main__":

    PARSER = argparse.ArgumentParser()

    PARSER.add_argument('--input_dir', '-i', type=str,
                        help=('Exisisting directory with the subject(s) to process'))
    PARSER.add_argument('--work_dir', '-w', type=str,
                        help=('Directory where to store the results.'))
    PARSER.add_argument('--clean-cache', '-c', action='store_true',
                        help=('To remove all the intermediate files. Enable this only '
                              'when you are sure that the workflow is running properly '
                              'otherwise it will always restart from scratch. '
                              'Default False.'))

    ARGS = PARSER.parse_args()

    BASE_DIR = ARGS.input_dir
    WORKFLOW_CACHE = os.path.join(ARGS.work_dir, 'temp_dir')
    NIPYPE_CACHE_BASE = os.path.join(ARGS.work_dir, 'nipype_cache')
    RESULT_DIR = os.path.join(ARGS.work_dir, 'segmentation_results')
    CLEAN_CACHE = ARGS.clean_cache

    
    sub_list = os.listdir(BASE_DIR)

    if not os.path.isdir(WORKFLOW_CACHE):
        os.makedirs(WORKFLOW_CACHE)

    for sub_id in sub_list:
        NIPYPE_CACHE = os.path.join(NIPYPE_CACHE_BASE, sub_id)
        datasource, sessions = gbm_datasource(sub_id, BASE_DIR)
        workflow = build_registration_workflow(
            sub_id, datasource, sessions, RESULT_DIR, NIPYPE_CACHE)
        workflow.run(plugin='Linear')
        if CLEAN_CACHE:
            shutil.rmtree(NIPYPE_CACHE)

    print('Done!')
