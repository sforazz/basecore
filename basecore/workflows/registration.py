"Registration workflows"
import nipype
from nipype.interfaces.fsl.maths import ApplyMask
from nipype.interfaces.ants import ApplyTransforms
from nipype.interfaces.utility import Merge, Split
from nipype.interfaces.fsl.utils import Reorient2Std
from basecore.interfaces.ants import AntsRegSyn
from basecore.workflows.datahandler import SEQUENCES, datasink_base


def longitudinal_registration(sub_id, datasource, sessions, reference,
                              result_dir, nipype_cache, bet_workflow=None):
    """
    This is a workflow to register multi-modalities MR (T2, T1KM, FLAIR) to their 
    reference T1 image, in multiple time-points cohort. In particular, for each 
    subject, this workflow will register the MR images in each time-point (tp)
    to the corresponding T1, then it will register all the T1 images to a reference T1
    (the one that is the closest in time to the radiotherapy session), and finally the
    reference T1 to the BPLCT. At the end, all the MR images will be saved both in T1 space
    (for each tp) and in CT space.
    """
    reg2T1 = nipype.MapNode(interface=AntsRegSyn(), iterfield=['input_file'], name='reg2T1')
    reg2T1.inputs.transformation = 's'
    reg2T1.inputs.num_dimensions = 3
    reg2T1.inputs.num_threads = 6

    if reference:
        regT12CT = nipype.MapNode(interface=AntsRegSyn(),
                                  iterfield=['input_file'],
                                  name='regT12CT')
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

    apply_mask_t1ref_nodes = []
    for i in range(3):
        masking = nipype.MapNode(interface=ApplyMask(), iterfield=['in_file', 'mask_file'],
                                 name='masking_t1ref{}'.format(i))
        apply_mask_t1ref_nodes.append(masking)
    
    reorient_nodes = []
    for i in range(4):
        reorient = nipype.MapNode(interface=Reorient2Std(), iterfield=['in_file'],
                                 name='reorient{}'.format(i))
        reorient_nodes.append(reorient)
    
    reorient_t10 = nipype.Node(interface=Reorient2Std(), name='reorient_t10')

    apply_ts_nodes = []
    for i in range(3):
        apply_ts = nipype.MapNode(interface=ApplyTransforms(),
                                  iterfield=['input_image', 'transforms'],
                                  name='apply_ts{}'.format(i))
        apply_ts_nodes.append(apply_ts)
    # Apply ts nodes for T1_ref normalization
    apply_ts_nodes1 = []
    for i in range(3):
        apply_ts = nipype.MapNode(interface=ApplyTransforms(),
                                  iterfield=['input_image', 'transforms'],
                                  name='apply_ts1{}'.format(i))
        apply_ts_nodes1.append(apply_ts)

    split_ds_nodes = []
    for i in range(4):
        split_ds = nipype.Node(interface=Split(), name='split_ds{}'.format(i))
        split_ds.inputs.splits = [1]*len(sessions)
        split_ds_nodes.append(split_ds)

    apply_ts_t1 = nipype.MapNode(interface=ApplyTransforms(),
                                 iterfield=['input_image', 'transforms'],
                                 name='apply_ts_t1')
    merge_nodes = []
    if reference:
        iterfields = ['in1', 'in2', 'in3', 'in4']
        iterfields_t1 = ['in1', 'in2', 'in3']
        if_0 = 2
    else:
        iterfields = ['in1', 'in2', 'in3']
        iterfields_t1 = ['in1', 'in2']
        if_0 = 1

    for i in range(3):
        merge = nipype.MapNode(interface=Merge(len(iterfields)),
                                 iterfield=iterfields,
                                 name='merge{}'.format(i))
        merge.inputs.ravel_inputs = True
        merge_nodes.append(merge)
    # Merging transforms for normalization to T1_ref
    merge_nodes1 = []
    for i in range(3):
        merge = nipype.MapNode(interface=Merge(3),
                                 iterfield=['in1', 'in2', 'in3'],
                                 name='merge1{}'.format(i))
        merge.inputs.ravel_inputs = True
        merge_nodes1.append(merge)

    merge_ts_t1 = nipype.MapNode(interface=Merge(len(iterfields_t1)),
                                 iterfield=iterfields_t1,
                                 name='merge_t1')
    merge_ts_t1.inputs.ravel_inputs = True

    # have to create a fake merge of the transformation from t10 to CT in order
    # to have the same number if matrices as input in mapnode
    fake_merge = nipype.Node(interface=Merge(len(sessions)), name='fake_merge')

    datasink = nipype.Node(nipype.DataSink(base_directory=result_dir), "datasink")

    substitutions = [('subid', sub_id)]
    for i, session in enumerate(sessions):
        substitutions += [('session'.format(i), session)]
        substitutions += [('_masking0{}/antsregWarped_masked.nii.gz'.format(i),
                           session+'/'+'CT1_preproc.nii.gz')]
        substitutions += [('_reg2T1{}/antsreg0GenericAffine.mat'.format(i),
                           session+'/'+'reg2T1_ref.mat')]
        substitutions += [('_reg2T1{}/antsreg1Warp.nii.gz'.format(i),
                           session+'/'+'reg2T1_ref_warp.nii.gz')]
        substitutions += [('_reg2T1{}/antsregWarped.nii.gz'.format(i),
                           session+'/'+'T1_reg2T1_ref.nii.gz')]
        substitutions += [('_regT12CT{}/antsreg0GenericAffine.mat'.format(i),
                           '/regT1_ref2CT.mat')]
        substitutions += [('_masking1{}/antsregWarped_masked.nii.gz'.format(i),
                           session+'/'+'T2_preproc.nii.gz')]
        substitutions += [('_masking2{}/antsregWarped_masked.nii.gz'.format(i),
                           session+'/'+'FLAIR_preproc.nii.gz')]
        substitutions += [('_apply_ts0{}/CT1_reoriented_trans.nii.gz'.format(i),
                           session+'/'+'CT1_reg2CT.nii.gz')]
        substitutions += [('_apply_ts1{}/T2_reoriented_trans.nii.gz'.format(i),
                           session+'/'+'T2_reg2CT.nii.gz')]
        substitutions += [('_apply_ts2{}/FLAIR_reoriented_trans.nii.gz'.format(i),
                           session+'/'+'FLAIR_reg2CT.nii.gz')]
        substitutions += [('_apply_ts_t1{}/T1_reoriented_trans.nii.gz'.format(i),
                           session+'/'+'T1_reg2CT.nii.gz')]
        substitutions += [('_apply_ts10{}/CT1_reoriented_trans.nii.gz'.format(i),
                           session+'/'+'CT1_reg2T1_ref.nii.gz')]
        substitutions += [('_apply_ts11{}/T2_reoriented_trans.nii.gz'.format(i),
                           session+'/'+'T2_reg2T1_ref.nii.gz')]
        substitutions += [('_apply_ts12{}/FLAIR_reoriented_trans.nii.gz'.format(i),
                           session+'/'+'FLAIR_reg2T1_ref.nii.gz')]
        substitutions += [('_masking_t1ref0{}/CT1_reoriented_trans_masked.nii.gz'.format(i),
                           session+'/'+'CT1_reg2T1_ref_masked.nii.gz')]
        substitutions += [('_masking_t1ref1{}/T2_reoriented_trans_masked.nii.gz'.format(i),
                           session+'/'+'T2_reg2T1_ref_masked.nii.gz')]
        substitutions += [('_masking_t1ref2{}/FLAIR_reoriented_trans_masked.nii.gz'.format(i),
                           session+'/'+'FLAIR_reg2T1_ref_masked.nii.gz')]

    datasink.inputs.substitutions =substitutions
    # Create Workflow
    workflow = nipype.Workflow('registration_workflow', base_dir=nipype_cache)

    workflow.connect(datasource, 't1_0', reorient_t10, 'in_file')

    for i, node in enumerate(reorient_nodes):
        workflow.connect(datasource, SEQUENCES[i], node, 'in_file')

    for i, reg in enumerate(reg_nodes):
        workflow.connect(reorient_nodes[i+1], 'out_file', reg, 'input_file')
        workflow.connect(reorient_nodes[0], 'out_file', reg, 'ref_file')
