"Function to upload to XNAT"
from timeloop import Timeloop
from datetime import timedelta
import os
from basecore.workflows.datahandler import xnat_datasink
import shutil


XNAT_URL = 'https://central.xnat.org'
XNAT_PID = 'MRRT004'
XNAT_USER = 'fsforazz'
BASE_DIR = '/mnt/sdb/result2upload'

tl = Timeloop()

@tl.job(interval=timedelta(seconds=60))
def sample_job_every_2s():
    folders = os.listdir(BASE_DIR)
    if 'ready' in folders:
        print('Uploading the results to XNAT with the following parameters:')
        print('Server: {}'.format(XNAT_URL))
        print('Project ID: {}'.format(XNAT_PID))
        print('User ID: {}'.format(XNAT_USER))

        sub_id = [x for x in folders if x!='ready'][0]
        xnat_datasink(XNAT_PID, sub_id, BASE_DIR,
                      XNAT_USER, 'sono1genio!', url=XNAT_URL, processed=True)
        for folder in folders:
            shutil.rmtree(os.path.join(BASE_DIR, folder))
    else:
        print('No results to be uploaded yet. Checking again in 10 minutes')

    
if __name__ == "__main__":
    tl.start(block=True)