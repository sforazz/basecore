import os
import glob
import nipype
from nipype.interfaces.utility import Split
from basecore.utils.utils import check_dcm_dose
from basecore.database.pyxnat import Pyxnat
from basecore.database.base import check_xnat_cache


POSSIBLE_SEQUENCES = ['t1', 'ct1', 't1km', 't2', 'flair']


class BaseDataHandler():

    def __init__(self, sub_id, input_dir, work_dir, process_rt=False,
                 xnat_source=False, xnat_project_id=None,
                 xnat_config=None, xnat_overwrite=False,
                 xnat_processed_session=True, xnat_sink=False):

        self.sub_id = sub_id
        self.base_dir = input_dir
        self.process_rt = process_rt
        self.nipype_cache = os.path.join(work_dir, 'nipype_cache', sub_id)
        self.result_dir = os.path.join(work_dir, 'workflows_output')
        self.xnat_source = xnat_source
        self.xnat_project_id = xnat_project_id
        self.xnat_config = xnat_config
        self.xnat_overwrite = xnat_overwrite
        self.xnat_processed_session = xnat_processed_session
        self.xnat_sink = xnat_sink
        self.xnat_scans_id = []
        self.workflow_name = self.__class__.__name__
        self.outdir = os.path.join(self.result_dir, self.workflow_name)
        if xnat_source:
            self.pyxnat = Pyxnat(self.xnat_config, project_id=self.xnat_project_id,
                                 processed_session=self.xnat_processed_session,
                                 overwrite=self.xnat_overwrite)
    
    def database(self):
        
        base_dir = self.base_dir
        sub_id = self.sub_id

        sessions = [x for x in os.listdir(os.path.join(base_dir, sub_id))
                    if 'REF' not in x and 'T10' not in x and 'RT_' not in x]
        ref_session = [x for x in os.listdir(os.path.join(base_dir, sub_id))
                       if x == 'REF' and os.path.isdir(os.path.join(base_dir, sub_id, x))]
        t10_session = [x for x in os.listdir(os.path.join(base_dir, sub_id))
                       if x == 'T10' and os.path.isdir(os.path.join(base_dir, sub_id, x))]
        rt_session = [x for x in os.listdir(os.path.join(base_dir, sub_id))
                       if 'RT_' in x and os.path.isdir(os.path.join(base_dir, sub_id, x))]

        sequences = list(set([y.split('.nii.gz')[0].lower() for x in sessions
                              for y in os.listdir(os.path.join(base_dir, sub_id, x))
                              if y.endswith('.nii.gz')]))
        if not sequences:
            sequences = list(set([y.lower() for x in sessions
                              for y in os.listdir(os.path.join(base_dir, sub_id, x))
                              if os.path.isdir(os.path.join(base_dir, sub_id, x, y))]))
            ext = ''
        else:
            ext = '.nii.gz'
        sequences = [x for x in sequences if x in POSSIBLE_SEQUENCES]
        if 't1' in sequences:
            ref_sequence = 't1'
        elif 'ct1' in sequences:
            ref_sequence = 'ct1'
        elif 't1km' in sequences:
            ref_sequence = 't1km'
        elif ext == '':
            ref_sequence = ''
        else:
            raise Exception('Nor T1 neither T1KM were found in {}. You need at least one of them '
                            'in order to perform registration.'.format(sub_id))
        if sequences and ref_sequence:
            sequences.remove(ref_sequence)
        if ref_session:
            reference = True
        else:
            print('NO REFERENCE CT!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
            reference = False
    
        if t10_session:
            t10 = True
        else:
            t10 = False
    
        rt = {}
        if rt_session and self.process_rt:
            rt['physical'] = []
            rt['rbe'] = []
            rt['doses'] = []
            rt['rtstruct'] = []
            if os.path.isdir(os.path.join(base_dir, sub_id, rt_session[0], 'RTDOSE')):
                physical = [x for x in os.listdir(os.path.join(
                    base_dir, sub_id, rt_session[0], 'RTDOSE')) if '1-PHY' in x]
                if physical:
                    dcms = [x for y in physical for x in glob.glob(os.path.join(
                            base_dir, sub_id, rt_session[0], 'RTDOSE', y, '*.dcm'))]
                    right_dcm = check_dcm_dose(dcms)
                    if not right_dcm:
                        physical = []
                rbe = [x for x in os.listdir(os.path.join(
                    base_dir, sub_id, rt_session[0], 'RTDOSE')) if '1-RBE' in x]
                if rbe:
                    dcms = [x for y in rbe for x in glob.glob(os.path.join(
                            base_dir, sub_id, rt_session[0], 'RTDOSE', y, '*.dcm'))]
                    right_dcm = check_dcm_dose(dcms)
                    if not right_dcm:
                        rbe = []
                if not physical and not rbe:
                    doses = [x for x in os.listdir(os.path.join(
                        base_dir, sub_id, rt_session[0], 'RTDOSE'))]
                    if doses:
                        dcms = [x for y in doses for x in glob.glob(os.path.join(
                            base_dir, sub_id, rt_session[0], 'RTDOSE', y, '*.dcm'))]
                        right_dcm = check_dcm_dose(dcms)
                        if not right_dcm:
                            doses = []
                else:
                    doses = []
                rt['physical'] = physical
                rt['rbe'] = rbe
                rt['doses'] = doses
            if os.path.isdir(os.path.join(base_dir, sub_id, rt_session[0], 'RTSTRUCT')):
                rtstruct = [x for x in os.listdir(os.path.join(
                    base_dir, sub_id, rt_session[0], 'RTSTRUCT')) if '1-' in x]
                rt['rtstruct'] = rtstruct
            rt['session'] = rt_session[0]
        else:
            rt = None

        self.sessions = sessions
        self.reference = reference
        self.t10 = t10
        self.sequences = sequences
        self.ref_sequence = ref_sequence
        self.rt = rt
        self.ext = ext

        field_template, template_args, outfields = self.define_datasource_inputs()

        self.field_template = field_template
        self.template_args = template_args
        self.outfields= outfields

    def define_datasource_inputs(self):
    
        sequences = self.sequences
        ref_sequence = [self.ref_sequence]
        t10 = self.t10
        reference = self.reference
        rt = self.rt
        ext = self.ext
        process_rt = self.process_rt

        field_template = dict()
        template_args = dict()
        outfields = ref_sequence+sequences
        for seq in ref_sequence+sequences:
            field_template[seq] = '%s/%s/{0}{1}'.format(seq.upper(), ext)
            template_args[seq] = [['sub_id', 'sessions']]
    
        if t10:
            field_template['t1_0'] = '%s/%s/T1{0}'.format(ext)
            template_args['t1_0'] = [['sub_id', 'ref_t1']]
            outfields.append('t1_0')
        if reference:
            field_template['reference'] = '%s/%s/CT{0}'.format(ext)
            template_args['reference'] = [['sub_id', 'ref_ct']]
            outfields.append('reference')
        if rt and process_rt:
            physical = rt['physical']
            rbe = rt['rbe']
            doses = rt['doses']
            rtstruct = rt['rtstruct']
            field_template['rt'] = '%s/%s'
            template_args['rt'] = [['sub_id', 'rt']]
            outfields.append('rt')
            if physical:
                field_template['physical'] = '%s/%s/RTDOSE/1-PHY*'
                template_args['physical'] = [['sub_id', 'rt']]
                outfields.append('physical')
            if rbe:
                field_template['rbe'] = '%s/%s/RTDOSE/1-RBE*'
                template_args['rbe'] = [['sub_id', 'rt']]
                outfields.append('rbe')
            if doses:
                field_template['doses'] = '%s/%s/RTDOSE/*'
                template_args['doses'] = [['sub_id', 'rt']]
                outfields.append('doses')
            if rtstruct:
                field_template['rtstruct'] = '%s/%s/RTSTRUCT/1-*'
                template_args['rtstruct'] = [['sub_id', 'rt']]
                outfields.append('rtstruct')
        elif rt and not process_rt:
            field_template['rt'] = '%s/%s'
            template_args['rt'] = [['sub_id', 'rt']]
            outfields.append('rt')
    
        return field_template, template_args, outfields

    def create_datasource(self):
        
        datasource = nipype.Node(
            interface=nipype.DataGrabber(
                infields=['sub_id', 'sessions', 'ref_ct', 'ref_t1'],
                outfields=self.outfields),
                name='datasource')
        datasource.inputs.base_directory = self.base_dir
        datasource.inputs.template = '*'
        datasource.inputs.sort_filelist = True
        datasource.inputs.raise_on_empty = False
        datasource.inputs.field_template = self.field_template
        datasource.inputs.template_args = self.template_args
        datasource.inputs.sub_id = self.sub_id
        datasource.inputs.sessions = self.sessions
        datasource.inputs.ref_ct = 'REF'
        datasource.inputs.ref_t1 = 'T10'
        if self.rt is not None:
            datasource.inputs.rt = self.rt['session']
        
        return datasource

    def datasink(self, workflow, workflow_datasink):

        datasource = self.data_source
        sequences1 = [x for x in datasource.inputs.field_template.keys()
                      if x!='t1_0' and x!='reference' and x!='rt' and x!='rt_dose'
                      and x!='doses' and x!='rts_dcm' and x!='rtstruct'
                      and x!='physical' and x!='rbe']
        rt = [x for x in datasource.inputs.field_template.keys()
              if x=='rt']
    
        split_ds_nodes = []
        for i in range(len(sequences1)):
            split_ds = nipype.Node(interface=Split(), name='split_ds{}'.format(i))
            split_ds.inputs.splits = [1]*len(self.sessions)
            split_ds_nodes.append(split_ds)
    
    
        for i, node in enumerate(split_ds_nodes):
            if len(self.sessions) > 1:
                workflow.connect(datasource, sequences1[i], node,
                                 'inlist')
                for j, sess in enumerate(self.sessions):
                    workflow.connect(node, 'out{}'.format(j+1),
                                     workflow_datasink, 'results.subid.{0}.@{1}'
                                     .format(sess, sequences1[i]))
            else:
                workflow.connect(datasource, sequences1[i], workflow_datasink,
                                 'results.subid.{0}.@{1}'.format(self.sessions[0],
                                                                 sequences1[i]))
        if self.reference:
            workflow.connect(datasource, 'reference', workflow_datasink,
                             'results.subid.REF.@ref_ct')
        if self.t10:
            workflow.connect(datasource, 't1_0', workflow_datasink,
                             'results.subid.T10.@ref_t1')
        if rt:
            workflow.connect(datasource, 'rt', workflow_datasink,
                             'results.subid.@rt')
        return workflow
    
    def xnat_datasource(self):

        skip_sessions = check_xnat_cache(self.sessions, self.xnat_scans_id,
                                         self.sub_id, self.base_dir)

        if [x for x in self.sessions if x not in skip_sessions]:

            self.pyxnat.get(self.base_dir, subjects=[self.sub_id],
                            needed_scans=self.xnat_scans_id,
                            skip_sessions=skip_sessions)

    def xnat_datasink(self):
    
        sub_folder = os.path.join(self.outdir, self.sub_id)
        sessions = [x for x in sorted(os.listdir(sub_folder))
                    if os.path.isdir(os.path.join(sub_folder, x))]

        if os.path.isfile(os.path.join(sub_folder, 'xnat_datasink_successfullly_completed')):
            print('Results for this subject have been already uploaded to XNAT.')
        else:
            self.pyxnat.put(self.sub_id, sessions, sub_folder)
            with open(os.path.join(sub_folder, 'xnat_datasink_successfullly_completed'),
                      'w') as f:
                f.write('Done!')
            print('Uploading successfully completed!')