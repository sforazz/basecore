"Registration workflows"
import nipype
from nipype.interfaces.fsl.maths import ApplyMask
from nipype.interfaces.ants import ApplyTransforms
from nipype.interfaces.utility import Merge
from nipype.interfaces.fsl.utils import Reorient2Std
from basecore.interfaces.ants import AntsRegSyn
from basecore.workflows.datahandler import datasink_base


def brain_registration(sub_id, datasource, sessions, reference,
                              result_dir, nipype_cache, bet_workflow=None,
                              t10=False, sequences=[], ref_sequence=[]):
    """
    This is a workflow to register multi-modalities MR brain images to their 
    reference MR image, in multi or single time-point(s) cohort. In particular, for each 
    subject, this workflow will register the MR images in each time-point (tp)
    to the corresponding reference(can be T1 or T1KM), then it will register all the ref'
    ' images to a reference "T10" MR (for example the one used during the radiotherapy planning),'
    ' and finally the reference MR to the BPLCT. At the end, all the MR images will be saved '
    'both in reference space (for each tp), in "T10" space and in CT space.
    """

    substitutions = [('subid', sub_id)]
    if t10:
        reg2T1 = nipype.MapNode(interface=AntsRegSyn(), iterfield=['input_file'], name='reg2T1')
        reg2T1.inputs.transformation = 's'
        reg2T1.inputs.num_dimensions = 3
        reg2T1.inputs.num_threads = 6
    if t10:
        outname_reg2T1 = 'reg2T1_ref'
        outname_T12CT = 'T1_ref_reg2CT'
    else:
        outname_reg2T1 = 'reg2CT'
        outname_T12CT = 'T1_reg2CT'

    if reference:
        regT12CT = nipype.MapNode(interface=AntsRegSyn(),
                                  iterfield=['input_file'],
                                  name='regT12CT')
        regT12CT.inputs.transformation = 'r'
        regT12CT.inputs.num_dimensions = 3
        regT12CT.inputs.num_threads = 4
        if t10:
            iterfields = ['in1', 'in2', 'in3', 'in4']
            iterfields_t1 = ['in1', 'in2', 'in3']
            if_0 = 2
        else:
            iterfields = ['in1', 'in2']
            iterfields_t1 = ['in1', 'in2']
            if_0 = 1
    elif not reference and t10:
        iterfields = ['in1', 'in2', 'in3']
        iterfields_t1 = ['in1', 'in2']
        if_0 = 1

    reg_nodes = {}
    apply_mask_nodes = {}
    apply_mask_t1ref_nodes = {}
    apply_ts_nodes = {}
    apply_ts_nodes1 = {}
    merge_nodes = {}
    merge_nodes1 = {}

    for seq in sequences:
        reg = nipype.MapNode(interface=AntsRegSyn(), iterfield=['input_file', 'ref_file'],
                             name='ants_reg{}'.format(seq))
        reg.inputs.transformation = 'r'
        reg.inputs.num_dimensions = 3
        reg.inputs.num_threads = 4
        reg.inputs.interpolation = 'BSpline'
        reg_nodes[seq] = reg

        masking = nipype.MapNode(interface=ApplyMask(), iterfield=['in_file', 'mask_file'],
                                 name='masking{}'.format(seq))
        apply_mask_nodes[seq] = masking
        if t10:
            masking_t1ref = nipype.MapNode(interface=ApplyMask(),
                                           iterfield=['in_file', 'mask_file'],
                                           name='masking_t1ref{}'.format(seq))
            apply_mask_t1ref_nodes[seq] = masking_t1ref

        apply_ts = nipype.MapNode(interface=ApplyTransforms(),
                                  iterfield=['input_image', 'transforms'],
                                  name='apply_ts{}'.format(seq))
        apply_ts_nodes[seq] = apply_ts
        # Apply ts nodes for T1_ref normalization
        if t10:
            apply_ts1 = nipype.MapNode(interface=ApplyTransforms(),
                                      iterfield=['input_image', 'transforms'],
                                      name='apply_ts1{}'.format(seq))
            apply_ts_nodes1[seq] = apply_ts1
            merge1 = nipype.MapNode(interface=Merge(3),
                                     iterfield=['in1', 'in2', 'in3'],
                                     name='merge1{}'.format(seq))
            merge1.inputs.ravel_inputs = True
            merge_nodes1[seq] = merge1
        if reference:
            merge = nipype.MapNode(interface=Merge(len(iterfields)),
                                     iterfield=iterfields,
                                     name='merge{}'.format(seq))
            merge.inputs.ravel_inputs = True
            merge_nodes[seq] = merge
        # Merging transforms for normalization to T1_ref
        
        for i, session in enumerate(sessions):
            substitutions += [(('_masking_t1ref{0}{1}/{2}_reoriented_trans_masked.nii.gz'
                                .format(seq, i, seq.upper())),
                               session+'/'+'{}_reg2T1_ref_masked.nii.gz'.format(seq.upper()))]
            substitutions += [('_apply_ts1{0}{1}/{2}_reoriented_trans.nii.gz'.format(seq, i, seq.upper()),
                               session+'/'+'{}_reg2T1_ref.nii.gz'.format(seq.upper()))]
            substitutions += [('_apply_ts{0}{1}/{2}_reoriented_trans.nii.gz'.format(seq, i, seq.upper()),
                               session+'/'+'{}_reg2CT.nii.gz'.format(seq.upper()))]
            substitutions += [('_masking{0}{1}/antsregWarped_masked.nii.gz'.format(seq, i, seq.upper()),
                               session+'/'+'{}_preproc.nii.gz'.format(seq.upper()))]
    
    reorient_nodes = {}
    for seq in [ref_sequence]+sequences:
        reorient = nipype.MapNode(interface=Reorient2Std(), iterfield=['in_file'],
                                 name='reorient{}'.format(seq))
        reorient_nodes[seq] = reorient
    if t10:
        reorient_t10 = nipype.Node(interface=Reorient2Std(), name='reorient_t10')
    if reference and t10:
        apply_ts_t1 = nipype.MapNode(interface=ApplyTransforms(),
                                     iterfield=['input_image', 'transforms'],
                                     name='apply_ts_t1')
    
        merge_ts_t1 = nipype.MapNode(interface=Merge(len(iterfields_t1)),
                                     iterfield=iterfields_t1,
                                     name='merge_t1')
        merge_ts_t1.inputs.ravel_inputs = True

    # have to create a fake merge of the transformation from t10 to CT in order
    # to have the same number if matrices as input in mapnode
    if reference:
        fake_merge = nipype.Node(interface=Merge(len(sessions)), name='fake_merge')
    if t10:
        fake_merge_t1 = nipype.Node(interface=Merge(len(sessions)), name='fake_merge_t1')

    datasink = nipype.Node(nipype.DataSink(base_directory=result_dir), "datasink")

    for i, session in enumerate(sessions):
        substitutions += [('session'.format(i), session)]
        substitutions += [('_reg2T1{}/antsreg0GenericAffine.mat'.format(i),
                           session+'/'+'{0}_{1}.mat'.format(ref_sequence.upper(),
                                                            outname_reg2T1))]
        substitutions += [('_reg2T1{}/antsreg1Warp.nii.gz'.format(i),
                           session+'/'+'{}_reg2T1_ref_warp.nii.gz'
                           .format(ref_sequence.upper()))]
        substitutions += [('_reg2T1{}/antsreg1InverseWarp.nii.gz'.format(i),
                           session+'/'+'{}_reg2T1_ref_inverse_warp.nii.gz'
                           .format(ref_sequence.upper()))]
        substitutions += [('_reg2T1{}/antsregWarped.nii.gz'.format(i),
                           session+'/'+'{0}_{1}_masked.nii.gz'
                           .format(ref_sequence.upper(), outname_reg2T1))]
        substitutions += [('_reg2T1{}/antsreg0GenericAffine.mat'.format(i),
                           session+'/'+'{0}_{1}.mat'.format(ref_sequence.upper(),
                                                            outname_reg2T1))]
        substitutions += [('_regT12CT{}/antsreg0GenericAffine.mat'.format(i),
                           '{}.mat'.format(outname_T12CT))]
        substitutions += [('_regT12CT{}/antsregWarped.nii.gz'.format(i),
                           '{}.nii.gz'.format(outname_T12CT))]
        substitutions += [('_apply_ts_t1{}/T1_reoriented_trans.nii.gz'.format(i),
                           session+'/'+'T1_reg2CT.nii.gz')]

    datasink.inputs.substitutions =substitutions
    # Create Workflow
    workflow = nipype.Workflow('registration_workflow', base_dir=nipype_cache)
    if t10:
        workflow.connect(datasource, 't1_0', reorient_t10, 'in_file')

    for seq in reorient_nodes:
        workflow.connect(datasource, seq, reorient_nodes[seq], 'in_file')

    for seq in sequences:
        workflow.connect(reorient_nodes[seq], 'out_file', reg_nodes[seq], 'input_file')
        workflow.connect(reorient_nodes[ref_sequence], 'out_file', reg_nodes[seq], 'ref_file')
        
        if reference:
            if t10:
                workflow.connect(reg_nodes[seq], 'regmat', merge_nodes[seq], 'in{}'.format(if_0+2))
                workflow.connect(reg2T1, 'regmat', merge_nodes[seq], 'in{}'.format(if_0+1))
                workflow.connect(reg2T1, 'warp_file', merge_nodes[seq], 'in{}'.format(if_0))
            
                workflow.connect(fake_merge, 'out', merge_nodes[seq], 'in1')
            else:
                workflow.connect(reg_nodes[seq], 'regmat', merge_nodes[seq], 'in2')
                workflow.connect(regT12CT, 'regmat', merge_nodes[seq], 'in1')
            # Bring all MR in CT space
            workflow.connect(reorient_nodes[seq], 'out_file', apply_ts_nodes[seq], 'input_image')
            workflow.connect(datasource, 'reference', apply_ts_nodes[seq], 'reference_image')
            workflow.connect(merge_nodes[seq], 'out', apply_ts_nodes[seq], 'transforms')
            workflow.connect(apply_ts_nodes[seq], 'output_image', datasink,
                             'results.subid.@{}_reg2CT'.format(seq))
        # merge transformation to bring all images in T10 space
        if t10:
            workflow.connect(reg_nodes[seq], 'regmat', merge_nodes1[seq], 'in3')
            workflow.connect(reg2T1, 'regmat', merge_nodes1[seq], 'in2')
            workflow.connect(reg2T1, 'warp_file', merge_nodes1[seq], 'in1')
            # bring every MR in T1_ref space
            workflow.connect(reorient_nodes[seq], 'out_file',
                             apply_ts_nodes1[seq], 'input_image')
            workflow.connect(reorient_t10, 'out_file',
                             apply_ts_nodes1[seq], 'reference_image')
            workflow.connect(merge_nodes1[seq], 'out',
                             apply_ts_nodes1[seq], 'transforms')
            workflow.connect(apply_ts_nodes1[seq], 'output_image', datasink,
                             'results.subid.@{}_reg2T1_ref'.format(seq))
            workflow.connect(apply_ts_nodes1[seq], 'output_image',
                             apply_mask_t1ref_nodes[seq], 'in_file')
            # mask images in T10 space
            workflow.connect(fake_merge_t1, 'out', apply_mask_t1ref_nodes[seq], 'mask_file')
            workflow.connect(apply_mask_t1ref_nodes[seq], 'out_file', datasink,
                             'results.subid.@{}_reg2T1_ref_masked'.format(seq))
        # apply T1 mask to registered images
        workflow.connect(reg_nodes[seq], 'reg_file', apply_mask_nodes[seq], 'in_file')
        if bet_workflow is not None:
            workflow.connect(bet_workflow, 'bet.out_mask', apply_mask_nodes[seq], 'mask_file')
        else:
            workflow.connect(datasource, 't1_mask', apply_mask_nodes[seq], 'mask_file')
        workflow.connect(apply_mask_nodes[seq], 'out_file', datasink,
                         'results.subid.@{}_preproc'.format(seq))

    if reference:
        for i, sess in enumerate(sessions):
            workflow.connect(regT12CT, 'regmat', fake_merge, 'in{}'.format(i+1))
            workflow.connect(regT12CT, 'regmat', datasink,
                             'results.subid.{0}.@regT12CT_mat'.format(sess))
            workflow.connect(regT12CT, 'reg_file', datasink,
                             'results.subid.{0}.@T12T1_ref'.format(sess))
        workflow.connect(datasource, 'reference', regT12CT, 'ref_file')
        if t10:
            workflow.connect(reorient_t10, 'out_file', regT12CT,
                             'input_file')
            workflow.connect(fake_merge, 'out', merge_ts_t1, 'in1')
            workflow.connect(reg2T1, 'regmat', merge_ts_t1, 'in{}'.format(if_0+1))
            workflow.connect(reg2T1, 'warp_file', merge_ts_t1, 'in{}'.format(if_0))
            workflow.connect(datasource, 'reference', apply_ts_t1,
                             'reference_image')
            workflow.connect(reorient_nodes[ref_sequence], 'out_file',
                             apply_ts_t1, 'input_image')

            workflow.connect(merge_ts_t1, 'out', apply_ts_t1, 'transforms')
            workflow.connect(apply_ts_t1, 'output_image', datasink,
                             'results.subid.@T1_reg2CT')
        else:
            workflow.connect(reorient_nodes[ref_sequence], 'out_file',
                             regT12CT, 'input_file')

    if t10:
        for i, sess in enumerate(sessions):
                if bet_workflow is not None:
                    workflow.connect(bet_workflow, 't1_0_bet.out_mask',
                                     fake_merge_t1, 'in{}'.format(i+1))
                else:
                    workflow.connect(datasource, 't1_0_mask',
                                     fake_merge_t1, 'in{}'.format(i+1))
        if bet_workflow is not None:
            workflow.connect(bet_workflow, 'bet.out_file', reg2T1, 'input_file')
            workflow.connect(bet_workflow, 't1_0_bet.out_file', reg2T1, 'ref_file')
        else:
            workflow.connect(datasource, 't1_bet', reg2T1, 'input_file')
            workflow.connect(datasource, 't1_0_bet', reg2T1, 'ref_file')
        workflow.connect(reg2T1, 'warp_file', datasink,
                         'results.subid.@reg2CT_warp')
        workflow.connect(reg2T1, 'inv_warp', datasink,
                         'results.subid.@reg2CT_inverse_warp')
        workflow.connect(reg2T1, 'reg_file', datasink,
                         'results.subid.@reg2CT_file')
        workflow.connect(reg2T1, 'regmat', datasink,
                         'results.subid.@reg2CT_mat')

    if bet_workflow is not None:
        workflow = datasink_base(datasink, datasource, workflow,
                                 sessions, reference, t10=t10)
    else:
        workflow = datasink_base(datasink, datasource, workflow, sessions, reference,
                                 extra_nodes=['t1_bet'], t10=t10)

    return workflow
