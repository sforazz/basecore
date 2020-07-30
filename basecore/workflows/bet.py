"Brain extraction workflow"
import nipype
from basecore.interfaces.mic import HDBet
from nipype.interfaces.fsl.utils import Reorient2Std
from basecore.workflows.base import BaseWorkflow
from nipype.interfaces.ants import N4BiasFieldCorrection


class BETWorkflow(BaseWorkflow):
    
    def workflow(self):

        self.datasource()

        datasource = self.data_source
        ref_sequence = self.ref_sequence
        t10 = self.t10
        sub_id = self.sub_id
        result_dir = self.result_dir
        sessions = self.sessions
        nipype_cache = self.nipype_cache

        bet = nipype.MapNode(interface=HDBet(), iterfield=['input_file'],
                             name='bet', serial=True)
        bet.inputs.save_mask = 1
        bet.inputs.out_file = '{}_preproc'.format(ref_sequence.upper())
        
        reorient = nipype.MapNode(interface=Reorient2Std(), iterfield=['in_file'],
                                  name='reorient')
        n4 = nipype.MapNode(interface=N4BiasFieldCorrection(), iterfield=['input_image'],
                                  name='n4')
    
        if t10:
            bet_t10 = nipype.Node(interface=HDBet(), name='t1_0_bet')
            bet_t10.inputs.save_mask = 1
            bet_t10.inputs.out_file = 'T1_0_bet'
            reorient_t10 = nipype.Node(interface=Reorient2Std(), iterfield=['in_file'],
                                  name='reorient_t10')
            n4_t10 = nipype.MapNode(interface=N4BiasFieldCorrection(),
                                    iterfield=['input_image'], name='n4_t10')
    
        datasink = nipype.Node(nipype.DataSink(base_directory=result_dir), "datasink")
    
        substitutions = [('subid', sub_id)]
        substitutions += [('results/', '{}/'.format(self.workflow_name))]
        for i, session in enumerate(sessions):
            
            substitutions += [('_bet{}/'.format(i), session+'/')]
    
        datasink.inputs.substitutions =substitutions
        # Create Workflow
        workflow = nipype.Workflow('brain_extraction_workflow', base_dir=nipype_cache)
    
        workflow.connect(datasource, ref_sequence, reorient, 'in_file')
        workflow.connect(reorient, 'out_file', n4, 'input_image')
        workflow.connect(n4, 'output_image', bet, 'input_file')
        if t10:
            workflow.connect(datasource, 't1_0', reorient_t10, 'in_file')
            workflow.connect(reorient_t10, 'out_file', n4_t10, 'input_image')
            workflow.connect(n4_t10, 'output_image', bet_t10, 'input_file')
            workflow.connect(bet_t10, 'out_file', datasink,
                             'results.subid.T10.@T1_ref_bet')
            workflow.connect(bet_t10, 'out_mask', datasink,
                             'results.subid.T10.@T1_ref_bet_mask')
    
        workflow.connect(bet, 'out_file', datasink,
                         'results.subid.@T1_preproc')
        workflow.connect(bet, 'out_mask', datasink,
                         'results.subid.@T1_mask')

        workflow = self.datasink(workflow, datasink)

        return workflow
