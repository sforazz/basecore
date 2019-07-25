from .base import connect, resource_exts, find_executable 
from .exceptions import (
    XnatUtilsUsageError, XnatUtilsError,
    XnatUtilsMissingResourceException)
import os
import errno
import re
import shutil
from xnat.exceptions import XNATResponseError
import subprocess as sp


def varput(subject_or_session_id, variable, value, **kwargs):
    """
    Sets variables (custom or otherwise) of a session or subject in a MBI-XNAT
    project

    User credentials can be stored in a ~/.netrc file so that they don't need
    to be entered each time a command is run. If a new user provided or netrc
    doesn't exist the tool will ask whether to create a ~/.netrc file with the
    given credentials.

    Parameters
    ----------
    subject_or_session_id : str
        Name of subject or session to set the variable of
    variable : str
        Name of the variable to set
    value : str
        Value to set the variable to
    user : str
        The user to connect to the server with
    loglevel : str
        The logging level to display. In order of increasing verbosity
        ERROR, WARNING, INFO, DEBUG.
    connection : xnat.Session
        An existing XnatPy session that is to be reused instead of
        creating a new session. The session is wrapped in a dummy class
        that disables the disconnection on exit, to allow the method to
        be nested in a wider connection context (i.e. reuse the same
        connection between commands).
    server : str | int | None
        URI of the XNAT server to connect to. If not provided connect
        will look inside the ~/.netrc file to get a list of saved
        servers. If there is more than one, then they can be selected
        by passing an index corresponding to the order they are listed
        in the .netrc
    use_netrc : bool
        Whether to load and save user credentials from netrc file
        located at $HOME/.netrc
    """
    with connect(**kwargs) as login:
        # Get XNAT object to set the field of
        if subject_or_session_id.count('_') == 1:
            xnat_obj = login.subjects[subject_or_session_id]
        elif subject_or_session_id.count('_') >= 2:
            xnat_obj = login.experiments[subject_or_session_id]
        else:
            raise XnatUtilsUsageError(
                "Invalid ID '{}' for subject or sessions (must contain one "
                "underscore  for subjects and two underscores for sessions)"
                .format(subject_or_session_id))
        # Set value
        xnat_obj.fields[variable] = value


def varget(subject_or_session_id, variable, default='', **kwargs):
    """
    Gets the value of a variable (custom or otherwise) of a session or subject
    in a MBI-XNAT project

    User credentials can be stored in a ~/.netrc file so that they don't need
    to be entered each time a command is run. If a new user provided or netrc
    doesn't exist the tool will ask whether to create a ~/.netrc file with the
    given credentials.

    Parameters
    ----------
    subject_or_session_id : str
        Name of subject or session to set the variable of
    variable : str
        Name of the variable to set
    default : str
        Default value if object does not have a value
    user : str
        The user to connect to the server with
    loglevel : str
        The logging level to display. In order of increasing verbosity
        ERROR, WARNING, INFO, DEBUG.
    connection : xnat.Session
        An existing XnatPy session that is to be reused instead of
        creating a new session. The session is wrapped in a dummy class
        that disables the disconnection on exit, to allow the method to
        be nested in a wider connection context (i.e. reuse the same
        connection between commands).
    server : str | int | None
        URI of the XNAT server to connect to. If not provided connect
        will look inside the ~/.netrc file to get a list of saved
        servers. If there is more than one, then they can be selected
        by passing an index corresponding to the order they are listed
        in the .netrc
    use_netrc : bool
        Whether to load and save user credentials from netrc file
        located at $HOME/.netrc
    """
    with connect(**kwargs) as login:
        # Get XNAT object to set the field of
        if subject_or_session_id.count('_') == 1:
            xnat_obj = login.subjects[subject_or_session_id]
        elif subject_or_session_id.count('_') >= 2:
            xnat_obj = login.experiments[subject_or_session_id]
        else:
            raise XnatUtilsUsageError(
                "Invalid ID '{}' for subject or sessions (must contain one "
                "underscore for subjects and two underscores for sessions)"
                .format(subject_or_session_id))
        # Get value
        try:
            return xnat_obj.fields[variable]
        except KeyError:
            return default


def get_digests(resource):
    """
    Downloads the MD5 digests associated with the files in a resource.
    These are saved with the downloaded files in the cache and used to
    check if the files have been updated on the server
    """
    result = resource.xnat_session.get(resource.uri + '/files')
    if result.status_code != 200:
        raise XnatUtilsError(
            "Could not download metadata for resource {}. Files "
            "may have been uploaded but cannot check checksums"
            .format(resource.id))
    return dict((r['Name'], r['digest'])
                for r in result.json()['ResultSet']['Result'])


def get_extension(resource_name):
    try:
        ext = resource_exts[resource_name]
    except KeyError:
        ext = ''
    return ext


