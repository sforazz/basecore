import os
import argparse
import nipype


sequences = ['t1', 'ct1', 't2', 'flair']


def gbm_datasource(sub_id, BASE_DIR):

    sessions = [x for x in os.listdir(os.path.join(BASE_DIR, sub_id))
                if 'REF' not in x and 'T10' not in x and 'RT_' not in x]
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
    
    return datasource, sessions


def segmentation_datasource(sub_id, BASE_DIR):

    sessions = [x for x in os.listdir(os.path.join(BASE_DIR, sub_id))
                if 'REF' not in x and 'T10' not in x and 'RT_' not in x
                and os.path.isdir(os.path.join(BASE_DIR, sub_id, x))]
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
    
    return datasource, sessions


if __name__ == "__main__":

    PARSER = argparse.ArgumentParser()

    PARSER.add_argument('--input_dir', '-i', type=str,
                        help=('Exisisting directory with the subject(s) to process'))

    ARGS = PARSER.parse_args()

    BASE_DIR = ARGS.input_dir

    
    sub_list = os.listdir(BASE_DIR)

    for sub_id in sub_list:
        datasource, sessions = gbm_datasource(sub_id, BASE_DIR)
        datasource.run()

    print('Done!')
