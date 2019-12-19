from pyxnat import Interface
from pyxnat.core.errors import DatabaseError
import re
from .base import get_resource_name
from basecore.utils.filemanip import split_filename


def put(project, subject, session, scan, config=None, url=None, pwd=None, user=None,
        processed=False):

    _, scan_name, extention = split_filename(scan)
    session_modality_re = re.compile(r'(MR|CT|RT)(\d+|\w+)')
#     scan_name = scan.split('/')[-1].split('.')[0]
    print('Uploading {}...'.format(scan_name))
    match = session_modality_re.match(session)
    res_format = get_resource_name(scan)
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
    experiment = sub_id.experiment('%s_%s%s'%(xnat_sub.label(), session, proc))
    if not experiment.exists():
        try:
            experiment.create(experiments=experiment_type)
        except DatabaseError:
            experiment.create(experiments=experiment_type)
        print('New experiment %s created!' %experiment.id())
    else:
        print('Experiment %s already in the repository' %experiment.id())
    xnat_scan = experiment.scan(scan_name+extention)
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
    else:
        print('Scan %s already in the repository!' %xnat_scan.id())
    
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
    
    