import argparse
from basecore.database.pyxnat import put


if __name__ == "__main__":

    PARSER = argparse.ArgumentParser()
    PARSER.add_argument('--input-folder', '-i', type=str,
                        help=('Folder to upload to XNAT.'))
    PARSER.add_argument('--sub-id', type=str,
                        help=('Subject ID on XNAT.'))
    PARSER.add_argument('--session-id', type=str,
                        help=('Session ID on XNAT.'))
    PARSER.add_argument('--xnat-url', '-xurl', type=str, default='https://central.xnat.org',
                        help=('The url of the server must be provided here. '
                              'Default is https://central.xnat.org'))
    PARSER.add_argument('--xnat-pid', '-xpid', type=str,
                        help=('The project ID o the server where to upload '
                              'the results must be provided here.'))
    PARSER.add_argument('--xnat-user', '-xuser', type=str,
                        help=('The username on the server must be provided here.'))
    PARSER.add_argument('--xnat-pwd', '-xpwd', type=str,
                        help=('The password on the server must be provided here.'))

    ARGS = PARSER.parse_args()
    print('Uploading the results to XNAT with the following parameters:')
    print('Server: {}'.format(ARGS.xnat_url))
    print('Project ID: {}'.format(ARGS.xnat_pid))
    print('User ID: {}'.format(ARGS.xnat_user))
    
    put(ARGS.xnat_pid, ARGS.sub_id, ARGS.session, ARGS.input_folder, url=ARGS.xnat_url,
        pwd=ARGS.xnat_pwd, user=ARGS.xnat_user, processed=ARGS.processed)
