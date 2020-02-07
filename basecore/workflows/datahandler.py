import os
import nipype
from nipype.interfaces.utility import Split
from basecore.database.pyxnat import put


SEQUENCES = ['ct1', 't2', 'flair']
REF_SEQUENCE = 't1'
POSSIBLE_SEQUENCES = ['t1', 'ct1', 't1km', 't2', 'flair']


def create_datasource(base_dir, sub_id, sessions, field_template,
                      template_args, outfields):
    
    datasource = nipype.Node(
        interface=nipype.DataGrabber(
            infields=['sub_id', 'sessions', 'ref_ct', 'ref_t1'],
            outfields=outfields),
            name='datasource')
    datasource.inputs.base_directory = base_dir
    datasource.inputs.template = '*'
    datasource.inputs.sort_filelist = True
    datasource.inputs.raise_on_empty = False
    datasource.inputs.field_template = field_template
    datasource.inputs.template_args = template_args
    datasource.inputs.sub_id = sub_id
    datasource.inputs.sessions = sessions
    datasource.inputs.ref_ct = 'REF'
    datasource.inputs.ref_t1 = 'T10'
    
    return datasource


def define_datasource_inputs(sequences, ref_sequence, t10, reference):

    field_template = dict()
    template_args = dict()
    if t10:
        field_template['t1_0'] = '%s/%s/T1.nii.gz'
        template_args['t1_0'] = [['sub_id', 'ref_t1']]
    if reference:
        field_template['reference'] = '%s/%s/CT.nii.gz'
        template_args['reference'] = [['sub_id', 'ref_ct']]
    
    for seq in ref_sequence+sequences:
        field_template[seq] = '%s/%s/{}.nii.gz'.format(seq.upper())
        template_args[seq] = [['sub_id', 'sessions']]
    
    outfields = ref_sequence+sequences+['reference']
    if t10:
        outfields.append('t1_0')

    return field_template, template_args, outfields

    
def base_datasource(sub_id, base_dir, sequences=None, ref_sequence=None):
        
    sessions = [x for x in os.listdir(os.path.join(base_dir, sub_id))
                if 'REF' not in x and 'T10' not in x and 'RT_' not in x]
    ref_session = [x for x in os.listdir(os.path.join(base_dir, sub_id))
                   if x == 'REF' and os.path.isdir(os.path.join(base_dir, sub_id, x))]
    t10_session = [x for x in os.listdir(os.path.join(base_dir, sub_id))
                   if x == 'T10' and os.path.isdir(os.path.join(base_dir, sub_id, x))]

    if sequences is None or ref_sequence is None:
        sequences = list(set([y.split('.nii.gz')[0].lower() for x in sessions
                              for y in os.listdir(os.path.join(base_dir, sub_id, x))
                              if y.endswith('.nii.gz')]))
        sequences = [x for x in sequences if x in POSSIBLE_SEQUENCES]
        if 't1' in sequences:
            ref_sequence = 't1'
        elif 'ct1' in sequences:
            ref_sequence = 'ct1'
        elif 't1km' in sequences:
            ref_sequence = 't1km'
        else:
            raise Exception('Nor T1 neither T1KM were found in {}. You need at least one of them '
                            'in order to perform registration.'.format(sub_id))
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

    field_template, template_args, outfields = define_datasource_inputs(
        sequences, [ref_sequence], t10, reference)

    datasource = create_datasource(base_dir, sub_id, sessions,
                                   field_template, template_args, outfields)
    
    return datasource, sessions, reference, t10, sequences, ref_sequence


