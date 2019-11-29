import os
import argparse
import shutil
from basecore.workflows.registration import longitudinal_registration
from basecore.workflows.segmentation import tumor_segmentation
from basecore.workflows.bet import brain_extraction
from basecore.workflows.datahandler import (
    gbm_datasource, segmentation_datasource, registration_datasource)


if __name__ == "__main__":

    PARSER = argparse.ArgumentParser()

    PARSER.add_argument('--input_dir', '-i', type=str,
                        help=('Exisisting directory with the subject(s) to process'))
    PARSER.add_argument('--work_dir', '-w', type=str,
                        help=('Directory where to store the results.'))
    PARSER.add_argument('--run_registration', '-reg', action='store_true',
                        help=('Whether or not to run registration before segmentation.'
                              ' Default is False.'))
    PARSER.add_argument('--run_bet', '-bet', action='store_true',
                        help=('Whether or not to run brain extraction before registration.'
                              ' Default is False.'))
    PARSER.add_argument('--gtv_seg_model_dir', '-gtv_md', type=str, default='None',
                        help=('Directory with the model parameters, trained with nnUNet.'))
    PARSER.add_argument('--tumor_seg_model_dir', '-tumor_md', type=str, default='None',
                        help=('Directory with the model parameters, trained with nnUNet.'))
    PARSER.add_argument('--clean-cache', '-c', action='store_true',
                        help=('To remove all the intermediate files. Enable this only '
                              'when you are sure that the workflow is running properly '
                              'otherwise it will always restart from scratch. '
                              'Default False.'))

    ARGS = PARSER.parse_args()

    if ARGS.run_registration:
        BASE_DIR = ARGS.input_dir
    else:
        BASE_DIR = os.path.join(ARGS.work_dir, 'registration_results',
                                'results')
    WORKFLOW_CACHE = os.path.join(ARGS.work_dir, 'temp_dir')
    NIPYPE_CACHE_BASE = os.path.join(ARGS.work_dir, 'nipype_cache')
    RESULT_DIR = os.path.join(ARGS.work_dir, 'segmentation_results')
    CLEAN_CACHE = ARGS.clean_cache

    sub_list = os.listdir(BASE_DIR)

    for sub_id in sub_list:
        NIPYPE_CACHE = os.path.join(NIPYPE_CACHE_BASE, sub_id)
        if ARGS.run_registration:
            if ARGS.run_bet:
                datasource, sessions, reference = gbm_datasource(sub_id, BASE_DIR)
                bet_workflow = brain_extraction(
                    sub_id, datasource, sessions, RESULT_DIR, NIPYPE_CACHE, reference)
            else:
                datasource, sessions = registration_datasource(
                    sub_id, os.path.join(ARGS.work_dir, 'bet_results', 'results'))
                bet_workflow = None

            reg_workflow = longitudinal_registration(
                sub_id, datasource, sessions, reference, RESULT_DIR,
                NIPYPE_CACHE, bet_workflow=bet_workflow)
        else:
            datasource, sessions, reference = segmentation_datasource(
                sub_id, os.path.join(ARGS.work_dir, 'registration_results', 'results'))
            reg_workflow = None
            bet_workflow = None

        seg_workflow = tumor_segmentation(
            datasource, sub_id, sessions, ARGS.gtv_seg_model_dir,
            ARGS.tumor_seg_model_dir, RESULT_DIR, NIPYPE_CACHE, reference,
            reg_workflow=reg_workflow, bet_workflow=bet_workflow)

        seg_workflow.run(plugin='Linear')
        if CLEAN_CACHE:
            shutil.rmtree(NIPYPE_CACHE)

    print('Done!')
