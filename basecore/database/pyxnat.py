from pyxnat import Interface
from pyxnat.core.errors import DatabaseError
import re
import os
import glob
import getpass
from .base import get_resource_name
from basecore.utils.filemanip import split_filename
import json


session_modality_re = re.compile(r'(MR|CT|RT)(\d+|\w+)')

class Pyxnat():
    
    def __init__(self, xnat_config, xnat_url = 'https://central.xnat.org',
                 project_id=None, processed_session=True, overwrite=False):

        self.processed_session = processed_session
        self.overwrite = overwrite

        if project_id is None:
            project_id = input("Please enter the XNAT project ID "
                               " you want to use: ")
        self.project_id = project_id

        if xnat_config:
            config_file = xnat_config
        elif os.path.isfile(os.path.join(
                os.path.expanduser('~'), '.pyxnat_config.cfg')):
            print('Found saved Pyxnat configuration file. It will be used to connect to XNAT.')
            config_file = '~/.pyxnat_config.cfg'
            with open(config_file, 'r') as f:
                config = json.load(f)
            xnat_url = config['server']
            xnat_user = config['user']
        else:
            print('No Pyxnat configuration file provided. You will be prompt to insert '
                  'your XNAT credentials.')
            config_file = None
            xnat_url_prompt = input(
                "The default url if https://central.xnat.org, if you wish "
                "to change it please enter the new url now, otherwise press enter: ")
            if xnat_url_prompt:
                xnat_url = xnat_url_prompt
            xnat_user = input("Please enter your XNAT username: ")
            xnat_pwd = getpass.getpass("Please enter your XNAT password: ")
            save_config = input(
                "If you want to save the current configuration into '~/.pyxnat_config.cfg' "
                "to use it in the next login, please type 'yes': ")
            if save_config == 'yes':
                save_config = True
            else:
                save_config = False

        print('Connecting to XNAT with the following parameters:')
        print('Server: {}'.format(xnat_url))
        print('Project ID: {}'.format(project_id))
        print('User ID: {}'.format(xnat_user))

        if config_file is not None:
            interface = Interface(config=config_file)
        else:
            interface = Interface(
                server=xnat_url, user=xnat_user,
                password=xnat_pwd, proxy='www-int2:80')
            if save_config:
                interface.save_config(os.path.join(
                os.path.expanduser('~'), '.pyxnat_config.cfg'))

        self.interface = interface

    def put(self, subject, sessions, sub_folder):
        
        uri =  '/data/projects/%s/subjects/%s'%(self.project_id, subject)
        response = self.interface.put(uri)
        subject_uid = response.content
        print('New subject %s created!' %subject_uid)
    
        xnat_subs = self.interface.select.project(self.project_id).subjects()
        xnat_sub = [x for x in xnat_subs if x.label() == subject][0]
        sub_id = self.interface.select.project(self.project_id).subject(xnat_sub.id())
    
        for session in sessions:
            print('Processing session {}'.format(session))
            session_folder = os.path.join(sub_folder, session)
            scans = [x for x in sorted(glob.glob(session_folder+'/*')) if os.path.isfile(x)]
            match = session_modality_re.match(session)
            proc = ''
            if match is None and self.processed_session:
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
            if experiment.exists() and self.overwrite:
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
    
    def get(self, cache_dir, subjects=[], needed_scans=[], skip_sessions=[]):
        "Function to download ALL the subject/sessions/scans from one project."
        "If processed=True, only the processed sessions will be downloaded, "
        "otherwise only the not-processed (i.e. the sessions with raw data)."
        failed = []
    
        xnat_subjects = self.interface.select.project(self.project_id).subjects().get()
        xnat_sub_labels = [self.interface.select.project(self.project_id).subject(x).label()
                           for x in xnat_subjects]
        print('Found {0} subjects in project {1}'.format(len(xnat_subjects), self.project_id))
        # check to see if the requested subjects are on XNAT
        if subjects:
            if not set(subjects).issubset(xnat_sub_labels):
                unprocessed = [x for x in subjects if x not in xnat_sub_labels]
                print('The following subjects are not present in project {0} on XNAT'
                      ' and will be ignored: {1}'
                      .format(self.project_id, '\n'.join(unprocessed)))
                xnat_subjects = [x for x in subjects if x not in unprocessed]
            else:
                xnat_subjects = subjects
                print('All the requested subjects were found on XNAT.')
        else:
            print('Since no subjects were specified, all subjects will be downloaded')
    
        for sub_id in xnat_subjects:
            xnat_sub = self.interface.select.project(self.project_id).subject(sub_id)
            sub_name = xnat_sub.label()
            if self.processed_session:
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
                if session_name not in skip_sessions:
                    print('\nProcessing session {}\n'.format(session_name))
                    folder_path = os.path.join(cache_dir, sub_name, session_name)
                    if not os.path.isdir(folder_path):
                        os.makedirs(folder_path)
                    else:
                        print('{} already exists. This might mean that you are trying to '
                              'restart a job, so I will check for already downloaded resources '
                              'in order to speed up the process.'.format(folder_path))
                    scans = xnat_session.scans().get()
                    if needed_scans:
                        scans = [x for x in scans if x in needed_scans]
        
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
