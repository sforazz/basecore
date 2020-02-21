import os
from pyxnat import Interface


resource_exts = {
    'NIFTI': '.nii',
    'NIFTI_GZ': '.nii.gz',
    'PDF': '.pdf',
    'MRTRIX': '.mif',
    'DICOM': '',
    'secondary': '',
    'TEXT_MATRIX': '.mat',
    'MRTRIX_GRAD': '.b',
    'FSL_BVECS': '.bvec',
    'FSL_BVALS': '.bval',
    'MATLAB': '.mat',
    'ANALYZE': '.img',
    'ZIP': '.zip',
    'RDATA': '.rdata',
    'DAT': '.dat',
    'RAW': '.rda',
    'JPG': '.JPG',
    'TEXT': '.txt',
    'TAR_GZ': '.tar.gz',
    'CSV': '.csv',
    'BINARY_FILE': '.bf'}


def check_cache(sessions, xnat_scans, sub_id, base_dir):
    
    skip_sessions = []
    for session in sessions:
        avail_scan_names = list(set([x.split('.')[0] for x in 
                            os.listdir(os.path.join(base_dir, sub_id, session))]))
        not_downloaded = [x for x in xnat_scans if x not in avail_scan_names]
        if not not_downloaded:
            skip_sessions.append(session)
    
    return skip_sessions


def extract_extension(filename):
    name_parts = os.path.basename(filename).split('.')
    if len(name_parts) == 1:
        ext = ''
    else:
        if name_parts[-1] == 'gz':
            num_parts = 2
        else:
            num_parts = 1
        ext = '.' + '.'.join(name_parts[-num_parts:])
    return ext.lower()


def get_resource_name(filename):
    ext = extract_extension(filename)
    try:
        return next(k for k, v in resource_exts.items()
                    if v == ext)
    except StopIteration:
        if ext.startswith('.'):
            ext = ext[1:]
        return ext.upper()
