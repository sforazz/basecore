"Segmentation workflows"
import nipype
from nipype.interfaces.utility import Merge
from basecore.interfaces.utils import NNUnetPreparation
from basecore.interfaces.mic import HDGlioPredict, NNUnetInference
from basecore.workflows.base import BaseWorkflow
from nipype.interfaces.ants import ApplyTransforms


NEEDED_SEQUENCES = ['t1', 'ct1', 't2', 'flair']


class TumorSegmentation(BaseWorkflow):
    
    def __init__(self, gtv_model, tumor_model, normalize=True, **kwargs):
        
        super().__init__(**kwargs)
        self.gtv_model = gtv_model
        self.tumor_model = tumor_model
        self.normalize = normalize
    
    def datasource(self):

        self.database()
        normalize = self.normalize

        reference = self.reference
        t10 = self.t10
        ref_sequence = self.ref_sequence
        sequences = self.sequences
        
        field_template = dict()
        template_args = dict()
    
        if reference and normalize:
            field_template['t12ct_mat'] = '%s/%s/{}_regT1_ref2CT.mat'.format(ref_sequence.upper())
            template_args['t12ct_mat'] = [['sub_id', 'sessions']]
        if t10 and normalize:
            field_template['reg2t1_warp'] = '%s/%s/{}_reg2T1_ref_warp.nii.gz'.format(ref_sequence.upper())
            field_template['reg2t1_mat'] = '%s/%s/{}_reg2T1_ref.mat'.format(ref_sequence.upper())
            template_args['reg2t1_warp'] = [['sub_id', 'sessions']]
            template_args['reg2t1_mat'] = [['sub_id', 'sessions']]
        for seq in sequences+[ref_sequence]:
            field_template['{}_preproc'.format(seq)] = '%s/%s/{}_preproc.nii.gz'.format(seq.upper())
            template_args['{}_preproc'.format(seq)] = [['sub_id', 'sessions']]
        
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

        tumor_model = self.tumor_model
        gtv_model = self.gtv_model
        datasource = self.data_source
        ref_sequence = [self.ref_sequence]
        sequences = self.sequences
        sub_id = self.sub_id
        result_dir = self.result_dir
        nipype_cache = self.nipype_cache
        sessions = self.sessions

        sequences = ref_sequence+sequences
        if 't1km' in sequences:
            sequences.remove('t1km')
            sequences.append('ct1')
            ct1 = 't1km'
        else:
            ct1 = 'ct1'
    
        not_found = [x for x in sequences+NEEDED_SEQUENCES
                     if x not in sequences or x not in NEEDED_SEQUENCES]
        if not_found:
            print('{} sequences were provided. Tumor segmentation with HD-GLIO cannot be performed'
                  .format(' '.join(not_found)))
            hd_glio = False
        else:
            hd_glio = True
        if not_found and 'ct1' in not_found or 'flair' in not_found:
            raise Exception('T1 post contrast agent and/or FLAIR were not provided.'
                            ' Nor tumor neither GTV segmentation can be performed.')
    
        if hd_glio:
            tumor_seg  = nipype.MapNode(interface=HDGlioPredict(),
                                        iterfield=['t1', 'ct1', 't2', 'flair'],
                                        name='tumor_segmentation')
            tumor_seg.inputs.out_file = 'segmentation'
    
        mi = nipype.MapNode(Merge(2), iterfield=['in1', 'in2'],
                            name='merge')
    
        gtv_seg_data_prep = nipype.MapNode(interface=NNUnetPreparation(),
                                           iterfield=['images'],
                                           name='gtv_seg_data_prep')
    
        gtv_seg = nipype.MapNode(interface=NNUnetInference(), iterfield=['input_folder'],
                                 name='gtv_segmentation')
        gtv_seg.inputs.model_folder = gtv_model
        gtv_seg.inputs.prefix = 'gtv'
    
        tumor_seg_2mods = nipype.MapNode(interface=NNUnetInference(), iterfield=['input_folder'],
                                 name='tumor_seg_2mods')
        tumor_seg_2mods.inputs.model_folder = tumor_model
        tumor_seg_2mods.inputs.prefix = 'tumor_2mod'
    
        datasink = nipype.Node(nipype.DataSink(base_directory=result_dir), "datasink")
    
        substitutions = [('/segmentation.nii.gz', '/Tumor_predicted.nii.gz')]
        substitutions += [('subid', sub_id)]
        substitutions += [('results/', '{}/'.format(self.workflow_name))]

        for i, session in enumerate(sessions):
            substitutions += [('_tumor_segmentation{}/'.format(i), session+'/')]
            substitutions += [('_gtv_segmentation{}/subject1'.format(i),
                               session+'/GTV_predicted')]
            substitutions += [('nnunet_inference_gtv/subject1'.format(i),
                               session+'/GTV_predicted')]
            substitutions += [('_tumor_seg_2mods{}/subject1'.format(i),
                               session+'/Tumor_predicted_2modalities')]
            substitutions += [('nnunet_inference_tumor_2mod/subject1'.format(i),
                               session+'/Tumor_predicted_2modalities')]
        datasink.inputs.substitutions =substitutions
    
        # Create Workflow
        workflow = nipype.Workflow('tumor_segmentation_workflow', base_dir=nipype_cache)
        
        workflow.connect(datasource, '{}_preproc'.format(ct1), mi, 'in1')
        workflow.connect(datasource, 'flair_preproc', mi, 'in2')
        if hd_glio:
            workflow.connect(datasource, '{}_preproc'.format(ct1), tumor_seg, 'ct1')
            workflow.connect(datasource, 't2_preproc', tumor_seg, 't2')
            workflow.connect(datasource, 'flair_preproc', tumor_seg, 'flair')
            workflow.connect(datasource, 't1_preproc', tumor_seg, 't1')
    
        # Nodes to prepare the data before nnUNet inference
        workflow.connect(mi, 'out', gtv_seg_data_prep, 'images')
    
        # Nodes to segment GTV and tumor using nnUNet
        workflow.connect(gtv_seg_data_prep, 'output_folder',
                         gtv_seg, 'input_folder')
        workflow.connect(gtv_seg_data_prep, 'output_folder',
                         tumor_seg_2mods, 'input_folder')
    
        if hd_glio:
            workflow.connect(tumor_seg, 'out_file', datasink,
                             'results.subid.@tumor_seg')
        workflow.connect(gtv_seg, 'output_file', datasink,
                         'results.subid.@gtv_seg')
        workflow.connect(tumor_seg_2mods, 'output_file', datasink,
                         'results.subid.@tumor_seg_2mods')
    
        if self.normalize and (self.reference or self.t10):
            self.to_transform = {'gtv_segmentation.output_file': 'subject1',
                                 'tumor_seg_2mods.output_file': 'subject1'}
            if hd_glio:
                self.to_transform['tumor_segmentation.out_file'] = 'segmentation'
            self.seg_workflow = workflow
            workflow = self.apply_transformations()
        else:
            workflow = self.datasink(workflow, datasink)

        return workflow

    def apply_transformations(self):
        
        base_workflow = self.seg_workflow

        datasource = self.data_source
        to_transform = self.to_transform

        workflow = nipype.Workflow('apply_transformations_workflow',
                                   base_dir=self.nipype_cache)
        datasink = nipype.Node(nipype.DataSink(base_directory=self.result_dir), "datasink")
    
        substitutions = [('subid', self.sub_id)]
        substitutions += [('results/', 'tumor_segmentation_results/')]
        for image in to_transform:
            base_name = image.replace('.', '_')
            outname = image.split('.')[0].upper()
            if self.reference:
                apply_ts_ref = nipype.MapNode(interface=ApplyTransforms(),
                                              iterfield=['input_image', 'transforms'],
                                              name='apply_ts_ref{}'.format(base_name))
                apply_ts_ref.inputs.interpolation = 'NearestNeighbor'
        
                workflow.connect(datasource, 'reference', apply_ts_ref, 'reference_image')
                if self.t10:
                    merge_ref_ts = nipype.MapNode(interface=Merge(3),
                                                  iterfield=['in1', 'in2', 'in3'],
                                                  name='merge_ct_ts{}'.format(base_name))
                    workflow.connect(datasource, 't12ct_mat', merge_ref_ts, 'in1')
                    workflow.connect(datasource, 'reg2t1_warp', merge_ref_ts, 'in2')
                    workflow.connect(datasource, 'reg2t1_mat', merge_ref_ts, 'in3')
                    workflow.connect(merge_ref_ts, 'out', apply_ts_ref, 'transforms')
                else:
                    workflow.connect(datasource, 't12ct_mat', apply_ts_ref, 'transforms')
                workflow.connect(base_workflow, image, apply_ts_ref, 'input_image')
                workflow.connect(apply_ts_ref, 'output_image', datasink,
                                 'results.subid.@{}_reg2ref'.format(base_name))
        
            if self.t10:
                merge_t10_ts = nipype.MapNode(interface=Merge(2),
                                              iterfield=['in1', 'in2'],
                                              name='merge_t10_ts{}'.format(base_name))
                apply_ts_t10 = nipype.MapNode(interface=ApplyTransforms(),
                                              iterfield=['input_image', 'transforms'],
                                              name='apply_ts_t10{}'.format(base_name))
                apply_ts_t10.inputs.interpolation = 'NearestNeighbor'
        
                workflow.connect(datasource, 't1_0', apply_ts_t10, 'reference_image')
                workflow.connect(datasource, 'reg2t1_warp', merge_t10_ts, 'in1')
                workflow.connect(datasource, 'reg2t1_mat', merge_t10_ts, 'in2')
                workflow.connect(merge_t10_ts, 'out', apply_ts_t10, 'transforms')
            
                workflow.connect(base_workflow, image, apply_ts_t10, 'input_image')
                workflow.connect(apply_ts_t10, 'output_image', datasink,
                                 'results.subid.@{}_reg2T10'.format(base_name))
     
            for i, session in enumerate(self.sessions):
                substitutions += [('_apply_ts_t10{0}{1}/{2}_trans.nii.gz'
                                   .format(base_name, i, to_transform[image]),
                                   session+'/'+'{}_reg2T1ref.nii.gz'.format(outname))]
                substitutions += [('_apply_ts_ref{0}{1}/{2}_trans.nii.gz'
                                   .format(base_name, i, to_transform[image]),
                                   session+'/'+'{}_reg2CT.nii.gz'.format(outname))]
    
        datasink.inputs.substitutions =substitutions

        workflow = self.datasink(workflow, datasink)
    
        return workflow
