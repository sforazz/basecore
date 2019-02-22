import os
import pandas as pd


ALLOWED_EXT = ['.xlsx', '.csv']
ILLEGAL_CHARACTERS = ['/', '(', ')', '[', ']', '{', '}', ' ', '-']


def split_filename(fname):
    """Split a filename into parts: path, base filename and extension.
    Parameters
    ----------
    fname : str
        file or path name
    Returns
    -------
    pth : str
        base path from fname
    fname : str
        filename from fname, without extension
    ext : str
        file extension from fname
    """

    special_extensions = [".nii.gz", ".tar.gz", ".niml.dset"]

    pth = os.path.dirname(fname)
    fname = os.path.basename(fname)

    ext = None
    for special_ext in special_extensions:
        ext_len = len(special_ext)
        if (len(fname) > ext_len) and \
                (fname[-ext_len:].lower() == special_ext.lower()):
            ext = fname[-ext_len:]
            fname = fname[:-ext_len]
            break
    if not ext:
        fname, ext = os.path.splitext(fname)

    return pth, fname, ext


def batch_processing(input_data, key_col1='subjects', key_col2='masks', root=''):
    """Function to process the data in batch mode. It will take a .csv or .xlsx file with
    two columns. The first one called 'subjects' contains all the paths to the raw_data folders
    (one path per raw); the second one called 'masks' contains all the corresponding paths to 
    the segmented mask folders. 
    Parameters
    ----------
    input_data : str
        Excel or CSV file
    root : str
        (optional) root path to pre-pend to each subject and mask in the input_data file
    Returns
    -------
    raw_data : list
        list with all the subjects to process
    masks : list
        list with the corresponding mask to use to extract the features
    """
    if os.path.isfile(input_data):
        _, _, ext = split_filename(input_data)
        if ext not in ALLOWED_EXT:
            raise Exception('The file extension of the specified input file ({}) is not supported.'
                            ' The allowed extensions are: .xlsx or .csv')
        if ext == '.xlsx':
            files = pd.read_excel(input_data)
        elif ext == '.csv':
            files = pd.read_csv(input_data)
        files=files.dropna()
        try:
            masks = [os.path.join(root, str(x)) for x in list(files[key_col2])]
        except KeyError:
            print('No "masks" column found in the excel sheet. The cropping, if selected, will be performed without it.')
            masks = None
        raw_data = [os.path.join(root, str(x)) for x in list(files[key_col1])] 

        return raw_data, masks
