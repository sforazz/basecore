"Brain extraction workflow"
import nipype
from basecore.interfaces.mic import HDBet
from basecore.workflows.datahandler import datasink_base


def brain_extraction(sub_id, datasource, sessions,
                     RESULT_DIR, NIPYPE_CACHE, reference):

    bet = nipype.MapNode(interface=HDBet(), iterfield=['input_file'], name='bet')
    bet.inputs.save_mask = 1
    bet.inputs.out_file = 'T1_preproc'

    bet_t10 = nipype.Node(interface=HDBet(), name='t1_0_bet')
    bet_t10.inputs.save_mask = 1
    bet_t10.inputs.out_file = 'T1_0_bet'

    datasink = nipype.Node(nipype.DataSink(base_directory=RESULT_DIR), "datasink")

    substitutions = [('subid', sub_id)]
    for i, session in enumerate(sessions):
        
        substitutions += [('_bet{}/'.format(i), session+'/')]

    datasink.inputs.substitutions =substitutions
    # Create Workflow
    workflow = nipype.Workflow('brain_extraction_workflow', base_dir=NIPYPE_CACHE)

    workflow.connect(datasource, 't1', bet, 'input_file')
    workflow.connect(datasource, 't1_0', bet_t10, 'input_file')

    workflow.connect(bet, 'out_file', datasink,
                     'results.subid.@T1_preproc')
    workflow.connect(bet, 'out_mask', datasink,
                     'results.subid.@T1_mask')
    workflow.connect(bet_t10, 'out_file', datasink,
                     'results.subid.T10.@T1_ref_bet')

    workflow = datasink_base(datasink, datasource, workflow, sessions, reference)

    return workflow
