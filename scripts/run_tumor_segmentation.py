import os
import argparse
import shutil
from basecore.workflows.registration import apply_transformations
from basecore.workflows.segmentation import tumor_segmentation
from basecore.workflows.datahandler import (
    segmentation_datasource, xnat_datasink)
from basecore.database.pyxnat import get
from basecore.database.base import get_subject_list
from basecore.utils.utils import check_already_downloaded


if __name__ == "__main__":

    PARSER = argparse.ArgumentParser()

    PARSER.add_argument('--input_dir', '-i', type=str,
                        help=('Exisisting directory with the subject(s) to process'))
    PARSER.add_argument('--work_dir', '-w', type=str,
                        help=('Directory where to store the results.'))
    PARSER.add_argument('--gtv_seg_model_dir', '-gtv_md', type=str, default='None',
                        help=('Directory with the model parameters, trained with nnUNet.'))
    PARSER.add_argument('--tumor_seg_model_dir', '-tumor_md', type=str, default='None',
                        help=('Directory with the model parameters, trained with nnUNet.'))
    PARSER.add_argument('--normalize', '-n', action='store_true',
                        help=('Whether or not to normalize the segmented tumors to the '
                              '"reference" and/or "T10" images, if present.'))
    PARSER.add_argument('--clean-cache', '-c', action='store_true',
                        help=('To remove all the intermediate files. Enable this only '
                              'when you are sure that the workflow is running properly '
                              'otherwise it will always restart from scratch. '
                              'Default False.'))
    PARSER.add_argument('--xnat-sink', '-xs', action='store_true',
                        help=('Whether or not to upload the processed files to XNAT. '
                              'Default is False'))
    PARSER.add_argument('--xnat-source', action='store_true',
                        help=('Whether or not to source data from XNAT. '
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
    NIPYPE_CACHE_BASE = os.path.join(ARGS.work_dir, 'nipype_cache')
    RESULT_DIR = os.path.join(ARGS.work_dir, 'segmentation_results')
    CLEAN_CACHE = ARGS.clean_cache

    if (os.path.isdir(BASE_DIR) and ARGS.xnat_source) or os.path.isdir(BASE_DIR):
        sub_list = os.listdir(BASE_DIR)
    elif ARGS.xnat_source and not os.path.isdir(BASE_DIR):
        BASE_DIR = os.path.join(BASE_DIR, 'xnat_cache')
        sub_list = get_subject_list(
            ARGS.xnat_pid, user=ARGS.xnat_user, pwd=ARGS.xnat_pwd,
            url=ARGS.xnat_url)

    for sub_id in sub_list:

        print('Processing subject {}'.format(sub_id))
        NIPYPE_CACHE = os.path.join(NIPYPE_CACHE_BASE, sub_id)

        datasource, sessions, reference, t10, sequences, ref_sequence, xnat_scans = segmentation_datasource(
            sub_id, BASE_DIR, apply_transform=True, xnat_source=ARGS.xnat_source)

        if ARGS.xnat_source:
            skip_sessions = check_already_downloaded(sessions, xnat_scans, sub_id, BASE_DIR)
            if [x for x in sessions if x not in skip_sessions]:
                get(ARGS.xnat_pid, BASE_DIR, user=ARGS.xnat_user, pwd=ARGS.xnat_pwd,
                    url=ARGS.xnat_url, processed=True, subjects=[sub_id], needed_scans=xnat_scans,
                    skip_sessions=skip_sessions)

        workflow_runner, hd_glio = tumor_segmentation(
            datasource, sub_id, sessions, ARGS.gtv_seg_model_dir,
            ARGS.tumor_seg_model_dir, RESULT_DIR, NIPYPE_CACHE, reference,
            t10=t10, sequences=sequences, ref_sequence=[ref_sequence])
        
        if ARGS.normalize:
            to_transform = {'gtv_segmentation.output_file': 'subject1',
                            'tumor_seg_2mods.output_file': 'subject1'}
            if hd_glio:
                to_transform['tumor_segmentation.out_file'] = 'segmentation'
            workflow_runner = apply_transformations(
                datasource, workflow_runner, t10, reference, NIPYPE_CACHE,
                sub_id, sessions, RESULT_DIR, sequences=sequences,
                ref_sequence=ref_sequence, to_transform=to_transform)

        workflow_runner.run(plugin='Linear', plugin_args={'job_finished_timeout': 15})

        if ARGS.xnat_sink:
            xnat_datasink(ARGS.xnat_pid, sub_id, os.path.join(RESULT_DIR, 'results'),
                          ARGS.xnat_user, ARGS.xnat_pwd, url=ARGS.xnat_url, processed=True)

        if CLEAN_CACHE:
            shutil.rmtree(NIPYPE_CACHE)

    print('Done!')
