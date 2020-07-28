import argparse
import getpass
import os
import pydicom
import glob
import re
import pydicom as pd


class Password(argparse.Action):
    def __call__(self, parser, namespace, values, option_string):

        if values is None:
            values = getpass.getpass('Please type in your password: ')

        setattr(namespace, self.dest, values)


def check_already_downloaded(sessions, xnat_scans, sub_id, base_dir):
    
    skip_sessions = []
    for session in sessions:
        avail_scan_names = list(set([x.split('.')[0] for x in 
                            os.listdir(os.path.join(base_dir, sub_id, session))]))
        not_downloaded = [x for x in xnat_scans if x not in avail_scan_names]
        if not not_downloaded:
            skip_sessions.append(session)
    
    return skip_sessions


def check_dcm_dose(dcms):

    right_dcm = []
    for dcm in dcms:
        hd = pydicom.read_file(dcm)
        try:
            hd.GridFrameOffsetVector
            hd.pixel_array
            right_dcm.append(dcm)
        except:
            continue
    return right_dcm


def check_rtstruct(basedir, regex):

    data = []
    no_rt = []
    no_match = []
    for root, _, files in os.walk(basedir):
        for name in files:
            if (('RTDOSE' in name and name.endswith('.nii.gz'))
                    and os.path.isdir(os.path.join(root, 'RTSTRUCT_used'))):
                sub_name = root.split('/')[-2]
                try:
                    rts = glob.glob(os.path.join(root, 'RTSTRUCT_used', '*.dcm'))[0]
                    matching = check_rts(rts, regex)
                    if matching:
                        data.append(sub_name)
                    else:
                        no_match.append(sub_name)
                except IndexError:
                    print('No RTSTRUCT for {}'.format(root.split('/')[-2]))
                    no_rt.append(sub_name)
    return list(set(data))


def check_data(basedir, data_to_find, masks=[]):

    data = []
    for root, _, files in os.walk(basedir):
        for name in files:
            if data_to_find in name and name.endswith('.nii.gz'):
                sub_name = root.split('/')[-2]
                if masks:
                    check = []
                    for mask in masks:
                        if os.path.isfile(os.path.join(root, mask+'.nii.gz')):
                            check.append(1)
                        else:
                            check.append(0)
                    if len(set(check)) == 1 and list(set(check))[0]==1:
                        match = True
                    else:
                        match = False
                else:
                    match = True
                if match:
                    data.append(sub_name)
    return list(set(data))


def check_rts(rts, regex):

    ds = pd.read_file(rts)
    reg_expression = re.compile(regex)
    matching_regex = False
    for i in range(len(ds.StructureSetROISequence)):
        match = reg_expression.match(ds.StructureSetROISequence[i].ROIName)
        if match is not None:
            matching_regex = True
            break
    return matching_regex
