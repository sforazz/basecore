import os
import json
import subprocess as sp
import collections


class ClusterDatabase():
    
    def __init__(self, config_file=None, cluster_host_name='e132-comp01',
                 project_id=None, cluster_basedir='/datasets/datasets_E210'):

        self.cluster_basedir = cluster_basedir

        if project_id is None:
            project_id = input("Please enter the project ID on the Cluster"
                               " you want to use: ")
        self.project_id = project_id

        if config_file is not None:
            config_file = config_file
        elif os.path.isfile(os.path.join(
                os.path.expanduser('~'), '.cluster_config.cfg')):
            print('Found saved Cluster configuration file. It will be '
                  'used to connect to the Cluster.')
            config_file = os.path.join(
                os.path.expanduser('~'), '.cluster_config.cfg')
            with open(config_file, 'r') as f:
                config = json.load(f)
            cluster_host_name = config['cluster_host_name']
            cluster_user = config['user']
        else:
            print('No cluster configuration file provided. You will be prompt to insert '
                  'your cluster configurations')
            config_file = None
            cluster_host_prompt = input(
                "The default host name is e132-comp01, if you wish "
                "to change it please enter the new host name now, otherwise press enter: ")
            if cluster_host_prompt:
                cluster_host_name = cluster_host_prompt
            cluster_user = input("Please enter your cluster username: ")
            save_config = input(
                "If you want to save the current configuration into '~/.cluster_config.cfg' "
                "to use it in the next login, please type 'yes': ")
            if save_config == 'yes':
                config = {}
                config['cluster_host_name'] = cluster_host_name
                config['user'] = cluster_user
                save_file = os.path.join(os.path.expanduser('~'),
                                         '.cluster_config.cfg')
                with open(save_file, 'w') as f:
                    json.dump(config, f)
        
        print('Connecting to the cluster with the following parameters:')
        print('Cluster host name: {}'.format(cluster_host_name))
        print('Project ID: {}'.format(project_id))
        print('User name: {}'.format(cluster_user))

        self.myserver = '{0}@{1}:{2}/{3}'.format(cluster_user, cluster_host_name,
                                                cluster_basedir, project_id)
        
    def check_precomputed_outputs(self, basepath, outfields, sessions, sub_id):
        
        cmd = 'rsync -rtvu {0}/database.json {1}'.format(self.myserver, basepath)
        self.run_rsync(cmd, ignore_error=True)
        
        database = self.load_database(os.path.join(basepath, 'database.json'))
        to_process = []
        if database is not None:
            sub_db = database[sub_id]
            for session in sessions:
                session_db = sub_db[session]
                not_processed_scans = [x for x in outfields if x not in session_db]
                if not_processed_scans:
                    to_process.append(session)
        
        return to_process

    def put(self, sessions, sub_folder):
        
        basepath, folder_name = os.path.split(sub_folder)

        cmd = 'rsync -rtvu {0}/database.json {1}'.format(self.myserver, basepath)
        self.run_rsync(cmd, ignore_error=True)

        database = dict()
        database[folder_name] = collections.defaultdict(dict)
        scans = [os.path.join(folder_name, x, y) for x in sessions
                 for y in os.listdir(os.path.join(sub_folder, x))]

        for element in scans:
            _, sess, scan = element.split('/')
            scan_name = scan.split('.')[0].lower()
            database[folder_name][sess][scan_name] = element

        scan_file = os.path.join(sub_folder, 'files_to_save_cluster.txt')
        with open(scan_file, 'w') as f:
            for el in scans:
                f.write(el+'\n')
            f.write('database.json')

        self.update_database(basepath, database, folder_name)

        cmd = 'rsync -rtvu --files-from={0} {1} {2}'.format(
            scan_file, basepath, self.myserver)
        self.run_rsync(cmd)
    
    def get(self, cache_dir, subjects=[], needed_scans=[], skip_sessions=[]):

        if not os.path.isdir(cache_dir):
            os.mkdir(cache_dir)
        cmd = 'rsync -rtvu {0}/database.json {1}'.format(self.myserver, cache_dir)
        self.run_rsync(cmd)

        database = self.load_database(os.path.join(cache_dir, 'database.json'))
        to_get = []
        for sub_id in subjects:
            if sub_id in database.keys():
                print('Subject {} found in the database'.format(sub_id))
                sessions = list(database[sub_id])
                print('Found {} session(s)'.format(len(sessions)))
                if skip_sessions:
                    sessions = [x for x in sessions if x not in skip_sessions]
                for session in sessions:
                    scans = list(database[sub_id][session])
                    if needed_scans:
                        scans = [x for x in scans if x in needed_scans]
                    for scan in scans:
                        to_get.append(database[sub_id][session][scan])

        scan_file = os.path.join(cache_dir, 'files_to_get_from_cluster.txt')
        with open(scan_file, 'w') as f:
            for el in to_get:
                f.write(el+'\n')
        cmd = 'rsync -rtvu --files-from={0} {1} {2}'.format(
            scan_file, self.myserver, cache_dir)
        self.run_rsync(cmd)
      
    def load_database(self, db_path):

        if os.path.isfile(db_path):
            with open(db_path, 'r') as f:
                database = json.load(f)
        else:
            database = None
        
        return database

    def update_database(self, basepath, new_db, folder_name):

        database = self.load_database(os.path.join(basepath, 'database.json'))

        if database is not None:
            if folder_name not in database.keys():
                database[folder_name] = collections.defaultdict(dict)
            database[folder_name].update(new_db[folder_name])
        else:
            database = new_db
        
        with open(os.path.join(basepath, 'database.json'), 'w') as f:
            json.dump(database, f)

    def run_rsync(self, cmd, ignore_error=False):

        try:
            sp.check_output(cmd, shell=True)
        except sp.CalledProcessError:
            if not ignore_error:
                raise Exception('rsync failed to perform the requested action. '
                                'Please try again later.')

    def get_subject_list(self, basepath):

        cmd = 'rsync -rtvu {0}/database.json {1}'.format(self.myserver, basepath)
        self.run_rsync(cmd, ignore_error=True)
        
        database = self.load_database(os.path.join(basepath, 'database.json'))
        if database is not None:
            sub_list = list(database.keys())
        else:
            sub_list = []

        return sub_list
