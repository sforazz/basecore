from pyxnat import Interface
from pyxnat.core.errors import DatabaseError
import re
import os
import glob
from .base import get_resource_name
from basecore.utils.filemanip import split_filename


session_modality_re = re.compile(r'(MR|CT|RT)(\d+|\w+)')


def put(project, subject, sessions, sub_folder, config=None, url=None, pwd=None, user=None,
        processed=False, overwrite=False):

    if config is not None:
        interface = Interface(config)
    else:
        interface = Interface(server=url, user=user,password=pwd,
                              proxy='www-int2:80')
    
    uri =  '/data/projects/%s/subjects/%s'%(project, subject)
    response = interface.put(uri)
    subject_uid = response.content
    print('New subject %s created!' %subject_uid)

    xnat_subs = interface.select.project(project).subjects()
    xnat_sub = [x for x in xnat_subs if x.label() == subject][0]
    sub_id = interface.select.project(project).subject(xnat_sub.id())

    for session in sessions:
        print('Processing session {}'.format(session))
        session_folder = os.path.join(sub_folder, session)
        scans = [x for x in sorted(glob.glob(session_folder+'/*')) if os.path.isfile(x)]
        match = session_modality_re.match(session)
        proc = ''
        if match is None and processed:
            experiment_type = 'xnat:mrSessionData'
            scan_type = 'xnat:mrScanData'
            proc = '_processed'
        elif match.group(1) == 'MR':
            experiment_type = 'xnat:mrSessionData'
            scan_type = 'xnat:mrScanData'
        elif match.group(1) == 'CT' or match.group(1) == 'CTREF':
            experiment_type = 'xnat:ctSessionData'
            scan_type = 'xnat:ctScanData'
        elif match.group(1) == 'RT':
            experiment_type = 'xnat:rtSessionData'
            scan_type = 'xnat:rtScanData'
        
        experiment = sub_id.experiment('%s_%s%s'%(xnat_sub.label(), session, proc))
        if experiment.exists() and overwrite:
            print('Deleting old experiment folder')
            experiment.delete()
        if not experiment.exists():
            try:
                experiment.create(experiments=experiment_type)
            except DatabaseError:
                experiment.create(experiments=experiment_type)
            print('New experiment %s created!' %experiment.id())

        for scan in scans:

            _, scan_name, extention = split_filename(scan)
            res_format = get_resource_name(scan)
        #     scan_name = scan.split('/')[-1].split('.')[0]
            print('Uploading {}...'.format(scan_name))
            xnat_scan = experiment.scan(scan_name)
            if not xnat_scan.exists():
                done = False
                z = 1
                while not done:
                    try:
                        xnat_scan.create(scans=scan_type)
                        done = True
                    except DatabaseError:
                        print('Same Database error: {} times'.format(z))
                        z = z+1
        #                 xnat_scan.create(scans=scan_type)
                print('New scan %s created!' %xnat_scan.id())
                resource = xnat_scan.resource(res_format)
                if not resource.exists():
                    try:
                        resource.create()
                    except DatabaseError:
                        resource.create()
                    print('New resource %s created!' %resource.id())
                else:
                    print('Resource %s already in the repository!' %resource.id())
                xnat_resource = resource.file(scan_name+extention)
                response = xnat_resource.put(src=scan, format=res_format,
                                             content=res_format, extract=False, overwrite=True)
            else:
                print('Scan %s already in the repository!' %xnat_scan.id())

#     else:
#         print('Experiment %s already in the repository' %experiment.id())


def get(project_id, cache_dir, config=None, url=None, pwd=None, user=None, processed=True,
        subjects=[]):
    "Function to download ALL the subject/sessions/scans from one project."
    "If processed=True, only the processed sessions will be downloaded, "
    "otherwise only the not-processed (i.e. the sessions with raw data)."
    failed = []

    if config is not None:
        interface = Interface(config)
    else:
        interface = Interface(server=url, user=user,password=pwd,
                              proxy='www-int2:80')

    xnat_subjects = interface.select.project(project_id).subjects().get()
    xnat_sub_labels = [interface.select.project(project_id).subject(x).label()
                       for x in xnat_subjects]
    print('Found {0} subjects in project {1}'.format(len(xnat_subjects), project_id))
    # check to see if the requested subjects are on XNAT
    if subjects:
        if not set(subjects).issubset(xnat_sub_labels):
            unprocessed = [x for x in subjects if x not in xnat_sub_labels]
            print('The following subjects are not present in project {0} on XNAT'
                  ' and will be ignored: {1}'
                  .format(project_id, '\n'.join(unprocessed)))
            xnat_subjects = [x for x in subjects if x not in unprocessed]
        else:
            xnat_subjects = subjects
            print('All the requested subjects were found on XNAT.')
    else:
        print('Since no subjects were specified, all subjects will be downloaded')

    for sub_id in xnat_subjects:
        xnat_sub = interface.select.project(project_id).subject(sub_id)
        sub_name = xnat_sub.label()
        if processed:
            sessions = [x for x in xnat_sub.experiments().get()
                        if 'processed' in xnat_sub.experiment(x).label()]
            print('\nFound {0} processed sessions for subject {1}'.format(len(sessions), sub_name))
        else:
            sessions = xnat_sub.experiments().get()
            print('Found {0} sessions for subject {1}'.format(len(sessions), sub_name))

        for session_id in sessions:
            xnat_session = xnat_sub.experiment(session_id)
            if len(xnat_session.label().split('_')) == 3:
                session_name = xnat_session.label().split('_')[1]
            elif len(xnat_session.label().split('_')) == 4:
                session_name = xnat_session.label().split('_')[2]
            else:
                print('WARNING: The session name seems to be different from '
                      'the convention used in the current workflow. It will be '
                      'taken equal to the session label from XNAT.')
                session_name = xnat_session.label().split('_')

            print('\nProcessing session {}\n'.format(session_name))
            folder_path = os.path.join(cache_dir, sub_name, session_name)
            if not os.path.isdir(folder_path):
                os.makedirs(folder_path)
            else:
                print('{} already exists. This might mean that you are trying to '
                      'restart a job, so I will check for already downloaded resources '
                      'in order to speed up the process.'.format(folder_path))
            scans = xnat_session.scans().get()
            for scan_id in scans:
                xnat_scan = xnat_session.scan(scan_id)
                resources = xnat_scan.resources().get()
                for res_id in resources:
                    xnat_resource = xnat_scan.resource(res_id)
                    files = xnat_resource.files().get()
                    for file_id in files:
                        downloaded = False
                        scan_name = xnat_resource.file(file_id).label()
                        if not os.path.isfile(os.path.join(folder_path, scan_name)):
                            print('Downloading resource {} ...'.format(scan_name))
                            while not downloaded:
                                try:
                                    xnat_resource.file(file_id).get_copy(
                                        os.path.join(folder_path, scan_name))
                                    downloaded = True
                                except ConnectionError:
                                    print('Connection lost during download. Try again...')
                                except:
                                    print('Could not download {0} for session {1} '
                                          'in subject {2}. Please try again later'
                                          .format(scan_name, session_name, sub_name))
                                    failed.append([sub_name, session_name, scan_name])
                        else:
                            print('{} already downloaded, skiping it.'.format(scan_name))
    if failed:
        with open(cache_dir+'/failed_download.txt', 'w') as f:
            for line in failed:
                f.write(line+'\n')