#         workflow.connect(datasource, SEQUENCES[i+1], reg, 'input_file')
#         workflow.connect(datasource, SEQUENCES[0], reg, 'ref_file')
    # bring every MR in CT space
    if reference:
        for i, node in enumerate(apply_ts_nodes):
            workflow.connect(reorient_nodes[i+1], 'out_file', node, 'input_image')
    #         workflow.connect(datasource, SEQUENCES[i+1], node, 'input_image')
            workflow.connect(datasource, 'reference', node, 'reference_image')
            workflow.connect(merge_nodes[i], 'out', node, 'transforms')
            workflow.connect(node, 'output_image', datasink,
                             'results.subid.@{}_reg2CT'.format(SEQUENCES[i+1]))
    # bring every MR in T1_ref space
    for i, node in enumerate(apply_ts_nodes1):
        workflow.connect(reorient_nodes[i+1], 'out_file', node, 'input_image')
#         workflow.connect(datasource, SEQUENCES[i+1], node, 'input_image')
#         workflow.connect(datasource, 't1_0', node, 'reference_image')
        workflow.connect(reorient_t10, 'out_file', node, 'reference_image')
        workflow.connect(merge_nodes1[i], 'out', node, 'transforms')
        workflow.connect(node, 'output_image', datasink,
                         'results.subid.@{}_reg2T1_ref'.format(SEQUENCES[i+1])) 

    for i, node in enumerate(merge_nodes):
        workflow.connect(reg_nodes[i], 'regmat', node, 'in{}'.format(if_0+2))
        workflow.connect(reg2T1, 'regmat', node, 'in{}'.format(if_0+1))
        workflow.connect(reg2T1, 'warp_file', node, 'in{}'.format(if_0))
        if reference:
            workflow.connect(fake_merge, 'out', node, 'in1')
    
    for i, node in enumerate(merge_nodes1):
        workflow.connect(reg_nodes[i], 'regmat', node, 'in3')
        workflow.connect(reg2T1, 'regmat', node, 'in2')
        workflow.connect(reg2T1, 'warp_file', node, 'in1')

    for i, mask in enumerate(apply_mask_nodes):
        workflow.connect(reg_nodes[i], 'reg_file', mask, 'in_file')
        if bet_workflow is not None:
            workflow.connect(bet_workflow, 'bet.out_mask', mask, 'mask_file')
        else:
            workflow.connect(datasource, 't1_mask', mask, 'mask_file')
        workflow.connect(mask, 'out_file', datasink,
                         'results.subid.@{}_preproc'.format(SEQUENCES[i+1]))
    
    for i, mask in enumerate(apply_mask_t1ref_nodes):
        workflow.connect(apply_ts_nodes1[i], 'output_image', mask, 'in_file')
        if bet_workflow is not None:
            workflow.connect(bet_workflow, 'bet.t1_0_bet', mask, 'mask_file')
        else:
            workflow.connect(datasource, 't1_0_mask', mask, 'mask_file')
        workflow.connect(mask, 'out_file', datasink,
                         'results.subid.@{}_reg2T1_ref_masked'.format(SEQUENCES[i+1]))

    if bet_workflow is not None:
        workflow.connect(bet_workflow, 'bet.out_file', reg2T1, 'input_file')
        workflow.connect(bet_workflow, 't1_0_bet.out_file', reg2T1, 'ref_file')
    else:
        workflow.connect(datasource, 't1_bet', reg2T1, 'input_file')
        workflow.connect(datasource, 't1_0_bet', reg2T1, 'ref_file')

    if reference:
        for i, sess in enumerate(sessions):
            workflow.connect(regT12CT, 'regmat', fake_merge, 'in{}'.format(i+1))
            workflow.connect(regT12CT, 'regmat', datasink,
                             'results.subid.{0}.@regT12CT_mat'.format(sess))
        workflow.connect(datasource, 'reference', regT12CT, 'ref_file')
        workflow.connect(reorient_t10, 'out_file', regT12CT,
                         'input_file') 
