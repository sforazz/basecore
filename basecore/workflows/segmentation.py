"Segmentation workflows"
import nipype
from nipype.interfaces.utility import Merge
from basecore.interfaces.utils import NNUnetPreparation
from basecore.interfaces.mic import HDGlioPredict, NNUnetInference
from nipype.interfaces.ants import ApplyTransforms
from basecore.workflows.datahandler import datasink_base


def tumor_segmentation(datasource, sub_id, sessions, gtv_model,
                       tumor_model, result_dir, nipype_cache, reference,
                       reg_workflow=None, bet_workflow=None):

    if reg_workflow is None:
        if reference:
            iterfields_t1 = ['in1', 'in2', 'in3']
            if_0 = 2
        else:
            iterfields_t1 = ['in1', 'in2']
            if_0 = 1
        merge_ts_t1 = nipype.MapNode(interface=Merge(len(iterfields_t1)),
                                     iterfield=iterfields_t1,
                                     name='merge_t1')
        merge_ts_t1.inputs.ravel_inputs = True
    

        
#         fake_merge = nipype.Node(interface=Merge(len(sessions)),
#                                  name='fake_merge')

    apply_ts_gtv = nipype.MapNode(interface=ApplyTransforms(),
                                 iterfield=['input_image', 'transforms'],
                                 name='apply_ts_gtv')
    apply_ts_gtv.inputs.interpolation = 'NearestNeighbor'
    apply_ts_tumor = nipype.MapNode(interface=ApplyTransforms(),
                                 iterfield=['input_image', 'transforms'],
                                 name='apply_ts_tumor')
    apply_ts_tumor.inputs.interpolation = 'NearestNeighbor'
    apply_ts_tumor1 = nipype.MapNode(interface=ApplyTransforms(),
                                 iterfield=['input_image', 'transforms'],
                                 name='apply_ts_tumor1')
    apply_ts_tumor1.inputs.interpolation = 'NearestNeighbor'

    tumor_seg  = nipype.MapNode(interface=HDGlioPredict(),
                                iterfield=['t1', 'ct1', 't2', 'flair'],
                                name='tumor_segmentation')
    tumor_seg.inputs.out_file = 'segmentation'

    mi = nipype.MapNode(Merge(2), iterfield=['in1', 'in2'],
                        name='merge')

    gtv_seg_data_prep = nipype.MapNode(interface=NNUnetPreparation(),
                                       iterfield=['images'],
                                       name='gtv_seg_data_prep')

    gtv_seg = nipype.MapNode(interface=NNUnetInference(), iterfield=['input_folder'],
                             name='gtv_segmentation')
    gtv_seg.inputs.model_folder = gtv_model

    tumor_seg_2mods = nipype.MapNode(interface=NNUnetInference(), iterfield=['input_folder'],
                             name='tumor_seg_2mods')
    tumor_seg_2mods.inputs.model_folder = tumor_model

    datasink = nipype.Node(nipype.DataSink(base_directory=result_dir), "datasink")

    substitutions = [('/segmentation.nii.gz', '/Tumor_predicted.nii.gz')]
    substitutions += [('subid', sub_id)]
    for i, session in enumerate(sessions):
        substitutions += [('_tumor_segmentation{}/'.format(i), session+'/')]
        substitutions += [('_gtv_segmentation{}/subject1'.format(i),
                           session+'/GTV_predicted')]
        substitutions += [('_tumor_seg_2mods{}/subject1'.format(i),
                           session+'/Tumor_predicted_2modalities')]
        substitutions += [('_apply_ts_gtv{}/subject1_trans.nii.gz'.format(i),
                           session+'/'+'GTV_predicted_reg2CT.nii.gz')]
        substitutions += [('_apply_ts_tumor1{}/subject1_trans.nii.gz'.format(i),
                           session+'/'+'Tumor_predicted_2modalities_reg2CT.nii.gz')]
        substitutions += [('_apply_ts_tumor{}/segmentation_trans.nii.gz'.format(i),
                           session+'/'+'Tumor_predicted_reg2CT.nii.gz')]
    datasink.inputs.substitutions =substitutions

    # Create Workflow
    workflow = nipype.Workflow('tumor_segmentation_workflow', base_dir=nipype_cache)

    # Connect from registration workflow, if provided
    if reg_workflow is not None:
        workflow.connect(reg_workflow, 'masking0.out_file', mi, 'in1')
        workflow.connect(reg_workflow, 'masking2.out_file', mi, 'in2')
        workflow.connect(reg_workflow, 'masking0.out_file', tumor_seg, 'ct1')
        workflow.connect(reg_workflow, 'masking1.out_file', tumor_seg, 't2')
        workflow.connect(reg_workflow, 'masking2.out_file', tumor_seg, 'flair')
        workflow.connect(bet_workflow, 'bet.out_file', tumor_seg, 't1')
        workflow.connect(reg_workflow, 'merge_t1.out', apply_ts_tumor, 'transforms')
        workflow.connect(reg_workflow, 'merge_t1.out', apply_ts_gtv, 'transforms')
        workflow.connect(reg_workflow, 'merge_t1.out', apply_ts_tumor1, 'transforms')
    else:
