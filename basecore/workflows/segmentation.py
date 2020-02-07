"Segmentation workflows"
import nipype
from nipype.interfaces.utility import Merge
from basecore.interfaces.utils import NNUnetPreparation
from basecore.interfaces.mic import HDGlioPredict, NNUnetInference
from basecore.workflows.datahandler import datasink_base


NEEDED_SEQUENCES = ['t1', 'ct1', 't2', 'flair']


def tumor_segmentation(datasource, sub_id, sessions, gtv_model,
                       tumor_model, result_dir, nipype_cache, reference,
                       t10=False, sequences=[], ref_sequence=[]):

    orig_sequences = sequences[:]
    sequences = ref_sequence+sequences
    if 't1km' in sequences:
        sequences.remove('t1km')
        sequences.append('ct1')
        ct1 = 't1km'
    else:
        ct1 = 'ct1'

    not_found = [x for x in sequences+NEEDED_SEQUENCES
                 if x not in sequences or x not in NEEDED_SEQUENCES]
    if not_found:
        print('{} sequences were provided. Tumor segmentation with HD-GLIO cannot be performed'
              .format(' '.join(not_found)))
        hd_glio = False
    else:
        hd_glio = True
    if not_found and 'ct1' in not_found or 'flair' in not_found:
        raise Exception('T1 post contrast agent and/or FLAIR were not provided.'
                        ' Nor tumor neither GTV segmentation can be performed.')

    if hd_glio:
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
    gtv_seg.inputs.prefix = 'gtv'

    tumor_seg_2mods = nipype.MapNode(interface=NNUnetInference(), iterfield=['input_folder'],
                             name='tumor_seg_2mods')
    tumor_seg_2mods.inputs.model_folder = tumor_model
    tumor_seg_2mods.inputs.prefix = 'tumor_2mod'

    datasink = nipype.Node(nipype.DataSink(base_directory=result_dir), "datasink")

    substitutions = [('/segmentation.nii.gz', '/Tumor_predicted.nii.gz')]
    substitutions += [('subid', sub_id)]
    for i, session in enumerate(sessions):
        substitutions += [('_tumor_segmentation{}/'.format(i), session+'/')]
        substitutions += [('_gtv_segmentation{}/subject1'.format(i),
                           session+'/GTV_predicted')]
        substitutions += [('nnunet_inference_gtv/subject1'.format(i),
                           session+'/GTV_predicted')]
        substitutions += [('_tumor_seg_2mods{}/subject1'.format(i),
                           session+'/Tumor_predicted_2modalities')]
        substitutions += [('nnunet_inference_tumor_2mod/subject1'.format(i),
                           session+'/Tumor_predicted_2modalities')]
    datasink.inputs.substitutions =substitutions

    # Create Workflow
    workflow = nipype.Workflow('tumor_segmentation_workflow', base_dir=nipype_cache)
    
    workflow.connect(datasource, '{}_preproc'.format(ct1), mi, 'in1')
    workflow.connect(datasource, 'flair_preproc', mi, 'in2')
    if hd_glio:
        workflow.connect(datasource, '{}_preproc'.format(ct1), tumor_seg, 'ct1')
        workflow.connect(datasource, 't2_preproc', tumor_seg, 't2')
        workflow.connect(datasource, 'flair_preproc', tumor_seg, 'flair')
        workflow.connect(datasource, 't1_preproc', tumor_seg, 't1')

    # Nodes to prepare the data before nnUNet inference
    workflow.connect(mi, 'out', gtv_seg_data_prep, 'images')

    # Nodes to segment GTV and tumor using nnUNet
    workflow.connect(gtv_seg_data_prep, 'output_folder',
                     gtv_seg, 'input_folder')
    workflow.connect(gtv_seg_data_prep, 'output_folder',
                     tumor_seg_2mods, 'input_folder')

    if hd_glio:
        workflow.connect(tumor_seg, 'out_file', datasink,
                         'results.subid.@tumor_seg')
    workflow.connect(gtv_seg, 'output_file', datasink,
                     'results.subid.@gtv_seg')
    workflow.connect(tumor_seg_2mods, 'output_file', datasink,
                     'results.subid.@tumor_seg_2mods')

    workflow = datasink_base(datasink, datasource, workflow, sessions,
                             reference, t10=t10, sequences=orig_sequences,
                             ref_sequence=ref_sequence)

    return workflow, hd_glio
