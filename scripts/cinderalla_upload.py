from basecore.database.xnat import put
import glob
import os


base_project_name = 'MRRT001'
base_dir = '/mnt/sdb/sorted_data/Data_cinderella_MR_CLass/'
subjects = [os.path.join(base_dir, x) for x in sorted(os.listdir(base_dir))
            if os.path.isdir(os.path.join(base_dir, x))][127:]
mr_contrasts = ['T1', 'T2', 'T1KM', 'ADC', 'SWI', 'FLAIR', 'T2KM']
rt_files = ['RTSTRUCT', 'RTDOSE', 'RTPLAN']

for sub in subjects:
    sub_name = sub.split('/')[-1]
    print('Processing subject {}'.format(sub_name))
    sessions = [os.path.join(sub, x) for x in sorted(os.listdir(sub))
                if os.path.isdir(os.path.join(sub, x))]
    for session in sessions:
        session_name = session.split('/')[-1]
        mr_scans = [os.path.join(session, x) for x in sorted(os.listdir(session))
                    if os.path.isdir(os.path.join(session, x))
                    and 'Unclassifiable' not in x
                    and x in mr_contrasts]
        ct_scans = [os.path.join(session, x) for x in sorted(os.listdir(session))
                    if os.path.isdir(os.path.join(session, x))
                    and 'Unclassifiable' not in x
                    and x == 'CT']
        rt_scans = [os.path.join(session, x) for x in sorted(os.listdir(session))
                    if os.path.isdir(os.path.join(session, x))
                    and 'Unclassifiable' not in x
                    and x in rt_files]
        if mr_scans:
            for scan in mr_scans:
                session_type = 'MR'
                dcms = sorted(glob.glob(scan+'/1-*/*dcm'))
                if dcms:
                    scan_name = scan.split('/')[-1]
                    print('Trying to upload {} scan'.format(scan_name))
                    xnat_session_name = '_'.join([base_project_name, sub_name, session_type+session_name])
                    put(xnat_session_name, scan_name, dcms, resource_name='dicom', create_session=True,
                        overwrite=True)
        if ct_scans:
            for scan in ct_scans:
                session_type = 'CT'
                dcms = sorted(glob.glob(scan+'/1-*/*dcm'))
                if dcms:
                    scan_name = scan.split('/')[-1]
                    print('Trying to upload {} scan'.format(scan_name))
                    xnat_session_name = '_'.join([base_project_name, sub_name, session_type+session_name])
                    put(xnat_session_name, scan_name, dcms, resource_name = 'dicom', create_session=True,
                        overwrite=True)
        if rt_scans:
            for scan in rt_scans:
                session_type = 'RT'
                dcms = sorted(glob.glob(scan+'/1-*/*dcm'))
                if dcms:
                    scan_name = scan.split('/')[-1]
                    print('Trying to upload {} scan'.format(scan_name))
                    xnat_session_name = '_'.join([base_project_name, sub_name, session_type+session_name])
                    put(xnat_session_name, scan_name, dcms, resource_name = 'dicom', create_session=True,
                        overwrite=True)

print('Done!')
