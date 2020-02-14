import os
import argparse
from basecore.database.base import get_subject_list
from basecore.workflows.segmentation import TumorSegmentation


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
    PARSER.add_argument('--xnat-sink', '-xs', action='store_true',
                        help=('Whether or not to upload the processed files to XNAT. '
                              'Default is False'))
    PARSER.add_argument('--xnat-source', action='store_true',
                        help=('Whether or not to source data from XNAT. '
                              'Default is False'))
    PARSER.add_argument('--xnat-project-id', '-xpid', type=str,
                        help=('XNAT project ID. If not provided, and xnat-source and/or '
                              'xnat-sink were selected, you will be prompted to enter it.'))
    PARSER.add_argument('--xnat-overwrite', action='store_true',
                        help=('Whether or not to delete existing subject on XNAT, if xnat-sink'
                              ' is selected. Default is False'))
    PARSER.add_argument('--xnat-processed-session', action='store_false',
                        help=('Whether or not download/upload data from/to a "processed" '
                              'session (i.e. "_processed" is in the name of the sessions).'
                              ' This should be false only if you work with DICOM RAW data, '
                              'otherwise True. Default is True.'))

    ARGS = PARSER.parse_args()

    BASE_DIR = ARGS.input_dir

    if (os.path.isdir(BASE_DIR) and ARGS.xnat_source) or os.path.isdir(BASE_DIR):
        sub_list = os.listdir(BASE_DIR)
    elif ARGS.xnat_source and not os.path.isdir(BASE_DIR):
        BASE_DIR = os.path.join(BASE_DIR, 'xnat_cache')
        sub_list = get_subject_list(
            ARGS.xnat_pid, user=ARGS.xnat_user, pwd=ARGS.xnat_pwd,
            url=ARGS.xnat_url)

    for sub_id in sub_list:

        print('Processing subject {}'.format(sub_id))

        workflow = TumorSegmentation(
            ARGS.gtv_seg_model_dir, ARGS.tumor_seg_model_dir,
            sub_id=sub_id, input_dir=BASE_DIR, work_dir=ARGS.work_dir,
            xnat_source=ARGS.xnat_source, xnat_project_id=ARGS.xnat_project_id,
            xnat_overwrite=ARGS.xnat_overwrite, xnat_sink=ARGS.xnat_sink,
            xnat_processed_session=ARGS.xnat_processed_session)
        workflow.runner()

    print('Done!')