def _download_dataformat(resource_name, download_dir, session_label,
                         scan_label, exp, scan, subject_dirs, convert_to,
                         converter, strip_name, suffix=False):
    # Get the target location for the downloaded scan
    if subject_dirs:
        parts = session_label.split('_')
        target_dir = os.path.join(download_dir,
                                   '_'.join(parts[:2]), parts[-1])
    else:
        target_dir = os.path.join(download_dir, session_label)
    try:
        os.makedirs(target_dir)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise
    if convert_to:
        try:
            target_ext = resource_exts[convert_to.upper()]
        except KeyError:
            try:
                target_ext = resource_exts[convert_to]
            except KeyError:
                raise XnatUtilsUsageError(
                    "Cannot convert to unrecognised format '{}'"
                    .format(convert_to))
    else:
        target_ext = get_extension(resource_name)
    target_path = os.path.join(target_dir, scan_label)
    if suffix:
        target_path += '-' + resource_name.lower()
    target_path += target_ext
    tmp_dir = target_path + '.download'
    # Download the scan from XNAT
    print('Downloading {}: {}'.format(exp.label, scan_label))
    try:
        scan.resources[resource_name].download_dir(tmp_dir)
    except KeyError:
        raise XnatUtilsMissingResourceException(
            resource_name, session_label, scan_label)
    except XNATResponseError as e:
        # Check for 404 status
        try:
            status = int(
                re.match('.*\(status (\d+)\).*', str(e)).group(1))
            if status == 404:
                print(
                    "Did not find any files for resource '{}' in '{}' "
                    "session".format(resource_name, session_label))
                return True
        except Exception:
            pass
        raise e
    # Extract the relevant data from the download dir and move to
    # target location
    src_path = os.path.join(tmp_dir, session_label, 'scans',
                            (scan_label[:-1]
                             if scan_label.endswith('-') else scan_label),
                            'resources', resource_name, 'files')
    fnames = os.listdir(src_path)
    # Link directly to the file if there is only one in the folder
    if len(fnames) == 1:
        src_path = os.path.join(src_path, fnames[0])
    # Convert or move downloaded dir/files to target path
    dcm2niix = find_executable('dcm2niix')
    mrconvert = find_executable('mrconvert')
    if converter == 'dcm2niix':
        if dcm2niix is None:
            raise XnatUtilsUsageError(
                "Selected converter 'dcm2niix' is not available, "
                "please make sure it is installed and on your "
                "path")
        mrconvert = None
    elif converter == 'mrconvert':
        if mrconvert is None:
            raise XnatUtilsUsageError(
                "Selected converter 'mrconvert' is not available, "
                "please make sure it is installed and on your "
                "path")
        dcm2niix = None
    else:
        assert converter is None
    # Clear target path if it exists
    if os.path.exists(target_path):
        if os.path.isdir(target_path):
            shutil.rmtree(target_path)
        else:
            os.remove(target_path)
    try:
        if (convert_to is None or convert_to.upper() == resource_name):
            # No conversion required
            if strip_name and resource_name in ('DICOM', 'secondary'):
                dcmfiles = sorted(os.listdir(src_path))
                os.mkdir(target_path)
                for f in dcmfiles:
                    dcm_num = int(f.split('-')[-2])
                    file_src_path = os.path.join(src_path, f)
                    file_target_path = os.path.join(
                        target_path, str(dcm_num).zfill(4) + '.dcm')
                    shutil.move(file_src_path, file_target_path)
            else:
                shutil.move(src_path, target_path)
        elif (convert_to in ('nifti', 'nifti_gz') and
              resource_name == 'DICOM' and dcm2niix is not None):
            # convert between dicom and nifti using dcm2niix.
            # mrconvert can do this as well but there have been
            # some problems losing TR from the dicom header.
            zip_opt = 'y' if convert_to == 'nifti_gz' else 'n'
            convert_cmd = '{} -z {} -o "{}" -f "{}" "{}"'.format(
                dcm2niix, zip_opt, target_dir, scan_label,
                src_path)
            sp.check_call(convert_cmd, shell=True)
        elif mrconvert is not None:
            # If dcm2niix format is not installed or another is
            # required use mrconvert instead.
            sp.check_call('{} "{}" "{}"'.format(
                mrconvert, src_path, target_path), shell=True)
        else:
            if (resource_name == 'DICOM' and convert_to in ('nifti',
                                                            'nifti_gz')):
                msg = 'either dcm2niix or '
            raise XnatUtilsUsageError(
                "Please install {} mrconvert to convert between {}"
                "and {} formats".format(
                    msg, resource_name.lower(), convert_to))
    except sp.CalledProcessError as e:
        shutil.move(src_path, os.path.join(
            target_dir,
            scan_label + get_extension(resource_name)))
        print(
            "Could not convert {}:{} to {} format ({})"
            .format(exp.label, scan.type, convert_to,
                    (e.output.strip() if e.output is not None else '')))
    # Clean up download dir
    shutil.rmtree(tmp_dir)
    return True
