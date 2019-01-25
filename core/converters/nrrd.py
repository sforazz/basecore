from .base import BaseConverter
import nrrd
import nibabel as nib
import numpy as np
import os


class NrrdConverter(BaseConverter):

    def convert(self, outname=None):

        if os.path.isdir(self.toConvert):
            raise Exception('Only .nrrd files can be converted into NIFTI. Got directory!')

        data, _ = nrrd.read(self.toConvert)
        tosave = nib.Nifti1Image(data, np.eye(4))
        if outname is not None:
            nib.save(tosave, outname)
        else:
            nib.save(tosave, os.path.join(self.basedir, self.filename)+'.nii.gz')