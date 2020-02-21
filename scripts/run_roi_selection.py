"Script to run brain extraction using HD-BET"
from basecore.utils.utils import check_rtstruct
from basecore.workflows.radiomics import RadiomicsWorkflow
from basecore.utils.config import cmdline_input_config, create_subject_list


if __name__ == "__main__":

    PARSER = cmdline_input_config()
    
    PARSER.add_argument('--roi-selection', '-rs', action='store_true',
                        help=('Whether or not to select the ROI in the RT structure set'
                              'with the highest overlap with the dose distribution. '
                              'Default is False'))
    PARSER.add_argument('--check-rts', action='store_false',
                        help=('Whether or not to check all the RTSTRUCT sets in the input '
                              ' directory to make sure that they contain at least one match'
                              ' for the provided regex. Default is True.'))
    PARSER.add_argument('--regular-expression', '-regex', type=str, default='',
                        help=('Regular expression to be used to extract the corresponding'
                              ' ROIs from the RT structure set. By default it will '
                              'extract any ROI containing GTV, PTV, CTV and Boost '
                              'in the name.'))

    ARGS = PARSER.parse_args()

    BASE_DIR = ARGS.input_dir
    if not ARGS.regular_expression:
        regex = '.*(G|g)(T|t)(V|v).*|.*(P|p)(T|t)(V|v).*|.*(B|b)osst.*|.*(C|c)(T|t)(V|v).*'
    else:
        regex = ARGS.regular_expression
    
    if ARGS.check_rts:
        subjecs_to_process = check_rtstruct(BASE_DIR, regex)
    else:
        subjecs_to_process = []

    sub_list, BASE_DIR = create_subject_list(BASE_DIR, ARGS.xnat_source,
                                             ARGS.cluster_source,
                                             subjects_to_process=subjecs_to_process)

    for sub_id in sub_list:

        print('Processing subject {}'.format(sub_id))

        workflow = RadiomicsWorkflow(
            regex=regex, roi_selection=ARGS.roi_selection,
            sub_id=sub_id, input_dir=BASE_DIR, work_dir=ARGS.work_dir,
            xnat_source=ARGS.xnat_source, xnat_project_id=ARGS.xnat_project_id,
            xnat_overwrite=ARGS.xnat_overwrite, xnat_sink=ARGS.xnat_sink,
            xnat_processed_session=ARGS.xnat_processed_session, process_rt=True,
            cluster_sink=ARGS.cluster_sink, cluster_source=ARGS.cluster_source,
            cluster_project_id=ARGS.cluster_project_id)

        workflow.runner()

    print('Done!')