#         for i in range(len(sessions)):
#             workflow.connect(datasource, 't12ct_mat', fake_merge,
#                              'in{}'.format(i+1))
        workflow.connect(datasource, 'reg2t1_warp', merge_ts_t1, 'in{}'.format(if_0+1))
        workflow.connect(datasource, 'reg2t1_mat', merge_ts_t1, 'in{}'.format(if_0))
        if reference:
            workflow.connect(datasource, 't12ct_mat', merge_ts_t1, 'in1')
        workflow.connect(merge_ts_t1, 'out', apply_ts_tumor, 'transforms')
        workflow.connect(merge_ts_t1, 'out', apply_ts_gtv, 'transforms')
        workflow.connect(merge_ts_t1, 'out', apply_ts_tumor1, 'transforms')
        workflow.connect(datasource, 'ct1_preproc', mi, 'in1')
        workflow.connect(datasource, 'flair_preproc', mi, 'in2')
        workflow.connect(datasource, 'ct1_preproc', tumor_seg, 'ct1')
        workflow.connect(datasource, 't2_preproc', tumor_seg, 't2')
        workflow.connect(datasource, 'flair_preproc', tumor_seg, 'flair')
        workflow.connect(datasource, 't1_preproc', tumor_seg, 't1')

    # Connect from datasource
    if reference:
        workflow.connect(datasource, 'reference', apply_ts_gtv,
                         'reference_image')
        workflow.connect(datasource, 'reference', apply_ts_tumor1,
                         'reference_image')
        workflow.connect(datasource, 'reference', apply_ts_tumor,
                         'reference_image')
    else:
        workflow.connect(datasource, 't1_0', apply_ts_gtv,
                         'reference_image')
        workflow.connect(datasource, 't1_0', apply_ts_tumor1,
                         'reference_image')
        workflow.connect(datasource, 't1_0', apply_ts_tumor,
                         'reference_image')

    # Connect other nodes

    # Nodes to prepare the data before nnUNet inference
    workflow.connect(mi, 'out', gtv_seg_data_prep, 'images')

    # Nodes to segment GTV and tumor using nnUNet
    workflow.connect(gtv_seg_data_prep, 'output_folder',
                     gtv_seg, 'input_folder')
    workflow.connect(gtv_seg_data_prep, 'output_folder',
                     tumor_seg_2mods, 'input_folder')

    # Nodes to normalize segmentations to CT space
    workflow.connect(gtv_seg, 'output_file', apply_ts_gtv, 'input_image')
    workflow.connect(tumor_seg_2mods, 'output_file', apply_ts_tumor1,
                     'input_image')
    workflow.connect(tumor_seg, 'out_file', apply_ts_tumor, 'input_image')

    # Connect datasink nodes to save outputs
    workflow.connect(tumor_seg, 'out_file', datasink,
                     'results.subid.@tumor_seg')
    workflow.connect(gtv_seg, 'output_file', datasink,
                     'results.subid.@gtv_seg')
    workflow.connect(tumor_seg_2mods, 'output_file', datasink,
                     'results.subid.@tumor_seg_2mods')
    workflow.connect(apply_ts_gtv, 'output_image', datasink,
                     'results.subid.@gtv_reg2CT')
    workflow.connect(apply_ts_tumor, 'output_image', datasink,
                     'results.subid.@tumor_reg2CT')
    workflow.connect(apply_ts_tumor1, 'output_image', datasink,
                     'results.subid.@tumor1_reg2CT')

    workflow = datasink_base(datasink, datasource, workflow, sessions, reference)

    return workflow
