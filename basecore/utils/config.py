import argparse
import os
from basecore.database.cluster import ClusterDatabase
from basecore.database.pyxnat import PyxnatDatabase


def cmdline_input_config():

    PARSER = argparse.ArgumentParser()
    
    PARSER.add_argument('--input_dir', '-i', type=str,
                        help=('Exisisting directory with the subject(s) to process'))
    PARSER.add_argument('--work_dir', '-w', type=str,
                        help=('Directory where to store the results.'))
    PARSER.add_argument('--xnat-sink', '-xs', action='store_true',
                        help=('Whether or not to upload the processed files to XNAT. '
                              'Default is False'))
    PARSER.add_argument('--xnat-source', action='store_true',
                        help=('Whether or not to source data from XNAT. '
                              'Default is False'))
    PARSER.add_argument('--xnat-project-id', '-xpid', type=str,
                        help=('XNAT project ID. If not provided, and xnat-source and/or '
                              'xnat-sink were selected, you will be prompted to enter it.'))
    PARSER.add_argument('--xnat-overwrite', action='store_true',
                        help=('Whether or not to delete existing subject on XNAT, if xnat-sink'
                              ' is selected. Default is False'))
    PARSER.add_argument('--xnat-processed-session', action='store_false',
                        help=('Whether or not download/upload data from/to a "processed" '
                              'session (i.e. "_processed" is in the name of the sessions).'
                              ' This should be false only if you work with DICOM RAW data, '
                              'otherwise True. Default is True.'))
    PARSER.add_argument('--cluster-sink', '-cs', action='store_true',
                        help=('Whether or not to upload the processed files to a cluster. '
                              'Default is False'))
    PARSER.add_argument('--cluster-source', action='store_true',
                        help=('Whether or not to source data from a cluster. '
                              'Default is False'))
    PARSER.add_argument('--cluster-project-id', '-cpid', type=str,
                        help=('Cluster project ID. If not provided, and cluster-source and/or '
                              'cluster-sink were selected, you will be prompted to enter it.'))
    
    return PARSER


def create_subject_list(base_dir, xnat_source=False, cluster_source=False,
                        subjects_to_process=[]):
    
    if ((os.path.isdir(base_dir) and xnat_source) or
            (os.path.isdir(base_dir) and cluster_source) or
            os.path.isdir(base_dir)):
        sub_list = [x for x in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, x))]
        if subjects_to_process:
            sub_list = [x for x in sub_list if x in subjects_to_process]

    elif xnat_source and not os.path.isdir(base_dir):
        base_dir = os.path.join(base_dir, 'xnat_cache')
        pyxnat = PyxnatDatabase()
        sub_list = pyxnat.get_subject_list()
        if subjects_to_process:
            sub_list = [x for x in sub_list if x in subjects_to_process]

    elif cluster_source and not os.path.isdir(base_dir):
        base_dir = os.path.join(base_dir, 'database_cache')
        cluster = ClusterDatabase()
        sub_list = cluster.get_subject_list(base_dir)
        if subjects_to_process:
            sub_list = [x for x in sub_list if x in subjects_to_process]
        cluster.get(base_dir, subjects=sub_list)

    return sub_list, base_dir
