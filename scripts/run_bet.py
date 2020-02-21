"Script to run brain extraction using HD-BET"
from basecore.workflows.bet import BETWorkflow
from basecore.utils.config import cmdline_input_config, create_subject_list


if __name__ == "__main__":

    PARSER = cmdline_input_config()

    ARGS = PARSER.parse_args()

    BASE_DIR = ARGS.input_dir

    sub_list, BASE_DIR = create_subject_list(BASE_DIR, ARGS.xnat_source,
                                             ARGS.cluster_source,
                                             subjects_to_process=[])

    for sub_id in sub_list:

        print('Processing subject {}'.format(sub_id))

        workflow = BETWorkflow(
            sub_id=sub_id, input_dir=BASE_DIR, work_dir=ARGS.work_dir,
            xnat_source=ARGS.xnat_source, xnat_project_id=ARGS.xnat_project_id,
            xnat_overwrite=ARGS.xnat_overwrite, xnat_sink=ARGS.xnat_sink,
            xnat_processed_session=ARGS.xnat_processed_session,
            cluster_sink=ARGS.cluster_sink, cluster_source=ARGS.cluster_source,
            cluster_project_id=ARGS.cluster_project_id)

        workflow.runner()

    print('Done!')
