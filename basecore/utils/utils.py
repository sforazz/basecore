import argparse
import getpass
import os


class Password(argparse.Action):
    def __call__(self, parser, namespace, values, option_string):

        if values is None:
            values = getpass.getpass('Please type in your password: ')

        setattr(namespace, self.dest, values)


def check_already_downloaded(sessions, xnat_scans, sub_id, base_dir):
    
    skip_sessions = []
    for session in sessions:
        avail_scan_names = [x.split('.') for x in 
                            os.listdir(os.path.join(base_dir, sub_id, session))]
        not_downloaded = [x for x in xnat_scans if x not in avail_scan_names]
        if not not_downloaded:
            skip_sessions.append(session)
    
    return skip_sessions