def registration_datasource(sub_id, base_dir, xnat_source=False):

    base_ds, sessions, reference, t10, sequences, ref_sequence = base_datasource(sub_id, base_dir)
    field_template = dict()
    template_args = dict()

    if t10:
        field_template['t1_0'] = '%s/%s/T10.nii.gz'
        field_template['t1_0_bet'] = '%s/%s/T1_0_bet.nii.gz'
        field_template['t1_0_mask'] = '%s/%s/T1_0_bet_mask.nii.gz'
        template_args['t1_0'] = [['sub_id', 'ref_t1']]
        template_args['t1_0_bet'] = [['sub_id', 'ref_t1']]
        template_args['t1_0_mask'] = [['sub_id', 'ref_t1']]
    field_template['t1_bet'] = '%s/%s/{}_preproc.nii.gz'.format(ref_sequence.upper())
    field_template['t1_mask'] = '%s/%s/{}_preproc_mask.nii.gz'.format(ref_sequence.upper())
    template_args['t1_bet'] = [['sub_id', 'sessions']]
    template_args['t1_mask'] = [['sub_id', 'sessions']]

    field_template.update(base_ds.inputs.field_template)
    template_args.update(base_ds.inputs.template_args)
    outfields = [x for x in field_template.keys()]

    if xnat_source:
        xnat_scan_ids = list(set([field_template[it].split('/')[-1].split('.')[0]
                                  for it in field_template]))
    else:
        xnat_scan_ids = []
    datasource = create_datasource(base_dir, sub_id, sessions,field_template,
                                   template_args, outfields)
    
    return datasource, sessions, reference, t10, sequences, ref_sequence, xnat_scan_ids


def segmentation_datasource(sub_id, base_dir, apply_transform=False, xnat_source=False):

    base_ds, sessions, reference, t10, sequences, ref_sequence = base_datasource(sub_id, base_dir)
    field_template = dict()
    template_args = dict()

    if reference and apply_transform:
        field_template['t12ct_mat'] = '%s/%s/regT1_ref2CT.mat'
        template_args['t12ct_mat'] = [['sub_id', 'sessions']]
    if t10 and apply_transform:
        field_template['reg2t1_warp'] = '%s/%s/reg2T1_ref_warp.nii.gz'
        field_template['reg2t1_mat'] = '%s/%s/reg2T1_ref.mat'
        template_args['reg2t1_warp'] = [['sub_id', 'sessions']]
        template_args['reg2t1_mat'] = [['sub_id', 'sessions']]
    for seq in sequences+[ref_sequence]:
        field_template['{}_preproc'.format(seq)] = '%s/%s/{}_preproc.nii.gz'.format(seq.upper())
        template_args['{}_preproc'.format(seq)] = [['sub_id', 'sessions']]
    
    field_template.update(base_ds.inputs.field_template)
    template_args.update(base_ds.inputs.template_args)
    outfields = [x for x in field_template.keys()]
    if xnat_source:
        xnat_scan_ids = list(set([field_template[it].split('/')[-1].split('.')[0]
                                  for it in field_template]))
    else:
        xnat_scan_ids = []
    datasource = create_datasource(base_dir, sub_id, sessions,field_template,
                                   template_args, outfields)
    
    return datasource, sessions, reference, t10, sequences, ref_sequence, xnat_scan_ids


def datasink_base(datasink, datasource, workflow, sessions, reference,
                  extra_nodes=[], t10=True, sequences=[], ref_sequence=[]):

#     sequences1 = ref_sequence+sequences+extra_nodes
    sequences1 = [x for x in datasource.inputs.field_template.keys()
                  if x!='t1_0' and x!='reference']
    split_ds_nodes = []
    for i in range(len(sequences1)):
        split_ds = nipype.Node(interface=Split(), name='split_ds{}'.format(i))
        split_ds.inputs.splits = [1]*len(sessions)
        split_ds_nodes.append(split_ds)


    for i, node in enumerate(split_ds_nodes):
        if len(sessions) > 1:
            workflow.connect(datasource, sequences1[i], node,
                             'inlist')
            for j, sess in enumerate(sessions):
                workflow.connect(node, 'out{}'.format(j+1),
                                 datasink, 'results.subid.{0}.@{1}'
                                 .format(sess, sequences1[i]))
        else:
            workflow.connect(datasource, sequences1[i], datasink,
                             'results.subid.{0}.@{1}'.format(sessions[0],
                                                             sequences1[i]))
    if reference:
        workflow.connect(datasource, 'reference', datasink,
                         'results.subid.REF.@ref_ct')
    if t10:
        workflow.connect(datasource, 't1_0', datasink,
                         'results.subid.T10.@ref_t1')
    return workflow


def xnat_datasink(project_id, sub_id, result_dir, user, pwd,
                  url='https://central.xnat.org', processed=True,
                  overwrite=False):
    
    sub_folder = os.path.join(result_dir, sub_id)
    sessions = [x for x in sorted(os.listdir(sub_folder))
                if os.path.isdir(os.path.join(sub_folder, x))]
    put(project_id, sub_id, sessions, sub_folder, url=url,
        pwd=pwd, user=user, processed=processed, overwrite=overwrite)
