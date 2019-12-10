from basecore.database.xnat import put
import glob
import os
import shutil
import subprocess as sp


base_project_name = 'MRRT003'
base_dir = '/mnt/sdb/GBM_4sequences_sorted/'
subjects = [os.path.join(base_dir, x) for x in sorted(os.listdir(base_dir))
            if os.path.isdir(os.path.join(base_dir, x))][127:]
mr_contrasts = ['T1', 'T2', 'CT1', 'FLAIR']
rt_files = ['RTSTRUCT', 'RTDOSE', 'RTPLAN', 'RTCT']
failed = []

for sub in subjects:
    sub_name = sub.split('/')[-1]
    print('Processing subject {}'.format(sub_name))
    sessions = [os.path.join(sub, x) for x in sorted(os.listdir(sub))
                if os.path.isdir(os.path.join(sub, x))]
    for session in sessions:
        session_name = session.split('/')[-1]
        if session_name == 'REF_FK':
            print()
        mr_scans = [os.path.join(session, x) for x in sorted(os.listdir(session))
                    if os.path.isfile(os.path.join(session, x))
                    and '.json' not in x
                    and x.split('.')[0] in mr_contrasts]
        ct_scans = [os.path.join(session, x) for x in sorted(os.listdir(session))
                    if os.path.isfile(os.path.join(session, x))
                    and '.json' not in x and session_name != 'REF_FK'
                    and x == 'CT.nii.gz']
        rt_scans = [os.path.join(session, x) for x in sorted(os.listdir(session))
                    if os.path.isdir(os.path.join(session, x))
                    and 'Unclassifiable' not in x
                    and x in rt_files]
        try:
            if mr_scans:
                for scan in mr_scans:
                    session_type = 'MR'
                    scan_name = scan.split('/')[-1].split('.')[0]
                    print('Trying to upload {} scan'.format(scan_name))
                    xnat_session_name = '_'.join([base_project_name, sub_name, session_type+session_name])
                    cmd = 'xnat-put {0} {1} --create_session -o {2}'.format(xnat_session_name, scan_name, scan)
                    sp.check_output(cmd, shell=True)
#                     put(xnat_session_name, scan_name, scan, create_session=True,
#                         overwrite=True)
            if ct_scans:
                for scan in ct_scans:
                    session_type = 'CT'
                    scan_name = scan.split('/')[-1].split('.')[0]
                    print('Trying to upload {} scan'.format(scan_name))
                    xnat_session_name = '_'.join([base_project_name, sub_name, session_type+session_name])
                    cmd = 'xnat-put {0} {1} --create_session -o {2}'.format(xnat_session_name, scan_name, scan)
                    sp.check_output(cmd, shell=True)
#                     put(xnat_session_name, scan_name, scan, create_session=True,
#                         overwrite=True)
            if rt_scans:
                for scan in rt_scans:
                    session_type = 'RT'
                    scan_name = scan.split('/')[-1].split('.')[0]
                    shutil.make_archive(scan, 'zip', scan)
                    print('Trying to upload {} scan'.format(scan_name))
                    xnat_session_name = '_'.join([base_project_name, sub_name, session_type+session_name])
                    cmd = 'xnat-put {0} {1} --create_session -o {2}'.format(xnat_session_name, scan_name, scan+'.zip')
                    sp.check_output(cmd, shell=True)
#                     put(xnat_session_name, scan_name, scan+'.zip', create_session=True,
#                         overwrite=True)
                    os.remove(scan+'.zip')
        except:
            print('Session {} failed to be uploaded to XNAT'.format(session))
            failed.append([sub, session])

with open('/mnt/sdb/GBM_4sequences_sorted/failed.txt', 'w') as f:
    for el in failed:
        f.write('{}\n'.format(el))

print('Done!')
