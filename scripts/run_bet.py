"Script to run the tumor segmentation using HD-GLIO"
import os
import argparse
import shutil
from basecore.workflows.datahandler import gbm_datasource,\
    cinderella_tp0_datasource
from basecore.workflows.bet import brain_extraction


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
    PARSER.add_argument('--single-tp', '-s', action='store_true',
                        help=('Whether or not to run bet for single time point or for multi '
                              'timepoints project.'
                              'Default multi-timepoints.'))

    ARGS = PARSER.parse_args()

    BASE_DIR = ARGS.input_dir
    WORKFLOW_CACHE = os.path.join(ARGS.work_dir, 'temp_dir')
    NIPYPE_CACHE_BASE = os.path.join(ARGS.work_dir, 'nipype_cache')
    RESULT_DIR = os.path.join(ARGS.work_dir, 'bet_results')
    CLEAN_CACHE = ARGS.clean_cache

    
    sub_list = os.listdir(BASE_DIR)

    for sub_id in sub_list:
        NIPYPE_CACHE = os.path.join(NIPYPE_CACHE_BASE, sub_id)
        if ARGS.single_tp:
            datasource, sessions, reference = cinderella_tp0_datasource(sub_id, BASE_DIR)
        else:
            datasource, sessions, reference = gbm_datasource(sub_id, BASE_DIR)
        workflow = brain_extraction(
            sub_id, datasource, sessions, RESULT_DIR, NIPYPE_CACHE, reference,
            t10= not ARGS.single_tp)
        workflow.run(plugin='Linear')
        if CLEAN_CACHE:
            shutil.rmtree(NIPYPE_CACHE)

    print('Done!')
