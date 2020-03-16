"Script to run brain extraction using HD-BET"
from basecore.workflows.radiomics import RadiomicsWorkflow
from basecore.utils.config import cmdline_input_config, create_subject_list


if __name__ == "__main__":

    PARSER = cmdline_input_config()

    PARSER.add_argument('--num-cores', '-nc', type=int, default=0,
                        help=('Number of cores to use to run the registration workflow '
                              'in parallel. Default is 0, which means the workflow '
                              'will run linearly.'))

    ARGS = PARSER.parse_args()

    BASE_DIR = ARGS.input_dir

    sub_list, BASE_DIR = create_subject_list(BASE_DIR, ARGS.xnat_source,
                                             ARGS.cluster_source,
                                             subjects_to_process=[])

    for sub_id in sub_list:

        print('Processing subject {}'.format(sub_id))

        workflow = RadiomicsWorkflow(
            sub_id=sub_id, input_dir=BASE_DIR, work_dir=ARGS.work_dir,
            xnat_source=ARGS.xnat_source, xnat_project_id=ARGS.xnat_project_id,
            xnat_overwrite=ARGS.xnat_overwrite, xnat_sink=ARGS.xnat_sink,
            xnat_processed_session=ARGS.xnat_processed_session, process_rt=True,
            cluster_sink=ARGS.cluster_sink, cluster_source=ARGS.cluster_source,
            cluster_project_id=ARGS.cluster_project_id)

        wf = workflow.workflow_setup(feat_ext=True, images=['FLAIR_preproc', 'T1KM_preproc'],
                                     rois=['GTV_predicted'])
        workflow.runner(wf, cores=ARGS.num_cores)

    print('Done!')
