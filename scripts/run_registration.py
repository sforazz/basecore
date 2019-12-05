"Script to run the tumor segmentation using HD-GLIO"
import os
import argparse
import shutil
from basecore.workflows.datahandler import (
    gbm_datasource, registration_datasource)
from basecore.workflows.bet import brain_extraction
from basecore.workflows.registration import longitudinal_registration


if __name__ == "__main__":

    PARSER = argparse.ArgumentParser()

    PARSER.add_argument('--input_dir', '-i', type=str,
                        help=('Exisisting directory with the subject(s) to process'))
    PARSER.add_argument('--work_dir', '-w', type=str,
                        help=('Directory where to store the results.'))
    PARSER.add_argument('--run_bet', '-bet', action='store_true',
                        help=('Whether or not to run registration before segmentation.'
                              ' Default is False.'))
    PARSER.add_argument('--num-cores', '-c', type=int, default=0,
                        help=('Number of cores to use to run the registration workflow '
                              'in parallel. Default is 0, which means the workflow '
                              'will run linearly.'))
    PARSER.add_argument('--clean-cache', '-c', action='store_true',
                        help=('To remove all the intermediate files. Enable this only '
                              'when you are sure that the workflow is running properly '
                              'otherwise it will always restart from scratch. '
                              'Default False.'))

    ARGS = PARSER.parse_args()

    BASE_DIR = ARGS.input_dir
    WORKFLOW_CACHE = os.path.join(ARGS.work_dir, 'temp_dir')
    NIPYPE_CACHE_BASE = os.path.join(ARGS.work_dir, 'nipype_cache')
    RESULT_DIR = os.path.join(ARGS.work_dir, 'registration_results')
    CLEAN_CACHE = ARGS.clean_cache
    CORES = ARGS.num_cores

    if ARGS.run_bet:
        BASE_DIR = ARGS.input_dir
    else:
        BASE_DIR = os.path.join(ARGS.work_dir, 'bet_results',
                                'results')
    sub_list = os.listdir(BASE_DIR)

    for sub_id in sub_list:
        NIPYPE_CACHE = os.path.join(NIPYPE_CACHE_BASE, sub_id)
        if ARGS.run_bet:
            datasource, sessions, reference = gbm_datasource(sub_id, BASE_DIR)
            bet_workflow = brain_extraction(
                sub_id, datasource, sessions, RESULT_DIR, NIPYPE_CACHE,
                reference)
        else:
            datasource, sessions, reference = registration_datasource(
                sub_id, os.path.join(ARGS.work_dir, 'bet_results', 'results'))
            bet_workflow = None

        workflow = longitudinal_registration(
            sub_id, datasource, sessions, reference, RESULT_DIR,
            NIPYPE_CACHE, bet_workflow=bet_workflow)

        if CORES == 0:
            print('The workflow will run linearly.')
            workflow.run(plugin='Linear')
        else:
            print('The workflow will run in parallel using {} cores'
                  .format(CORES))
            workflow.run('MultiProc', plugin_args={'n_procs': CORES})
        if CLEAN_CACHE:
            shutil.rmtree(NIPYPE_CACHE)

    print('Done!')
