from nipype.interfaces.base import (
    BaseInterface, CommandLineInputSpec, TraitedSpec, Directory, File,
    traits, BaseInterfaceInputSpec, InputMultiPath)
import pydicom
import numpy as np
from operator import itemgetter
from pydicom.errors import InvalidDicomError
from pathlib import Path
import shutil
import os
import nibabel as nib
import glob


class DicomCheckInputSpec(BaseInterfaceInputSpec):
    
    dicom_dir = Directory(exists=True, desc='Directory with the DICOM files to check')
    working_dir = Directory(exists=True, desc='Base directory to save the corrected DICOM files')


class DicomCheckOutputSpec(TraitedSpec):
    
    outdir = Directory(exists=True, desc='Path to the directory with the corrected DICOM files')
    scan_name = traits.Str(desc='Scan name')
    base_dir = Directory(exists=True, desc='Root path of outdir')


class DicomCheck(BaseInterface):
    
    input_spec = DicomCheckInputSpec
    output_spec = DicomCheckOutputSpec
    
    def _run_interface(self, runtime):

        dicom_dir = self.inputs.dicom_dir
        wd = self.inputs.working_dir

        sub_name = dicom_dir.split('/')[-4]
        tp = dicom_dir.split('/')[-3]
        scan_name = dicom_dir.split('/')[-2]
        if scan_name == 'RTSTRUCT':
            dicoms = sorted(glob.glob(dicom_dir+'/*.dcm'))
        else:
            dicoms, im_types, series_nums = self.dcm_info()
            dicoms = self.dcm_check(dicoms, im_types, series_nums)
        if dicoms:
            if not os.path.isdir(os.path.join(wd, sub_name, tp, scan_name)):
                os.makedirs(os.path.join(wd, sub_name, tp, scan_name))
            else:
                shutil.rmtree(os.path.join(wd, sub_name, tp, scan_name))
                os.makedirs(os.path.join(wd, sub_name, tp, scan_name))
            for d in dicoms:
                shutil.copy2(d, os.path.join(wd, sub_name, tp, scan_name))
            self.outdir = os.path.join(wd, sub_name, tp, scan_name)
            self.scan_name = scan_name
            self.base_dir = os.path.join(wd, sub_name, tp)
        return runtime
    
    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs['outdir'] = self.outdir
        outputs['scan_name'] = self.scan_name
        outputs['base_dir'] = self.base_dir

        return outputs
    
    def dcm_info(self):
        """Function to extract information from a list of DICOM files in one folder. It returns a list of
        unique image types and scan numbers found in the input list of DICOMS.
        Parameters
        ----------
        dcm_folder : str
            path to an existing folder with DICOM files
        Returns
        -------
        dicoms : list
            list of DICOM files in the folder
        image_types : list
            list of unique image types extracted from the DICOMS
        series_nums : list
            list of unique series numbers extracted from the DICOMS
        """
        dcm_folder = Path(self.inputs.dicom_dir)

        dicoms = sorted(list(dcm_folder.glob('*.dcm')))
        if not dicoms:
            dicoms = sorted(list(dcm_folder.glob('*.IMA')))
            if not dicoms:
                raise Exception('No DICOM files found in {}'.format(dcm_folder))

        ImageTypes = []
        SeriesNums = []
        toRemove = []
        InstanceNums = []
        for dcm in dicoms:
            try:
                header = pydicom.read_file(str(dcm))
                ImageTypes.append(tuple(header.ImageType))
                SeriesNums.append(header.SeriesNumber)
                InstanceNums.append(header.InstanceNumber)
            except AttributeError:
                print ('{} seems to do not have the right DICOM fields and '
                       'will be removed from the folder'.format(dcm))
                toRemove.append(dcm)
            except InvalidDicomError:
                print ('{} seems to do not have a readable DICOM header and '
                       'will be removed from the folder'.format(dcm))
                toRemove.append(dcm)
        # the following lines are to check whether or not there are 2 set of exactly the same DICOM files in the folder
        if (len(InstanceNums) == 2*(len(set(InstanceNums)))) and len(set(SeriesNums)) == 1:
            sortedInstanceNums = sorted(zip(dicoms, InstanceNums), key=itemgetter(1))
            uniqueInstanceNums = [x[0] for x in sortedInstanceNums[:][0:-1:2]]
            toRemove = toRemove+uniqueInstanceNums
        if toRemove:
            for f in toRemove:
                dicoms.remove(f)
        
        return dicoms, list(set(ImageTypes)), list(set(SeriesNums))
    
    def dcm_check(self, dicoms, im_types, series_nums):
        """Function to check the DICOM files in one folder. It is based on the glioma test data.
        This function checks the type of the image (to exclude those that are localizer acquisitions)
        and the series number (if in one folder there are more than one scans then this function will
        return the second one, assuming that it is the one after the contrast agent injection).
        It returns a list of DICOMS which belong to one scan only, ignoring localizer scans. 
        Parameters
        ----------
        dicoms : list
            list of DICOMS in one folder
        im_types : list
            list of all image types extracted from the DICOM headers
        series_nums : list
            list of all scan numbers extracted from the DICOM headers
        Returns
        -------
        dcms : list
            list of DICOMS files
        """
        if len(im_types) > 1:
            im_type = list([x for x in im_types if not
                            'PROJECTION IMAGE' in x][0])
    
            dcms = [x for x in dicoms if pydicom.read_file(str(x)).ImageType==im_type]
        elif len(series_nums) > 1:
            series_num = np.max(series_nums)
            dcms = [x for x in dicoms if pydicom.read_file(str(x)).SeriesNumber==series_num]
        else:
            dcms = dicoms
        
        return [str(x) for x in dcms]


