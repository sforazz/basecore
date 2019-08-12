import os.path
import hashlib
from .base import (
    sanitize_re, illegal_scan_chars_re, get_resource_name,
    session_modality_re, connect, skip_resources,
    matching_sessions, matching_scans)
from .exceptions import (
    XnatUtilsUsageError, XnatUtilsDigestCheckFailedError,
    XnatUtilsDigestCheckError, XnatUtilsMissingResourceException)
from .utils import get_digests, _download_dataformat
from past.builtins import basestring
from collections import defaultdict
from functools import reduce
from operator import add
from basecore.utils.dicom import DicomInfo
import xnat


DICOM_TAGS = ['PatientSex', 'PatientBirthDate', 'SeriesDate']

def put(session, scan, *filenames, **kwargs):
    """
    Uploads datasets to a MBI-XNAT project (requires manager privileges for the
    project).

    The format of the uploaded file is guessed from the file extension
    (recognised extensions are '.nii', '.nii.gz', '.mif'), the scan entry is
    created in the session and if 'create_session' kwarg is True the
    subject and session are created if they are not already present, e.g.

        >>> xnatutils.put('TEST001_001_MR01', 'a_dataset', ['test.nii.gz'],
                          create_session=True)

    NB: If the scan already exists the 'overwrite' kwarg must be provided to
    overwrite it.

    User credentials can be stored in a ~/.netrc file so that they don't need
    to be entered each time a command is run. If a new user provided or netrc
    doesn't exist the tool will ask whether to create a ~/.netrc file with the
    given credentials.

    Parameters
    ----------
    session : str
        Name of the session to upload the dataset to
    scan : str
        Name for the dataset on XNAT
    filenames : list(str)
        Filenames of the dataset(s) to upload to XNAT or a directory containing
        the datasets.
    overwrite : bool
        Allow overwrite of existing dataset
    create_session : bool
        Create the required session on XNAT to upload the the dataset to
    resource_name : str
        The name of the resource (the data format) to
        upload the dataset to. If not provided the format
        will be determined from the file extension (i.e.
        in most cases it won't be necessary to specify
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
    # Set defaults for kwargs

    overwrite = kwargs.pop('overwrite', False)
    create_session = kwargs.pop('create_session', False,)
    resource_name = kwargs.pop('resource_name', None)
    dicom_attributes = None
    # If a single directory is provided, upload all files in it that
    # don't start with '.'
    if len(filenames) == 1 and isinstance(filenames[0], (list, tuple)):
        filenames = filenames[0]
    if len(filenames) == 1 and os.path.isdir(filenames[0]):
        base_dir = filenames[0]
        filenames = [
            os.path.join(base_dir, f) for f in os.listdir(base_dir)
            if not f.startswith('.')]
    else:
        # Check filenames exist
        if not filenames:
            raise XnatUtilsUsageError(
                "No filenames provided to upload")
        for fname in filenames:
            if not os.path.exists(fname):
                raise XnatUtilsUsageError(
                    "The file to upload, '{}', does not exist"
                    .format(fname))
    if sanitize_re.match(session) or session.count('_') < 2:
        raise XnatUtilsUsageError(
            "Session '{}' is not a valid session name (must only contain "
            "alpha-numeric characters and at least two underscores"
            .format(session))
    if illegal_scan_chars_re.search(scan) is not None:
        raise XnatUtilsUsageError(
            "Scan name '{}' contains illegal characters".format(scan))

    if resource_name is None:
        if len(filenames) == 1:
            resource_name = get_resource_name(filenames[0])
        else:
            raise XnatUtilsUsageError(
                "'resource_name' option needs to be provided when uploading "
                "multiple files")
    else:
        resource_name = resource_name.upper()
        if resource_name == 'DICOM':
            info = DicomInfo(filenames[0])
            _, dicom_attributes = info.get_tag(DICOM_TAGS)
    with connect(**kwargs) as login:
#         login = xnat.connect('https://central.xnat.org', user="fsforazz", password="sono1genio!")
        match = session_modality_re.match(session)
        if match is None or match.group(1) == 'MR':
            session_cls = login.classes.MrSessionData
            scan_cls = login.classes.MrScanData
        elif match is None or match.group(1) == 'CT':
            session_cls = login.classes.CtSessionData
            scan_cls = login.classes.CtScanData
        elif match is None or match.group(1) == 'RT':
            session_cls = login.classes.RtSessionData
            scan_cls = login.classes.RtImageScanData
        else:
            # Default to MRSession
            session_cls = login.classes.MrSessionData
            scan_cls = login.classes.MrScanData
        try:
            xsession = login.experiments[session]
        except KeyError:
            if create_session:
                project_id = session.split('_')[0]
                subject_id = '_'.join(session.split('_')[:2])
                try:
                    xproject = login.projects[project_id]
                except KeyError:
                    raise XnatUtilsUsageError(
                        "Cannot create session '{}' as '{}' does not exist "
                        "(or you don't have access to it)".format(session,
                                                                  project_id))
                # Creates a corresponding subject and session if they don't
                # exist
                xsubject = login.classes.SubjectData(label=subject_id,
                                                        parent=xproject)
                if dicom_attributes is not None:
                    try:
                        xsubject.demographics.gender = dicom_attributes['PatientSex'][0]
                        xsubject.demographics.dob = dicom_attributes['PatientBirthDate'][0]
                    except:
                        print('No valid DICOM attributes found. The subject instance will be '
                              'created without those information.')
                        pass
                xsession = session_cls(
                    label=session, parent=xsubject)
                if dicom_attributes is not None and dicom_attributes['SeriesDate']:
                    xsession.date = dicom_attributes['SeriesDate'][0]
                print("{} session successfully created."
                      .format(xsession.label))
            else:
                raise XnatUtilsUsageError(
                    "'{}' session does not exist, to automatically create it "
                    "please use '--create_session' option."
                    .format(session))
        xdataset = scan_cls(id=scan, type=scan, parent=xsession)
        if overwrite:
            try:
                xdataset.resources[resource_name].delete()
                print("Deleted existing dataset at {}:{}".format(
                    session, scan))
            except KeyError:
                pass
        resource = xdataset.create_resource(resource_name)
        for fname in filenames:
            resource.upload(fname, os.path.basename(fname))
            print("{} uploaded to {}:{}".format(
                fname, session, scan))
        print("Uploaded files, checking digests...")
        # Check uploaded files checksums
        remote_digests = get_digests(resource)
        for fname in filenames:
            remote_digest = remote_digests[
                os.path.basename(fname).replace(' ', '%20')]
            with open(fname, 'rb') as f:
                try:
                    local_digest = hashlib.md5(f.read()).hexdigest()
                except OSError:
                    raise XnatUtilsDigestCheckFailedError(
                        "Could not check digest of '{}' "
                        "(reference '{}'), possibly file too large"
                        .format(fname, remote_digest))
            if local_digest != remote_digest:
                raise XnatUtilsDigestCheckError(
                    "Remote digest does not match local ({} vs {}) "
                    "for {}. Please upload your datasets again"
                    .format(remote_digest, local_digest, fname))
            print("Successfully checked digest for {}".format(
                fname, session, scan))


def get(session, download_dir, scans=None, resource_name=None,
        convert_to=None, converter=None, subject_dirs=False,
        with_scans=None, without_scans=None, strip_name=False,
        skip_downloaded=False, before=None, after=None,
        project_id=None, match_scan_id=True, **kwargs):
    """
    Downloads datasets (e.g. scans) from MBI-XNAT.

    By default all scans in the provided session(s) are downloaded to the
    current working directory unless they are filtered by the provided 'scan'
    kwarg. Both the session name and scan filters can be regular
    expressions, e.g.

        >>> xnatutils.get('MRH017_001_MR.*', '/home/tclose/Downloads',
                          scans='ep2d_diff.*')

    The destination directory can be specified by the 'directory' kwarg.
    Each session will be downloaded to its own folder under the destination
    directory unless the 'subject-dir' kwarg is provided in which case the
    sessions will be grouped under separate subject directories.

    If there are multiple resources for a dataset on MBI-XNAT (unlikely) the
    one to download can be specified using the 'resource_name' kwarg, otherwise
    the only recognised neuroimaging format (e.g. DICOM, NIfTI, MRtrix format).

    DICOM files (ONLY DICOM file) name can be stripped using the kwarg
    'strip_name'. If specified, the final name will be in the format
    000*.dcm.

    The downloaded images can be automatically converted to NIfTI or MRtrix
    formats using dcm2niix or mrconvert (if the tools are installed and on the
    system path) by providing the 'convert_to' kwarg and specifying the
    desired format.

        >>> xnatutils.get('TEST001_001_MR01', '/home/tclose/Downloads',
                          scans='ep2d_diff.*', convert_to='nifti_gz')

    User credentials can be stored in a ~/.netrc file so that they don't need
    to be entered each time a command is run. If a new user provided or netrc
    doesn't exist the tool will ask whether to create a ~/.netrc file with the
    given credentials.

    Parameters
    ----------
    session : str | list(str)
        Name of the sessions to download the dataset from
    target : str
        Path to download the scans to. If not provided the current working
        directory will be used
    scans : str | list(str)
        Name of the scans to include in the download. If not provided all scans
        from the session are downloaded. Multiple scans can be specified
    format : str
        The format of the resource to download. Not required if there is only
        one valid resource for each given dataset e.g. DICOM, which is
        typically the case
    convert_to : str
        Runs a conversion script on the downloaded scans to convert them to a
        given format if required converter : str
        choices=converter_choices,
    converter : str
        The conversion tool to convert the downloaded datasets. Can be one of
        '{}'. If not provided and both converters are available, dcm2niix will
        be used for DICOM->NIFTI conversion and mrconvert for other
        conversions.format ', '.joinconverter_choices
    subject_dirs : bool
         Whether to organise sessions within subject directories to hold the
         sessions in or not
    with_scans : list(str)
        A list of scans that the session is required to have (only applicable
        with datatype='session')
    without_scans : list(str)
        A list of scans that the session is required not to have (only
        applicable with datatype='session')
    strip_name : bool
        Whether to strip the default name of each dicom
         file to have just a number. Ex. 0001.dcm. It will
         work just on DICOM files, not NIFTI.
    use_scan_id: bool
        Use scan IDs rather than series type to identify scans
    skip_downloaded : bool
        Whether to ignore previously downloaded sessions (i.e. if there
        is a directory in the download directory matching the session
        name the session will be skipped)
    before : str
        Only select sessions before this date in %Y-%m-%d format
        (e.g. 2018-02-27)
    after : str
        Only select sessions after this date in %Y-%m-%d format
        (e.g. 2018-02-27)
    project_id : str | None
        The ID of the project to list the sessions from. It should only
        be required if you are attempting to list sessions that are
        shared into secondary projects and you only have access to the
        secondary project
    match_scan_id : bool
        Whether to use the scan ID to match scans with if the scan type
        is None
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
    # Convert scan string to list of scan strings if only one provided
    if isinstance(scans, basestring):
        scans = [scans]
    if skip_downloaded:
        skip = [d for d in os.listdir(download_dir)
                if os.path.isdir(os.path.join(download_dir, d))]
    else:
        skip = []
    with connect(**kwargs) as login:
        matched_sessions = matching_sessions(
            login, session, with_scans=with_scans,
            without_scans=without_scans, project_id=project_id,
            skip=skip, before=before, after=after)
        downloaded_scans = defaultdict(list)
        for session in matched_sessions:
            for scan in matching_scans(session, scans,
                                       match_id=match_scan_id):
                scan_label = scan.id
                if scan.type is not None:
                    scan_label += '-' + sanitize_re.sub('_', scan.type)
                downloaded = False
                if resource_name is not None:
                    try:
                        downloaded = _download_dataformat(
                            (resource_name.upper()
                             if resource_name != 'secondary'
                             else 'secondary'), download_dir, session.label,
                            scan_label, session, scan, subject_dirs,
                            convert_to, converter, strip_name)
                    except XnatUtilsMissingResourceException:
                        print(
                            "Did not find '{}' resource for {}:{}, "
                            "skipping".format(
                                resource_name, session.label,
                                scan_label))
                        continue
                else:
                    resource_names = [
                        r.label for r in scan.resources.values()
                        if r.label not in skip_resources]
                    if not resource_names:
                        print(
                            "No valid scan formats for '{}-{}' in '{}' "
                            "(found '{}')"
                            .format(scan.id, scan.type, session,
                                    "', '".join(scan.resources)))
                    elif len(resource_names) > 1:
                        for scan_resource_name in resource_names:
                            downloaded = _download_dataformat(
                                scan_resource_name, download_dir,
                                session.label, scan_label, session, scan,
                                subject_dirs, convert_to, converter,
                                strip_name, suffix=True)
                    else:
                        downloaded = _download_dataformat(
                            resource_names[0], download_dir, session.label,
                            scan_label, session, scan, subject_dirs,
                            convert_to, converter, strip_name)
                if downloaded:
                    downloaded_scans[session.label].append(scan.type)
        if not downloaded_scans:
            print("No scans matched pattern(s) '{}' in specified "
                  "sessions ({})".format(
                      ("', '".join(scans) if scans is not None else ''),
                      "', '".join(s.label for s in matched_sessions)))
        else:
            num_scans = reduce(add, map(len, downloaded_scans.values()))
            print("Successfully downloaded {} scans from {} session(s)"
                  .format(num_scans, len(matched_sessions)))
        return downloaded_scans