#         workflow.connect(datasource, 't1_0', regT12CT, 'input_file')
        workflow.connect(fake_merge, 'out', merge_ts_t1, 'in1')
        workflow.connect(datasource, 'reference', apply_ts_t1,
                         'reference_image')
#         workflow.connect(datasource, 't1_0', apply_ts_t1,
#                          'reference_image') 
#     workflow.connect(datasource, 't1', apply_ts_t1, 'input_image')
        workflow.connect(reorient_nodes[0], 'out_file', apply_ts_t1, 'input_image')
    
        workflow.connect(merge_ts_t1, 'out', apply_ts_t1, 'transforms')
        workflow.connect(apply_ts_t1, 'output_image', datasink,
                         'results.subid.@T1_reg2CT')
    workflow.connect(reg2T1, 'regmat', merge_ts_t1, 'in{}'.format(if_0+1))
    workflow.connect(reg2T1, 'warp_file', merge_ts_t1, 'in{}'.format(if_0))

    workflow.connect(reg2T1, 'warp_file', datasink,
                     'results.subid.@reg2CT_warp')
    workflow.connect(reg2T1, 'regmat', datasink,
                     'results.subid.@reg2CT_mat')
    workflow.connect(reg2T1, 'reg_file', datasink,
                     'results.subid.@T12T1_ref')

    if bet_workflow is not None:
        workflow = datasink_base(datasink, datasource, workflow, sessions, reference)
    else:
        workflow = datasink_base(datasink, datasource, workflow, sessions, reference,
                                 extra_nodes=['t1_bet'])

    return workflow


