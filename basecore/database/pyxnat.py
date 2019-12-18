from pyxnat import Interface
import re
from .base import get_resource_name


def put(project, subject, session, scan, config=None, url=None, pwd=None, user=None):

    session_modality_re = re.compile(r'(MR|CT|RT)(\d+|\w+)')
    scan_name = scan.split('/')[-1].split('.nii.gz')[0]
    match = session_modality_re.match(session)
    res_format = get_resource_name(scan)
    if match is None or match.group(1) == 'MR':
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
        interface = Interface(server=url, user=user,password=pwd)
    
    uri =  '/data/projects/%s/subjects/%s'%(project, subject)
    response = interface.put(uri)
    subject_uid = response.content
    print('New subject %s created!' %subject_uid)

    xnat_sub = list(interface.select.project(project).subjects())[0]
    sub_id = interface.select.project(project).subject(xnat_sub.id())
    experiment = sub_id.experiment('%s_%s'%(xnat_sub.label(), session))
    if not experiment.exists():
        experiment.create(experiments=experiment_type)
        print('New experiment %s created!' %experiment.id())
    else:
        print('Experiment %s already in the repository' %experiment.id())
    xnat_scan = experiment.scan(scan_name)
    if not xnat_scan.exists():
        xnat_scan.create(scans=scan_type)
        print('New scan %s created!' %xnat_scan.id())
    else:
        print('Scan %s already in the repository!' %xnat_scan.id())
    
    resource = xnat_scan.resource(res_format)
    if not resource.exists():
        resource.create()
        print('New resource %s created!' %resource.id())
    else:
        print('Resource %s already in the repository!' %resource.id())
    xnat_resource = resource.file(scan_name)
    response = xnat_resource.put(src=scan, format=res_format,
                                 content=res_format, extract=False, overwrite=True)
    
    