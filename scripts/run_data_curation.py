"Script to run the data curation for any study"
import os
from basecore.workflows.curation import DataCuration
from basecore.utils.config import cmdline_input_config, create_subject_list


if __name__ == "__main__":

    PARSER = cmdline_input_config()

    PARSER.add_argument('--num-cores', '-nc', type=int, default=0,
                        help=('Number of cores to use to run the registration workflow '
                              'in parallel. Default is 0, which means the workflow '
                              'will run linearly.'))
    PARSER.add_argument('--data_sorting', '-ds', action='store_true',
                        help=('Whether or not to sort the data before convertion. '
                              'Default is False'))

    ARGS = PARSER.parse_args()

    BASE_DIR = ARGS.input_dir

    sub_list, BASE_DIR = create_subject_list(BASE_DIR, ARGS.xnat_source,
                                             ARGS.cluster_source,
                                             subjects_to_process=[])

    if ARGS.data_sorting:
        workflow = DataCuration(
            sub_id='', input_dir=BASE_DIR, work_dir=ARGS.work_dir,
            process_rt=True)
        workflow.runner(data_sorting=True)
        BASE_DIR = os.path.join(ARGS.work_dir, 'workflows_output', 'RT_sorted_dir')
        sub_list = os.listdir(BASE_DIR)

    for sub_id in sub_list:

        print('Processing subject {}'.format(sub_id))

        workflow = DataCuration(
            sub_id=sub_id, input_dir=BASE_DIR, work_dir=ARGS.work_dir,
            xnat_source=ARGS.xnat_source, xnat_project_id=ARGS.xnat_project_id,
            xnat_overwrite=ARGS.xnat_overwrite, xnat_sink=ARGS.xnat_sink,
            xnat_processed_session=ARGS.xnat_processed_session, process_rt=True,
            cluster_sink=ARGS.cluster_sink, cluster_source=ARGS.cluster_source,
            cluster_project_id=ARGS.cluster_project_id)

        workflow.runner(cores=ARGS.num_cores)

    print('Done!')
