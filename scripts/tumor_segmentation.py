"Script to run the tumor segmentation using HD-GLIO"
import os
import argparse
import shutil
import nipype
from nipype.interfaces.fsl.maths import ApplyMask
from nipype.interfaces.dcm2nii import Dcm2niix
from nipype.interfaces.utility import Merge
from basecore.interfaces.utils import DicomCheck, ConversionCheck,\
    NNUnetPreparation
from basecore.interfaces.mic import HDBet, HDGlioPredict, NNUnetInference
from basecore.interfaces.ants import AntsRegSyn



if __name__ == "__main__":

    PARSER = argparse.ArgumentParser()

    PARSER.add_argument('--input_dir', '-i', type=str,
                        help=('Exisisting directory with the subject(s) to process'))
    PARSER.add_argument('--work_dir', '-w', type=str,
                        help=('Directory where to store the results.'))
    PARSER.add_argument('--model_dir', '-md', type=str,
                        help=('Directory with the model parameters, trained with nnUNet.'))
    PARSER.add_argument('--clean-cache', '-c', action='store_true',
                        help=('To remove all the intermediate files. Enable this only '
                              'when you are sure that the workflow is running properly '
                              'otherwise it will always restart from scratch. '
                              'Default False.'))

    ARGS = PARSER.parse_args()

    BASE_DIR = ARGS.input_dir
    WORKFLOW_CACHE = os.path.join(ARGS.work_dir, 'temp_dir')
    NIPYPE_CACHE = os.path.join(ARGS.work_dir, 'nipype_cache')
    RESULT_DIR = os.path.join(ARGS.work_dir, 'segmentation_results')
    CLEAN_CACHE = ARGS.clean_cache

    sequences = ['t1', 'ct1', 't2', 'flair']
    sub_list = os.listdir(BASE_DIR)

    if not os.path.isdir(WORKFLOW_CACHE):
        os.makedirs(WORKFLOW_CACHE)

    datasource = nipype.Node(
        interface=nipype.DataGrabber(infields=['subjects'], outfields=['t1', 'ct1', 't2', 'flair']),
        name='datasource')
    datasource.inputs.base_directory = BASE_DIR
    datasource.inputs.template = '*'
    datasource.inputs.sort_filelist = True
    datasource.inputs.field_template = dict(t1='%s/T1', ct1='%s/CT1', t2='%s/T2', flair='%s/FLAIR')
    datasource.inputs.subjects = sub_list

    dc_nodes = []
    for i in range(4):
        dc = nipype.MapNode(interface=DicomCheck(), iterfield=['dicom_dir'], name='dc{}'.format(i))
        dc.inputs.working_dir = WORKFLOW_CACHE
        dc_nodes.append(dc)

    converter_nodes = []
    for i in range(4):
        converter = nipype.MapNode(interface=Dcm2niix(),
                                   iterfield=['source_dir', 'out_filename'],
                                   name='converter{}'.format(i))
        converter.inputs.compress = 'y'
        converter.inputs.philips_float = False
        converter.inputs.merge_imgs = False
        converter_nodes.append(converter)

    cc_nodes = []
    for i in range(4):
        check = nipype.MapNode(interface=ConversionCheck(),
                               iterfield=['in_file', 'file_name'],
                               name='check{}'.format(i))
        cc_nodes.append(check)

    bet = nipype.MapNode(interface=HDBet(), iterfield=['input_file'], name='bet')
    bet.inputs.save_mask = 1
    bet.inputs.out_file = 'T1_bet'

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

    tumor_seg  = nipype.MapNode(interface=HDGlioPredict(), iterfield=['t1', 't1c', 't2', 'flair'],
                                name='tumor_segmentation')
    tumor_seg.inputs.out_file = 'segmentation'

    mi = nipype.MapNode(Merge(2), iterfield=['in1', 'in2'],
                        name='merge')

    gtv_seg_data_prep = nipype.MapNode(interface=NNUnetPreparation(),
                                       iterfield=['images'],
                                       name='gtv_seg_data_prep')

    gtv_seg = nipype.MapNode(interface=NNUnetInference(), iterfield=['input_folder'],
                             name='gtv_segmentation')
    gtv_seg.inputs.model_folder = ARGS.model_dir

    datasink = nipype.Node(nipype.DataSink(base_directory=RESULT_DIR), "datasink")
    substitutions = [('T1_bet.nii.gz', 'T1_preproc.nii.gz')]
    for i, sub in enumerate(sub_list):
        substitutions += [('_bet{}/'.format(i), sub+'/')]
        substitutions += [('_tumor_segmentation{}/'.format(i), sub+'/')]
        substitutions += [('_gtv_segmentation{}/'.format(i), sub+'/')]
        substitutions += [('nnunet_inference/subject1', 'GTV_predicted')]
        substitutions += [('/segmentation.nii.gz', '/Tumor_predicted.nii.gz')]
        substitutions += [('_masking0{}/antsregWarped_masked.nii.gz'.format(i),
                           sub+'/'+'CT1_preproc.nii.gz')]
        substitutions += [('_masking1{}/antsregWarped_masked.nii.gz'.format(i),
                           sub+'/'+'T2_preproc.nii.gz')]
        substitutions += [('_masking2{}/antsregWarped_masked.nii.gz'.format(i),
                           sub+'/'+'FLAIR_preproc.nii.gz')]
    datasink.inputs.substitutions =substitutions

    workflow = nipype.Workflow('data_preparation_workflow', base_dir=NIPYPE_CACHE)
    for i, dc_check in enumerate(dc_nodes):
        workflow.connect(datasource, sequences[i], dc_check, 'dicom_dir')
    for i, converter in enumerate(converter_nodes):
        workflow.connect(dc_nodes[i], 'outdir', converter, 'source_dir')
        workflow.connect(dc_nodes[i], 'scan_name', converter, 'out_filename')

    for i, check in enumerate(cc_nodes):
        workflow.connect(dc_nodes[i], 'scan_name', check, 'file_name')
        workflow.connect(converter_nodes[i], 'converted_files', check, 'in_file')

    for i, reg in enumerate(reg_nodes):
        workflow.connect(cc_nodes[i+1], 'out_file', reg, 'input_file')
        workflow.connect(cc_nodes[0], 'out_file', reg, 'ref_file')

    for i, mask in enumerate(apply_mask_nodes):
        workflow.connect(reg_nodes[i], 'reg_file', mask, 'in_file')
        workflow.connect(bet, 'out_mask', mask, 'mask_file')
        workflow.connect(mask, 'out_file', datasink,
                         'results.@{}_preproc'.format(sequences[i+1]))
    workflow.connect(cc_nodes[0], 'out_file', bet, 'input_file')
    workflow.connect(bet, 'out_file', tumor_seg, 't1')
    workflow.connect(apply_mask_nodes[0], 'out_file', tumor_seg, 't1c')
    workflow.connect(apply_mask_nodes[1], 'out_file', tumor_seg, 't2')
    workflow.connect(apply_mask_nodes[2], 'out_file', tumor_seg, 'flair')
    workflow.connect(apply_mask_nodes[0], 'out_file', mi, 'in1')
    workflow.connect(apply_mask_nodes[2], 'out_file', mi, 'in2')
    workflow.connect(mi, 'out', gtv_seg_data_prep, 'images')
    workflow.connect(gtv_seg_data_prep, 'output_folder',
                     gtv_seg, 'input_folder')
    workflow.connect(bet, 'out_file', datasink,
                     'results.@T1_preproc')
    workflow.connect(tumor_seg, 'out_file', datasink,
                     'results.@tumor_seg')
    workflow.connect(gtv_seg, 'output_folder', datasink,
                     'results.@gtv_seg')

    workflow.run(plugin='Linear')
    # workflow.run('MultiProc', plugin_args={'n_procs': 8})
    if CLEAN_CACHE:
        shutil.rmtree(WORKFLOW_CACHE)
        shutil.rmtree(NIPYPE_CACHE)

    print('Done!')
