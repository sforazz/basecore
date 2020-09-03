"Script to run brain extraction using HD-BET"
from basecore.workflows.radiomics import RadiomicsWorkflow
from basecore.utils.config import cmdline_input_config, create_subject_list
from basecore.utils.utils import check_data


if __name__ == "__main__":

    PARSER = cmdline_input_config()

    PARSER.add_argument('--num-cores', '-nc', type=int, default=0,
                        help=('Number of cores to use to run the registration workflow '
                              'in parallel. Default is 0, which means the workflow '
                              'will run linearly.'))

    ARGS = PARSER.parse_args()

    BASE_DIR = ARGS.input_dir
    
    for i in range(1, 27):
        print('Processing sphere {}'.format(i))
        image2process = 'CT1'
        mask2process = ['cluster_1_tumor_mask_sphere000{}'.format(str(i).zfill(2))]
        
        subjecs_to_process = check_data(BASE_DIR, image2process, masks=mask2process)
        print(len(subjecs_to_process))
        sub_list, BASE_DIR = create_subject_list(BASE_DIR, ARGS.xnat_source,
                                                 ARGS.cluster_source,
                                                 subjects_to_process=subjecs_to_process)
    
        for sub_id in sub_list:
    
            print('Processing subject {}'.format(sub_id))
    
            workflow = RadiomicsWorkflow(
                sub_id=sub_id, input_dir=BASE_DIR, work_dir=ARGS.work_dir,
                xnat_source=ARGS.xnat_source, xnat_project_id=ARGS.xnat_project_id,
                xnat_overwrite=ARGS.xnat_overwrite, xnat_sink=ARGS.xnat_sink,
                xnat_processed_session=ARGS.xnat_processed_session, process_rt=True,
                cluster_sink=ARGS.cluster_sink, cluster_source=ARGS.cluster_source,
                cluster_project_id=ARGS.cluster_project_id)
    
            wf = workflow.workflow_setup(feat_ext=True, images=[image2process],
                                         rois=mask2process)
            workflow.runner(wf, cores=ARGS.num_cores)

    print('Done!')