class ConversionCheckInputSpec(BaseInterfaceInputSpec):
    
    in_file = InputMultiPath(File(exists=True), desc='(List of) file that'
                             ' needs to be checked after DICOM to NIFTI conversion')
    file_name = traits.Str(desc='Name that the converted file has to match'
                           ' in order to be considered correct.')


class ConversionCheckOutputSpec(TraitedSpec):
    
    out_file = traits.Str()


class ConversionCheck(BaseInterface):
    
    input_spec = ConversionCheckInputSpec
    output_spec = ConversionCheckOutputSpec
    
    def _run_interface(self, runtime):

        converted = self.inputs.in_file
        scan_name = self.inputs.file_name

        to_remove = []
        base_dir = os.path.dirname(converted[0])
        extra = [x for x in converted if x.split('/')[-1]!='{}.nii.gz'.format(scan_name)]
        if len(extra) == len(converted):
            if len(extra) == 2 and scan_name == 'T2':
                to_remove.append(extra[0])
                os.rename(extra[1], os.path.join(base_dir, 'T2.nii.gz'))
                converted = [os.path.join(base_dir, 'T2.nii.gz')]
            else:
                to_remove += extra
                converted = None
        else:
            to_remove += extra

        if to_remove:
            for f in to_remove:
                os.remove(f)

#         if scan_name != 'CT':
#             shutil.rmtree(os.path.join(base_dir, '{}'.format(scan_name)))

        if converted is not None:
            self.converted = converted[0]
            try:
                ref = nib.load(self.converted)
                data = ref.get_data()
                if len(data.squeeze().shape) == 2 or len(data.squeeze().shape) > 4:
                    os.remove(self.converted)
                elif len(data.squeeze().shape) == 4:
                    im2save = nib.Nifti1Image(data[:, :, :, 0], affine=ref.affine)
                    nib.save(im2save, self.converted)
                elif len(data.dtype) > 0:
                    print('{} is not a greyscale image. It will be deleted.'.format(self.converted))
                    os.remove(self.converted)
            except:
                print('{} failed to save with nibabel. It will be deleted.'.format(self.converted))
                os.remove(self.converted)
            if os.path.isfile(self.converted):
                self.converted = self.converted
        else:
            self.converted = None
        
        if self.inputs.in_file and self.converted is None:
            with open(os.path.join(base_dir, 'corrupeted_scans.txt'), 'a') as f:
                f.write('{}'.format(scan_name))

        return runtime

    def _list_outputs(self):
        outputs = self._outputs().get()
        if self.converted is not None:
            outputs['out_file'] = self.converted

        return outputs


class RemoveRTFilesInputSpec(BaseInterfaceInputSpec):

    source_dir = traits.List()
    out_filename = traits.List()
    output_dir = traits.List()


class RemoveRTFilesOutputSpec(TraitedSpec):

    source_dir = traits.List()
    out_filename = traits.List()
    output_dir = traits.List()


class RemoveRTFiles(BaseInterface):
    
    input_spec = RemoveRTFilesInputSpec
    output_spec = RemoveRTFilesOutputSpec
    
    def _run_interface(self, runtime):
        
        source_dir = self.inputs.source_dir
        out_filename = self.inputs.out_filename
        output_dir = self.inputs.output_dir
        
        indexes = [i for i, x in enumerate(out_filename) if 'RTSTRUCT' not in x]
        self.source_dir = [source_dir[x] for x in indexes]
        self.out_filename = [out_filename[x] for x in indexes]
        self.output_dir = [output_dir[x] for x in indexes]
        
        return runtime
    
    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs['source_dir'] = self.source_dir
        outputs['out_filename'] = self.out_filename
        outputs['output_dir'] = self.output_dir

        return outputs
