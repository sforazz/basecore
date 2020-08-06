"File containing all the workflows related to radiomics analysis"
import nipype
from basecore.interfaces.mitk import Voxelizer
from basecore.interfaces.utils import CheckRTStructures
from basecore.interfaces.pyradiomics import FeatureExtraction
from basecore.workflows.base import BaseWorkflow
import os
from nipype.interfaces.utility import Merge


class RadiomicsWorkflow(BaseWorkflow):

    def __init__(self, regex='(.*GTV.*|.*gtv.*)|(.*CTV.*|.*ctv.*)|(.*PTV.*|.*ptv.*)', roi_selection=True, **kwargs):
        
        super().__init__(**kwargs)
        self.regex = regex
        self.roi_selection = roi_selection

    def datasource(self, modality='ct', **kwargs):

        self.database()
        rt = self.rt
        rt_dose = None
        if rt:
            if rt['physical']:
                rt_dose = '*PHY*.nii.gz'
            elif rt['rbe']:
                rt_dose = '*RBE*.nii.gz'
            elif rt['doses']:
                rt_dose = 'Unused_RTDOSE.nii.gz'
            elif rt['doses_nii']:
                rt_dose = 'RTDOSE.nii.gz'
            else:
                if self.roi_selection:
                    self.roi_selection = False
        else:
            if self.roi_selection:
                self.roi_selection = False
        
        field_template = dict()
        template_args = dict()
        if modality == 'ct':
            if rt_dose is not None:
                field_template['rt_dose'] = '%s/%s/{}'.format(rt_dose)
                template_args['rt_dose'] = [['sub_id', 'rt']]
    
            field_template['rtct_nifti'] = '%s/%s/RTCT.nii.gz'
            template_args['rtct_nifti'] = [['sub_id', 'rt']]
            
            field_template['rts_dcm'] = '%s/%s/RTSTRUCT_used/*dcm'
            template_args['rts_dcm'] = [['sub_id', 'rt']]
    
            field_template['rois'] = '%s/%s/out_struct*'
            template_args['rois'] = [['sub_id', 'rt']]
        elif modality == 'mri':
            for key, value in kwargs.items():
                if key == 'rois':
                    for roi in value:
                        if not roi.endswith('.nii.gz'):
                            roi_name = roi.lower()
                            ext = '.nii.gz'
                        else:
                            roi_name = roi.split('.nii.gz')[0].lower()
                            ext = ''
                        field_template[roi_name] = '%s/%s/{0}{1}'.format(roi, ext)
                        template_args[roi_name] = [['sub_id', 'sessions']]
                elif key == 'images':
                    for image in value:
                        if not image.endswith('.nii.gz'):
                            image_name = image.lower()
                            ext = '.nii.gz'
                        else:
                            image_name = image.split('.nii.gz')[0].lower()
                            ext = ''
                        field_template[image_name] = '%s/%s/{0}{1}'.format(image, ext)
                        template_args[image_name] = [['sub_id', 'sessions']]
        
        field_template.update(self.field_template)
        template_args.update(self.template_args)
        self.outfields = [x for x in field_template.keys()]
        self.field_template = field_template
        self.template_args = template_args

        if self.xnat_source:
            self.input_needed = list(set([self.field_template[it].split('/')[-1].split('.')[0]
                                      for it in self.field_template]))
            self.xnat_datasource()
        elif self.cluster_source:
            self.input_needed = self.outfields[:]
            self.cluster_datasource()

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
                                   name='voxelizer',
                                   nested=False)
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
    
    
    def ref_ct_features_extraction(self, rois=None, base_workflow=None):

        self.datasource()

        datasource = self.data_source
        nipype_cache = self.nipype_cache
        result_dir = self.result_dir
        sub_id = self.sub_id
#         sessions = self.sessions

        workflow = nipype.Workflow('features_extraction_workflow', base_dir=nipype_cache)
    
        datasink = nipype.Node(nipype.DataSink(base_directory=result_dir), "datasink")
        substitutions = [('subid', sub_id)]
        substitutions += [('results/', '{}/'.format(self.workflow_name))]
    
        features = nipype.MapNode(interface=FeatureExtraction(),
                                  iterfield=['input_image', 'rois'],
                                  name='features_extraction')
        features.inputs.parameter_file = '/home/fsforazz/git/core/resources/Params_CT.yaml'
    
#         for i, session in enumerate(sessions):
#             substitutions += [('_features_extraction{}/'.format(i), session+'/')]
        substitutions += [('_features_extraction0/', 'REF/')]
        datasink.inputs.substitutions =substitutions
    
        workflow.connect(datasource, 'reference', features, 'input_image')
        if base_workflow is not None:
            workflow.connect(base_workflow, rois, features, 'rois')
        else:
            workflow.connect(datasource, 'rois', features, 'rois')
        workflow.connect(features, 'feature_files', datasink,
                         'results.subid.@csv_file')
        workflow = self.datasink(workflow, datasink)
    
        return workflow

    def mri_features_extraction(self, rois=[], images=[]):

        self.datasource(modality='mri', rois=rois, images=images)

        datasource = self.data_source
        nipype_cache = self.nipype_cache
        result_dir = self.result_dir
        sub_id = self.sub_id
#         sessions = self.sessions

        workflow = nipype.Workflow('features_extraction_workflow', base_dir=nipype_cache)
    
        datasink = nipype.Node(nipype.DataSink(base_directory=result_dir), "datasink")
        substitutions = [('subid', sub_id)]
        substitutions += [('results/', '{}/'.format(self.workflow_name))]

        for image in images:
            if not image.endswith('.nii.gz'):
                image_name = image.lower()
            else:
                image_name = image.split('.nii.gz')[0].lower()
            for roi in rois:
                if not roi.endswith('.nii.gz'):
                    roi_name = roi.lower()
                else:
                    roi_name = roi.split('.nii.gz')[0].lower()
                features = nipype.MapNode(interface=FeatureExtraction(),
                                          iterfield=['input_image', 'rois'],
                                          name='features_extraction_{}{}'.format(image_name, roi_name))
                features.inputs.parameter_file = '/home/fsforazz/git/core/resources/Params_MR.yaml'
                workflow.connect(datasource, image_name, features, 'input_image')
                workflow.connect(datasource, roi_name, features, 'rois')
                workflow.connect(features, 'feature_files', datasink,
                                 'results.subid.@csv_file_{}{}'.format(image_name, roi_name))
    
                for i, session in enumerate(self.sessions):
                    substitutions += [('_features_extraction_{0}{1}{2}/'
                                       .format(image_name, roi_name, i),
                                       session+'/')]

        datasink.inputs.substitutions =substitutions

        workflow = self.datasink(workflow, datasink)
    
        return workflow

    def workflow_setup(self, ct_feat_ext=False, feat_ext=False, **kwargs):

        if ct_feat_ext:
            workflow = self.ref_ct_features_extraction()
        elif feat_ext:
            images = kwargs['images']
            rois = kwargs['rois']
            workflow = self.mri_features_extraction(rois, images)
        else:
            workflow = self.workflow()

        return workflow
