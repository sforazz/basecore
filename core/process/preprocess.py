import numpy as np
import nrrd
from core.utils.filemanip import split_filename
import os
import shutil
import glob
import pydicom


ALLOWED_EXT = ['.xlsx', '.csv']
ILLEGAL_CHARACTERS = ['/', '(', ')', '[', ']', '{', '}', ' ', '-']


def mouse_lung_data_preparation(raw_data, temp_dir):
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
    sequence_numbers = list(set([pydicom.read_file(x).SeriesNumber for x in dicoms]))
    for character in ILLEGAL_CHARACTERS:
        basename = basename.replace(character, '_')
    data_folders = []  # I will use this to store the sequence number of the CT data to convert
    for n_seq in sequence_numbers:                     
        dicom_vols = [x for x in dicoms if n_seq==pydicom.read_file(x).SeriesNumber]
        dcm_hd = pydicom.read_file(dicom_vols[0])
        if len(dicom_vols) > 1 and '50s' in dcm_hd.SeriesDescription:
            folder_name = temp_dir+'/{0}_Sequence_{1}'.format(basename, n_seq)
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
            data_folders.append(folder_name)
    if not data_folders:
        print('No suitable CT data with name containing "H50s" were found in {}'.format(raw_data))
        filename = None
    elif len(data_folders) > 1:
        print ('{0} datasets with name containing "H50s" were found in {1}. By default,'
               ' only the first one ({2}) will be used. Please check if this is correct.'
               .format(len(data_folders), raw_data, data_folders[0]))
    else:
        filename = sorted(glob.glob(data_folders[0]+'/*{}'.format(ext)))[0]
        hd = pydicom.read_file(filename)
        dcm_info['vox_x'] = hd.PixelSpacing[0]
        dcm_info['vox_y'] = hd.PixelSpacing[1]
        dcm_info['vox_z'] = hd.SliceThickness

    return filename, folder_name, dcm_info


def cropping(image, mask, prefix=None, size=[86, 86, 86]):

    print('\nStarting raw data and mask cropping...')
    imagePath, imageFilename, imageExt = split_filename(image)
    if prefix is None:
        imageOutname = os.path.join(imagePath, imageFilename+'_cropped')+imageExt
    else:
        imageOutname = os.path.join(imagePath, prefix+'_cropped')+imageExt
    
    _, maskFilename, maskExt = split_filename(mask)
    maskOutname = os.path.join(imagePath, maskFilename+'_cropped')+maskExt
    
    maskData, maskHD = nrrd.read(mask)
    imageData, imageHD = nrrd.read(image)
    
    x, y, z = np.where(maskData==1)
    x_size = np.max(x)-np.min(x)
    y_size = np.max(y)-np.min(y)
    z_size = np.max(z)-np.min(z)
    maskMax = np.max(maskData)
    maskMin = np.min(maskData)
    if maskMax > 1 and maskMin < 0:
        print('This image {} is probably not a mask, as it is not binary. '
              'It will be ignored. Please check if it is true.'.format(mask))
        imageOutname = None
        maskOutname = None
    else:
        if size:
            offset_x = (size[0]-x_size)/2
            offset_y = (size[1]-y_size)/2
            offset_z = (size[2]-z_size)/2
            if offset_x < 0 or offset_y < 0 or offset_z < 0:
                raise Exception('Size too small, please increase.')
    
            if offset_x.is_integer():
                new_x = [np.min(x)-offset_x, np.max(x)+offset_x]
            else:
                new_x = [np.min(x)-(offset_x-0.5), np.max(x)+(offset_x+0.5)]
            if offset_y.is_integer():
                new_y = [np.min(y)-offset_y, np.max(y)+offset_y]
            else:
                new_y = [np.min(y)-(offset_y-0.5), np.max(y)+(offset_y+0.5)]
            if offset_z.is_integer():
                new_z = [np.min(z)-offset_z, np.max(z)+offset_z]
            else:
                new_z = [np.min(z)-(offset_z-0.5), np.max(z)+(offset_z+0.5)]
            new_x = [int(x) for x in new_x]
            new_y = [int(x) for x in new_y]
            new_z = [int(x) for x in new_z]
        else:
            new_x = [np.min(x)-20, np.max(x)+20]
            new_y = [np.min(y)-20, np.max(y)+20]
            new_z = [np.min(z)-20, np.max(z)+20]
        croppedMask = maskData[new_x[0]:new_x[1], new_y[0]:new_y[1],
                               new_z[0]:new_z[1]]
        maskHD['sizes'] = np.array(croppedMask.shape)
        
        croppedImage = imageData[new_x[0]:new_x[1], new_y[0]:new_y[1],
                                 new_z[0]:new_z[1]]
        imageHD['sizes'] = np.array(croppedImage.shape)
        
        nrrd.write(imageOutname, croppedImage, header=imageHD)
        nrrd.write(maskOutname, croppedMask, header=maskHD)
    print('Cropping done!\n')
    return imageOutname, maskOutname
