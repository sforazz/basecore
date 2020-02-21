"File containing all the workflows related to radiomics analysis"
import nipype
from basecore.interfaces.mitk import Voxelizer
from basecore.interfaces.utils import CheckRTStructures
from basecore.interfaces.pyradiomics import FeatureExtraction
from basecore.workflows.base import BaseWorkflow


class RadiomicsWorkflow(BaseWorkflow):

    def __init__(self, regex, roi_selection=False, **kwargs):
        
        super().__init__(**kwargs)
        self.regex = regex
        self.roi_selection = roi_selection

    def datasource(self):

        self.database()
        rt = self.rt

        if rt:
            if rt['physical']:
                rt_dose = '*PHY*.nii.gz'
            elif rt['rbe']:
                rt_dose = '*RBE*.nii.gz'
            elif rt['doses']:
                rt_dose = 'Unused_RTDOSE.nii.gz'
            else:
                if self.roi_selection:
                    self.roi_selection = False
        else:
            if self.roi_selection:
                self.roi_selection = False
        
        field_template = dict()
        template_args = dict()

        field_template['rt_dose'] = '%s/%s/{}'.format(rt_dose)
        template_args['rt_dose'] = [['sub_id', 'rt']]

        field_template['rtct_nifti'] = '%s/%s/RTCT.nii.gz'
        template_args['rtct_nifti'] = [['sub_id', 'rt']]
        
        field_template['rts_dcm'] = '%s/%s/RTSTRUCT_used/*dcm'
        template_args['rts_dcm'] = [['sub_id', 'rt']]
        
        field_template.update(self.field_template)
        template_args.update(self.template_args)
        self.outfields = [x for x in field_template.keys()]
        self.field_template = field_template
        self.template_args = template_args

        if self.xnat_source:
            self.xnat_scan_ids = list(set([self.field_template[it].split('/')[-1].split('.')[0]
                                      for it in self.field_template]))
            self.xnat_datasource()

        self.data_source = self.create_datasource()

    def workflow(self):

        self.datasource()

        datasource = self.data_source
        nipype_cache = self.nipype_cache
        result_dir = self.result_dir
        sub_id = self.sub_id
        regex = self.regex
        roi_selection = self.roi_selection
        
        workflow = nipype.Workflow('rtstruct_extraction_workflow', base_dir=nipype_cache)
    
        datasink = nipype.Node(nipype.DataSink(base_directory=result_dir), "datasink")
        substitutions = [('subid', sub_id)]
#         substitutions += [('RTsession', self.rt['session'])]
        substitutions += [('results/', '{}/'.format(self.workflow_name))]
    
        voxelizer = nipype.MapNode(interface=Voxelizer(),
                                   iterfield=['reference', 'struct_file'],
                                   name='voxelizer')
        voxelizer.inputs.regular_expression = regex
        voxelizer.inputs.multi_structs = True
        voxelizer.inputs.binarization = True
        voxelizer.inputs.no_strict_voxelization = True
        
        if roi_selection:
            select = nipype.MapNode(interface=CheckRTStructures(),
                                    iterfield=['rois', 'dose_file'],
                                    name='select_gtv')
            workflow.connect(voxelizer, 'out_files', select, 'rois')
            workflow.connect(datasource, 'rt_dose', select, 'dose_file')
            workflow.connect(select, 'checked_roi', datasink,
                             'results.subid.@masks')
        else:
            workflow.connect(voxelizer, 'out_files', datasink,
                             'results.subid.@masks')
        
#         for i, session in enumerate(sessions):
        for i, session in enumerate(self.rt['session']):
            substitutions += [(('_select_gtv{}/'.format(i), session+'/'))]
            substitutions += [(('_voxelizer{}/'.format(i), session+'/'))]
#         substitutions += [('_select_gtv0/', '/')]
#         substitutions += [('_voxelizer0/', '/')]
        datasink.inputs.substitutions =substitutions
    
        workflow.connect(datasource, 'rtct_nifti', voxelizer, 'reference')
#         workflow.connect(datasource, 'reference', voxelizer, 'reference')
        workflow.connect(datasource, 'rts_dcm', voxelizer, 'struct_file')

        workflow = self.datasink(workflow, datasink)

        return workflow
    
    
    def ct_features_extraction(self, sub_id, datasource, sessions, result_dir,
                               nipype_cache, base_workflow, rois):
    
        workflow = nipype.Workflow('features_extraction_workflow', base_dir=nipype_cache)
    
        datasink = nipype.Node(nipype.DataSink(base_directory=result_dir), "datasink")
        substitutions = [('subid', sub_id)]
    
        features = nipype.MapNode(interface=FeatureExtraction(),
                                  iterfield=['input_image', 'rois'],
                                  name='features_extraction')
        features.inputs.parameter_file = '/home/fsforazz/Downloads/Params.yaml'
    
        for i, session in enumerate(sessions):
            substitutions += [('_features_extraction{}/'.format(i), session+'/')]
        datasink.inputs.substitutions =substitutions
    
        workflow.connect(datasource, 'reference', features, 'input_image')
        workflow.connect(base_workflow, rois, features, 'rois')
        workflow.connect(features, 'feature_files', datasink, 'features_extraction.@csv_file')
    
        return workflow