def single_tp_registration(sub_id, datasource, session, reference,
                           result_dir, nipype_cache, bet_workflow=None):
    """
    This is a workflow to register multi-modalities MR (T2, T1KM, FLAIR) to their 
    reference T1 image, in one single time-point cohort. In particular, for each 
    subject, this workflow will register the MR images in the provided time-point (tp)
    to the corresponding T1, then it will register the T1 image to the BPLCT (if present)'
    '. At the end, all the MR images will be saved both in T1 space and in CT space.
    """
    session = session[0]
    if reference:
        regT12CT = nipype.MapNode(interface=AntsRegSyn(),
                                  iterfield=['input_file'],
                                  name='regT12CT')
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
    
    if reference:
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
            merge = nipype.MapNode(interface=Merge(2),
                                     iterfield=['in1', 'in2'],
                                     name='merge{}'.format(i))
            merge.inputs.ravel_inputs = True
            merge_nodes.append(merge)

    datasink = nipype.Node(nipype.DataSink(base_directory=result_dir), "datasink")

    substitutions = [('subid', sub_id)]
    substitutions += [('session', session)]
    substitutions += [('_regT12CT0/antsreg0GenericAffine.mat',
                       '/reg2T1_ref.mat')]
    substitutions += [('_masking00/antsregWarped_masked.nii.gz',
                       session+'/'+'CT1_preproc.nii.gz')]
    substitutions += [('_regT12CT/antsreg0GenericAffine.mat',
                       '/regT1_ref2CT.mat')]
    substitutions += [('_masking10/antsregWarped_masked.nii.gz',
                       session+'/'+'T2_preproc.nii.gz')]
    substitutions += [('_masking20/antsregWarped_masked.nii.gz',
                       session+'/'+'FLAIR_preproc.nii.gz')]
    substitutions += [('_apply_ts00/antsregWarped_masked_trans.nii.gz',
                       session+'/'+'CT1_reg2CT.nii.gz')]
    substitutions += [('_apply_ts10/antsregWarped_masked_trans.nii.gz',
                       session+'/'+'T2_reg2CT.nii.gz')]
    substitutions += [('_apply_ts20/antsregWarped_masked_trans.nii.gz',
                       session+'/'+'FLAIR_reg2CT.nii.gz')]
    substitutions += [('_apply_ts_t10/T1_preproc_trans.nii.gz',
                       session+'/'+'T1_reg2CT.nii.gz')]

    datasink.inputs.substitutions =substitutions
    # Create Workflow
    workflow = nipype.Workflow('registration_workflow', base_dir=nipype_cache)

    for i, reg in enumerate(reg_nodes):
        workflow.connect(datasource, SEQUENCES[i+1], reg, 'input_file')
        workflow.connect(datasource, SEQUENCES[0], reg, 'ref_file')
    # bring every MR in CT space
    if reference:
        for i, node in enumerate(merge_nodes):
            workflow.connect(reg_nodes[i], 'regmat', node, 'in2')
            workflow.connect(regT12CT, 'regmat', node, 'in1')
        for i, node in enumerate(apply_ts_nodes):
            workflow.connect(apply_mask_nodes[i], 'out_file', node, 'input_image')
            workflow.connect(datasource, 'reference', node, 'reference_image')
            workflow.connect(regT12CT, 'regmat', node, 'transforms')
            workflow.connect(node, 'output_image', datasink,
                             'results.subid.@{}_reg2CT'.format(SEQUENCES[i+1]))

        workflow.connect(regT12CT, 'regmat', datasink,
                         'results.subid.{0}.@regT12CT_mat'.format(session))
        workflow.connect(datasource, 'reference', regT12CT, 'ref_file')
        workflow.connect(datasource, 't1', regT12CT, 'input_file')

        if bet_workflow is not None:
            workflow.connect(bet_workflow, 'bet.out_file', apply_ts_t1, 'input_image')
        else:
            workflow.connect(datasource, 't1_bet', apply_ts_t1, 'input_image')
        workflow.connect(datasource, 'reference', apply_ts_t1, 'reference_image')
        workflow.connect(apply_ts_t1, 'output_image', datasink,
                         'results.subid.@T1_reg2CT')
        workflow.connect(regT12CT, 'regmat', apply_ts_t1, 'transforms')

    for i, mask in enumerate(apply_mask_nodes):
        workflow.connect(reg_nodes[i], 'reg_file', mask, 'in_file')
        if bet_workflow is not None:
            workflow.connect(bet_workflow, 'bet.out_mask', mask, 'mask_file')
        else:
            workflow.connect(datasource, 't1_mask', mask, 'mask_file')
        workflow.connect(mask, 'out_file', datasink,
                         'results.subid.@{}_preproc'.format(SEQUENCES[i+1]))

    if bet_workflow is not None:
        workflow = datasink_base(datasink, datasource, workflow, [session], reference,
                                 t10=False)
    else:
        workflow = datasink_base(datasink, datasource, workflow, [session], reference,
                                 extra_nodes=['t1_bet'], t10=False)

    return workflow
