import os
import nipype
from nipype.interfaces.utility import Split
from basecore.database.pyxnat import put


SEQUENCES = ['t1', 'ct1', 't2', 'flair']


def gbm_datasource(sub_id, BASE_DIR):

    sessions = [x for x in os.listdir(os.path.join(BASE_DIR, sub_id))
                if 'REF' not in x and 'T10' not in x and 'RT_' not in x]
    ref_session = [x for x in os.listdir(os.path.join(BASE_DIR, sub_id))
                   if x == 'REF' and os.path.isdir(os.path.join(BASE_DIR, sub_id, x))]
    if ref_session:
        reference = True
    else:
        print('NO REFERENCE CT!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
        reference = False
    datasource = nipype.Node(
        interface=nipype.DataGrabber(
            infields=['sub_id', 'sessions', 'ref_ct', 'ref_t1'],
            outfields=['t1', 'ct1', 't2', 'flair', 'reference', 't1_0']),
            name='datasource')
    datasource.inputs.base_directory = BASE_DIR
    datasource.inputs.template = '*'
    datasource.inputs.sort_filelist = True
    datasource.inputs.raise_on_empty = False
    datasource.inputs.field_template = dict(t1='%s/%s/T1.nii.gz', ct1='%s/%s/CT1.nii.gz',
                                            t2='%s/%s/T2.nii.gz', flair='%s/%s/FLAIR.nii.gz',
                                            reference='%s/%s/CT.nii.gz',
                                            t1_0='%s/%s/T1.nii.gz')
    datasource.inputs.template_args = dict(t1=[['sub_id', 'sessions']],
                                           ct1=[['sub_id', 'sessions']],
                                           t2=[['sub_id', 'sessions']],
                                           flair=[['sub_id', 'sessions']],
                                           reference=[['sub_id', 'ref_ct']],
                                           t1_0=[['sub_id', 'ref_t1']])
    datasource.inputs.sub_id = sub_id
    datasource.inputs.sessions = sessions
    datasource.inputs.ref_ct = 'REF'
    datasource.inputs.ref_t1 = 'T10'
    
    return datasource, sessions, reference


def cinderella_tp0_datasource(sub_id, BASE_DIR):

    sessions = [x for x in os.listdir(os.path.join(BASE_DIR, sub_id))
                if 'REF' not in x and 'RT_' not in x]
    ref_session = [x for x in os.listdir(os.path.join(BASE_DIR, sub_id))
                   if x == 'REF' and os.path.isdir(os.path.join(BASE_DIR, sub_id, x))]
    if ref_session:
        reference = True
    else:
        print('NO REFERENCE CT!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
        reference = False

    datasource = nipype.Node(
        interface=nipype.DataGrabber(
            infields=['sub_id', 'sessions', 'ref_ct'],
            outfields=['t1', 'ct1', 't2', 'flair', 'reference']),
            name='datasource')
    datasource.inputs.base_directory = BASE_DIR
    datasource.inputs.template = '*'
    datasource.inputs.sort_filelist = True
    datasource.inputs.raise_on_empty = False
    datasource.inputs.field_template = dict(t1='%s/%s/T1.nii.gz', ct1='%s/%s/CT1.nii.gz',
                                            t2='%s/%s/T2.nii.gz', flair='%s/%s/FLAIR.nii.gz',
                                            reference='%s/%s/CT.nii.gz')
    datasource.inputs.template_args = dict(t1=[['sub_id', 'sessions']],
                                           ct1=[['sub_id', 'sessions']],
                                           t2=[['sub_id', 'sessions']],
                                           flair=[['sub_id', 'sessions']],
                                           reference=[['sub_id', 'ref_ct']])
    datasource.inputs.sub_id = sub_id
    datasource.inputs.sessions = sessions
    datasource.inputs.ref_ct = 'REF'
    
    return datasource, sessions, reference


def registration_datasource(sub_id, BASE_DIR):

    sessions = [x for x in os.listdir(os.path.join(BASE_DIR, sub_id))
                if 'REF' not in x and 'T10' not in x and 'RT_' not in x
                and os.path.isdir(os.path.join(BASE_DIR, sub_id, x))]
    ref_session = [x for x in os.listdir(os.path.join(BASE_DIR, sub_id))
                    if x == 'REF' and os.path.isdir(os.path.join(BASE_DIR, sub_id, x))]
    if ref_session:
        reference = True
    else:
        print('NO REFERENCE CT!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
        reference = False

    datasource = nipype.Node(
        interface=nipype.DataGrabber(
            infields=['sub_id', 'sessions', 'ref_ct', 'ref_t1'],
            outfields=['t1', 'ct1', 't2', 'flair', 'reference', 't1_0',
                       't1_0_bet', 't1_bet', 't1_mask', 't1_0_mask']),
            name='datasource')
    datasource.inputs.base_directory = BASE_DIR
    datasource.inputs.template = '*'
    datasource.inputs.sort_filelist = True
    datasource.inputs.raise_on_empty = False
    datasource.inputs.field_template = dict(t1='%s/%s/T1.nii.gz', ct1='%s/%s/CT1.nii.gz',
                                            t2='%s/%s/T2.nii.gz', flair='%s/%s/FLAIR.nii.gz',
                                            reference='%s/%s/CT.nii.gz',
                                            t1_0='%s/%s/T1.nii.gz',
                                            t1_0_bet='%s/%s/T1_0_bet.nii.gz',
                                            t1_0_mask='%s/%s/T1_0_bet_mask.nii.gz',
                                            t1_bet='%s/%s/T1_preproc.nii.gz',
                                            t1_mask='%s/%s/T1_preproc_mask.nii.gz')
    datasource.inputs.template_args = dict(t1=[['sub_id', 'sessions']],
                                           ct1=[['sub_id', 'sessions']],
                                           t2=[['sub_id', 'sessions']],
                                           flair=[['sub_id', 'sessions']],
                                           reference=[['sub_id', 'ref_ct']],
                                           t1_0=[['sub_id', 'ref_t1']],
                                           t1_0_bet=[['sub_id', 'ref_t1']],
                                           t1_0_mask=[['sub_id', 'ref_t1']],
                                           t1_bet=[['sub_id', 'sessions']],
                                           t1_mask=[['sub_id', 'sessions']])
    datasource.inputs.sub_id = sub_id
    datasource.inputs.sessions = sessions
    datasource.inputs.ref_ct = 'REF'
    datasource.inputs.ref_t1 = 'T10'
    
    return datasource, sessions, reference


def single_tp_registration_datasource(sub_id, BASE_DIR):

    sessions = [x for x in os.listdir(os.path.join(BASE_DIR, sub_id))
                if 'REF' not in x and 'RT_' not in x
                and os.path.isdir(os.path.join(BASE_DIR, sub_id, x))]
    ref_session = [x for x in os.listdir(os.path.join(BASE_DIR, sub_id))
                    if x == 'REF' and os.path.isdir(os.path.join(BASE_DIR, sub_id, x))]
    if ref_session:
        reference = True
    else:
        print('NO REFERENCE CT!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
        reference = False

    datasource = nipype.Node(
        interface=nipype.DataGrabber(
            infields=['sub_id', 'sessions', 'ref_ct'],
            outfields=['t1', 'ct1', 't2', 'flair', 'reference',
                       't1_bet', 't1_mask']),
            name='datasource')
    datasource.inputs.base_directory = BASE_DIR
    datasource.inputs.template = '*'
    datasource.inputs.sort_filelist = True
    datasource.inputs.raise_on_empty = False
    datasource.inputs.field_template = dict(t1='%s/%s/T1.nii.gz', ct1='%s/%s/CT1.nii.gz',
                                            t2='%s/%s/T2.nii.gz', flair='%s/%s/FLAIR.nii.gz',
                                            reference='%s/%s/CT.nii.gz',
                                            t1_bet='%s/%s/T1_preproc.nii.gz',
                                            t1_mask='%s/%s/T1_preproc_mask.nii.gz')
    datasource.inputs.template_args = dict(t1=[['sub_id', 'sessions']],
                                           ct1=[['sub_id', 'sessions']],
                                           t2=[['sub_id', 'sessions']],
                                           flair=[['sub_id', 'sessions']],
                                           reference=[['sub_id', 'ref_ct']],
                                           t1_bet=[['sub_id', 'sessions']],
                                           t1_mask=[['sub_id', 'sessions']])
    datasource.inputs.sub_id = sub_id
    datasource.inputs.sessions = sessions
    datasource.inputs.ref_ct = 'REF'
    
    return datasource, sessions, reference


def segmentation_datasource(sub_id, BASE_DIR):

    sessions = [x for x in os.listdir(os.path.join(BASE_DIR, sub_id))
                if 'REF' not in x and 'T10' not in x and 'RT_' not in x
                and os.path.isdir(os.path.join(BASE_DIR, sub_id, x))]
    ref_session = [x for x in os.listdir(os.path.join(BASE_DIR, sub_id))
                    if x == 'REF' and os.path.isdir(os.path.join(BASE_DIR, sub_id, x))]
    if ref_session:
        reference = True
    else:
        print('NO REFERENCE CT!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
        reference = False

    datasource = nipype.Node(
        interface=nipype.DataGrabber(
            infields=['sub_id', 'sessions', 'ref_ct', 'ref_t1'],
            outfields=['t1', 'ct1', 't2', 'flair', 'reference', 't1_0',
                       'reg2t1_warp', 'reg2t1_mat', 'ct1_preproc',
                       'flair_preproc', 't1_preproc', 't2_preproc',
                       't12ct_mat']),
            name='datasource')
    datasource.inputs.base_directory = BASE_DIR
    datasource.inputs.template = '*'
    datasource.inputs.sort_filelist = True
    datasource.inputs.raise_on_empty = False
    datasource.inputs.field_template = dict(t1='%s/%s/T1.nii.gz', ct1='%s/%s/CT1.nii.gz',
                                            t2='%s/%s/T2.nii.gz', flair='%s/%s/FLAIR.nii.gz',
                                            reference='%s/%s/CT.nii.gz',
                                            t1_0='%s/%s/T1.nii.gz',
                                            reg2t1_warp='%s/%s/reg2T1_ref_warp.nii.gz',
                                            reg2t1_mat='%s/%s/reg2T1_ref.mat',
                                            t12ct_mat='%s/%s/regT1_ref2CT.mat',
                                            ct1_preproc='%s/%s/CT1_preproc.nii.gz',
                                            t1_preproc='%s/%s/T1_preproc.nii.gz',
                                            t2_preproc='%s/%s/T2_preproc.nii.gz',
                                            flair_preproc='%s/%s/FLAIR_preproc.nii.gz')
    datasource.inputs.template_args = dict(t1=[['sub_id', 'sessions']],
                                           ct1=[['sub_id', 'sessions']],
                                           t2=[['sub_id', 'sessions']],
                                           flair=[['sub_id', 'sessions']],
                                           reference=[['sub_id', 'ref_ct']],
                                           t1_0=[['sub_id', 'ref_t1']],
                                           reg2t1_warp=[['sub_id', 'sessions']],
                                           reg2t1_mat=[['sub_id', 'sessions']],
                                           t12ct_mat=[['sub_id', 'sessions']],
                                           ct1_preproc=[['sub_id', 'sessions']],
                                           t1_preproc=[['sub_id', 'sessions']],
                                           t2_preproc=[['sub_id', 'sessions']],
                                           flair_preproc=[['sub_id', 'sessions']])
    datasource.inputs.sub_id = sub_id
    datasource.inputs.sessions = sessions
    datasource.inputs.ref_ct = 'REF'
    datasource.inputs.ref_t1 = 'T10'
    
    return datasource, sessions, reference


def single_tp_segmentation_datasource(sub_id, BASE_DIR):

    sessions = [x for x in os.listdir(os.path.join(BASE_DIR, sub_id))
                if 'REF' not in x and 'T10' not in x and 'RT_' not in x
                and os.path.isdir(os.path.join(BASE_DIR, sub_id, x))]
    ref_session = [x for x in os.listdir(os.path.join(BASE_DIR, sub_id))
                    if x == 'REF' and os.path.isdir(os.path.join(BASE_DIR, sub_id, x))]
    if ref_session:
        reference = True
    else:
        print('NO REFERENCE CT!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
        reference = False

    datasource = nipype.Node(
        interface=nipype.DataGrabber(
            infields=['sub_id', 'sessions', 'ref_ct'],
            outfields=['t1', 'ct1', 't2', 'flair', 'reference',
                       'reg2t1_warp', 'reg2t1_mat', 'ct1_preproc',
                       'flair_preproc', 't1_preproc', 't2_preproc',
                       'regT12CT']),
            name='datasource')
    datasource.inputs.base_directory = BASE_DIR
    datasource.inputs.template = '*'
    datasource.inputs.sort_filelist = True
    datasource.inputs.raise_on_empty = False
    datasource.inputs.field_template = dict(t1='%s/%s/T1.nii.gz', ct1='%s/%s/CT1.nii.gz',
                                            t2='%s/%s/T2.nii.gz', flair='%s/%s/FLAIR.nii.gz',
                                            reference='%s/%s/CT.nii.gz',
                                            regT12CT='%s/%s/reg2T1_ref.mat',
                                            ct1_preproc='%s/%s/CT1_preproc.nii.gz',
                                            t1_preproc='%s/%s/T1_preproc.nii.gz',
                                            t2_preproc='%s/%s/T2_preproc.nii.gz',
                                            flair_preproc='%s/%s/FLAIR_preproc.nii.gz')
    datasource.inputs.template_args = dict(t1=[['sub_id', 'sessions']],
                                           ct1=[['sub_id', 'sessions']],
                                           t2=[['sub_id', 'sessions']],
                                           flair=[['sub_id', 'sessions']],
                                           reference=[['sub_id', 'ref_ct']],
                                           regT12CT=[['sub_id', 'sessions']],
                                           ct1_preproc=[['sub_id', 'sessions']],
                                           t1_preproc=[['sub_id', 'sessions']],
                                           t2_preproc=[['sub_id', 'sessions']],
                                           flair_preproc=[['sub_id', 'sessions']])
    datasource.inputs.sub_id = sub_id
    datasource.inputs.sessions = sessions
    datasource.inputs.ref_ct = 'REF'
    
    return datasource, sessions, reference


def datasink_base(datasink, datasource, workflow, sessions, reference,
                  extra_nodes=[], t10=True):

    sequences = SEQUENCES+extra_nodes
    split_ds_nodes = []
    for i in range(len(sequences)):
        split_ds = nipype.Node(interface=Split(), name='split_ds{}'.format(i))
        split_ds.inputs.splits = [1]*len(sessions)
        split_ds_nodes.append(split_ds)


    for i, node in enumerate(split_ds_nodes):
        if len(sessions) > 1:
            workflow.connect(datasource, sequences[i], node,
                             'inlist')
            for j, sess in enumerate(sessions):
                workflow.connect(node, 'out{}'.format(j+1),
                                 datasink, 'results.subid.{0}.@{1}'
                                 .format(sess, sequences[i]))
        else:
            workflow.connect(datasource, sequences[i], datasink,
                             'results.subid.{0}.@{1}'.format(sessions[0],
                                                             sequences[i]))
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
