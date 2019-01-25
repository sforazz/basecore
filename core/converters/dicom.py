from .base import BaseConverter
import subprocess as sp
import os
import glob


class DicomConverter(BaseConverter):
    
    def convert(self, convert_to='nifti', method='dcm2niix'):

        if convert_to == 'nrrd':

            ext = '.nrrd'
            if method=='slicer':
                cmd = (('Slicer --no-main-window --python-code '+'"node=slicer.util.loadVolume('+
                    "'{0}', returnNode=True)[1]; slicer.util.saveNode(node, '{1}'); exit()"+'"')
                    .format(self.toConvert, os.path.join(self.basedir, self.filename)+ext))

            elif method=='mitk':
                cmd = ("MitkCLDicom2Nrrd -i '{0}' -o '{1}'".format(self.toConvert,
                                                                   os.path.join(self.basedir, self.filename)+ext))

            else:
                raise Exception('Not recognized {} method to convert from DICOM to NRRD.'.format(method))

        elif convert_to == 'nifti_gz':

            if method == 'dcm2niix':
                cmd = ("dcm2niix -o {0} -f {1} -z y {2}".format(self.basedir, self.filename,
                                                                self.toConvert))
            else:
                raise Exception('Not recognized {} method to convert from DICOM to NIFTI_GZ.'.format(method))

        elif convert_to == 'nifti':

            if method == 'dcm2niix':
                cmd = ("dcm2niix -o {0} -f {1} {2}".format(self.basedir, self.filename, self.toConvert))
            else:
                raise Exception('Not recognize {} method to convert from DICOM to NIFTI.'.format(method))
        else:
            raise NotImplementedError('The conversion from DICOM to {} has not been implemented yet.'
                                      .format(convert_to))

        sp.check_output(cmd, shell=True)

        if self.clean:
            self.clean_dir

    def clean_dir(self):

        if os.path.isfile(self.toConvert):
            basedir = self.basedir
        elif os.path.isdir(self.toConvert):
            basedir = self.toConvert
            
        toDelete = glob.glob(basedir+'/*.IMA')
        if not toDelete:
            toDelete = glob.glob(basedir+'/*.dcm')
        if toDelete:
            for f in toDelete:
                os.remove(f)
        else:
            print('No DICOM files to delete found in {}'.format(basedir))
