"Script to run image registration"
import os
import argparse
import shutil
from basecore.workflows.datahandler import (
    registration_datasource, xnat_datasink)
from basecore.workflows.registration import brain_registration
from basecore.database.pyxnat import get
from basecore.utils.utils import check_already_downloaded


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
    PARSER.add_argument('--xnat-source', action='store_true',
                        help=('Whether or not to source data from XNAT. '
                              'Default is False'))
    PARSER.add_argument('--xnat-sink', '-xs', action='store_true',
                        help=('Whether or not to upload the processed files to XNAT. '
                              'Default is False'))
    PARSER.add_argument('--overwrite', '-ow', action='store_true',
                        help=('Whether or not to delete existing session on XNAT. '
                              'Default is False'))
    PARSER.add_argument('--xnat-url', '-xurl', type=str, default='https://central.xnat.org',
                        help=('If xnat-sink, the url of the server must be provided here. '
                              'Default is https://central.xnat.org'))#
    PARSER.add_argument('--xnat-pid', '-xpid', type=str,
                        help=('If xnat-sink, the project ID o the server where to upload '
                              'the results must be provided here.'))
    PARSER.add_argument('--xnat-user', '-xuser', type=str,
                        help=('If xnat-sink, the username on the server must be provided here.'))
    PARSER.add_argument('--xnat-pwd', '-xpwd', type=str,
                        help=('If xnat-sink, the password on the server must be provided here.'))

    ARGS = PARSER.parse_args()

    BASE_DIR = ARGS.input_dir
    WORKFLOW_CACHE = os.path.join(ARGS.work_dir, 'temp_dir')
    NIPYPE_CACHE_BASE = os.path.join(ARGS.work_dir, 'nipype_cache')
    RESULT_DIR = os.path.join(ARGS.work_dir, 'registration_results')
    CLEAN_CACHE = ARGS.clean_cache
    CORES = ARGS.num_cores

    sub_list = os.listdir(BASE_DIR)

    print('Number of subjects: {}'.format(len(sub_list)))

    for sub_id in sub_list:
        ready = False
        NIPYPE_CACHE = os.path.join(NIPYPE_CACHE_BASE, sub_id)
        datasource, sessions, reference, t10, sequences, ref_sequence, xnat_scans = registration_datasource(
            sub_id, BASE_DIR)
        if ARGS.xnat_source:
            skip_sessions = check_already_downloaded(sessions, xnat_scans, sub_id, BASE_DIR)
            if not [x for x in sessions if x not in skip_sessions]:
                get(ARGS.xnat_pid, BASE_DIR, user=ARGS.xnat_user, pwd=ARGS.xnat_pwd,
                    url=ARGS.xnat_url, processed=True, subjects=[sub_id], needed_scans=xnat_scans,
                    skip_sessions=skip_sessions)

        workflow = brain_registration(
            sub_id, datasource, sessions, reference, RESULT_DIR,
            NIPYPE_CACHE, t10=t10, sequences=sequences,
            ref_sequence=ref_sequence)

        if CORES == 0:
            print('The workflow will run linearly.')
            workflow.run(plugin='Linear')
        else:
            print('The workflow will run in parallel using {} cores'
                  .format(CORES))
            workflow.run('MultiProc', plugin_args={'n_procs': CORES})

        if ARGS.xnat_sink:
            print('Uploading the results to XNAT with the following parameters:')
            print('Server: {}'.format(ARGS.xnat_url))
            print('Project ID: {}'.format(ARGS.xnat_pid))
            print('User ID: {}'.format(ARGS.xnat_user))

            xnat_datasink(ARGS.xnat_pid, sub_id, os.path.join(RESULT_DIR, 'results'),
                          ARGS.xnat_user, ARGS.xnat_pwd, url=ARGS.xnat_url, processed=True,
                          overwrite=ARGS.overwrite)

            print('Uploading successfully completed!')
        if CLEAN_CACHE:
            shutil.rmtree(NIPYPE_CACHE)

    print('Done!')
