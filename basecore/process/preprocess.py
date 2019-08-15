import os
import shutil
import glob
import pydicom
from basecore.utils.dicom import DicomInfo
from pathlib import Path
import pickle


ALLOWED_EXT = ['.xlsx', '.csv']
ILLEGAL_CHARACTERS = ['/', '(', ')', '[', ']', '{', '}', ' ', '-']

    
def dicom_check(raw_data, temp_dir):
    """Function to arrange the mouse lung data into a proper struture.
    In particular, this function will look into each raw_data folder searching for
    the data with H50s in the series description field in the DICOM header. Then,
    it will copy those data into another folder and will return the path to the first
    DICOM file that will be used to run the DICOM to NRRD conversion.
    Parameters
    ----------
    raw_data : str
        path to the raw data folder 
    Returns
    -------
    pth : str
        path to the first DICOM volume
    """
    
    dicoms = sorted(glob.glob(raw_data+'/*.IMA'))
    dcm_info = {}
    processed = False
    if not dicoms:
        dicoms = sorted(glob.glob(raw_data+'/*.dcm'))
        if not dicoms:
            raise Exception('No DICOM files found in {}! Please check.'.format(raw_data))
        else:
            ext = '.dcm'
    else:
        ext = '.IMA'
    
    if not os.path.isdir(temp_dir):
        os.mkdir(temp_dir)
    basename = raw_data.split('/')[-1]
    sequence_numbers = list(set([str(pydicom.read_file(x).SeriesNumber) for x in dicoms]))
    for character in ILLEGAL_CHARACTERS:
        basename = basename.replace(character, '_')
    for n_seq in sequence_numbers:                     
        dicom_vols = [x for x in dicoms if n_seq==str(pydicom.read_file(x).SeriesNumber)]
        dcm_hd = pydicom.read_file(dicom_vols[0])
        if len(dicom_vols) > 1 and '50s' in dcm_hd.SeriesDescription and not processed:
            dcm = DicomInfo(dicom_vols)
            _, tag = dcm.get_tag(['AcquisitionDate', 'SeriesTime'])
            folder_name = temp_dir+'/{0}_date_{1}_time_{2}'.format(basename, tag['AcquisitionDate'][0],
                                                                   tag['SeriesTime'][0])
            slices = [pydicom.read_file(x).InstanceNumber for x in dicom_vols]
            if len(slices) != len(set(slices)):
                print('Duplicate slices found in {} for H50s sequence. Please check. '
                      'This subject will be excluded from the analysis.'.format(raw_data))
                continue
            if not os.path.isdir(folder_name):
                os.mkdir(folder_name)
            else:
                shutil.rmtree(folder_name)
                os.mkdir(folder_name)
            for x in dicom_vols:
                try:
                    shutil.copy2(x, folder_name)
                except:
                    continue
            filename = sorted(glob.glob(folder_name+'/*{}'.format(ext)))[0]
            with open(folder_name+'/dcm_info.p', 'wb') as fp:
                pickle.dump(tag, fp, protocol=pickle.HIGHEST_PROTOCOL)
            processed = True
    if not processed:
        print('No suitable CT data with name containing "H50s" were found in {}'.format(raw_data))
        filename = None

    return filename, folder_name, dcm_info
