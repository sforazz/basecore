"Script to run the data curation for any study"
import os
import argparse
import shutil
from basecore.workflows.datahandler import base_datasource
from basecore.workflows.curation import convertion


if __name__ == "__main__":

    PARSER = argparse.ArgumentParser()

    PARSER.add_argument('--input_dir', '-i', type=str,
                        help=('Exisisting directory with the subject(s) to process'))
    PARSER.add_argument('--work_dir', '-w', type=str,
                        help=('Directory where to store the results.'))
    PARSER.add_argument('--num-cores', '-nc', type=int, default=0,
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
    RESULT_DIR = os.path.join(ARGS.work_dir, 'data_curated')
    CLEAN_CACHE = ARGS.clean_cache
    CORES = ARGS.num_cores

    
    sub_list = os.listdir(BASE_DIR)

    for sub_id in sub_list:
        NIPYPE_CACHE = os.path.join(NIPYPE_CACHE_BASE, sub_id)
        datasource, sessions, reference, t10, sequences, ref_sequence, rt_data = base_datasource(
            sub_id, BASE_DIR, process_rt=True)
        workflow = convertion(sub_id, datasource, sessions, reference,
                              RESULT_DIR, NIPYPE_CACHE, rt_data,
                              t10, sequences, ref_sequence)

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
