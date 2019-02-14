from skimage.filters.thresholding import threshold_otsu
from scipy.spatial.distance import cdist
import numpy as np
import nibabel as nb
from scipy.ndimage.morphology import binary_erosion


def binarization(image):
    
    th = threshold_otsu(image)

    image[image>=th] = 1
    image[image!=1] = 0
    
    return image


def eucl_max(nii1, nii2, percentile=100):

        origdata1 = nb.load(nii1).get_data()
        origdata1 = np.logical_not(
            np.logical_or(origdata1 == 0, np.isnan(origdata1)))
        origdata2 = nb.load(nii2).get_data()
        origdata2 = np.logical_not(
            np.logical_or(origdata2 == 0, np.isnan(origdata2)))

#         if isdefined(mask_volume):
#             maskdata = nb.load(mask_volume).get_data()
#             maskdata = np.logical_not(
#                 np.logical_or(maskdata == 0, np.isnan(maskdata)))
#             origdata1 = np.logical_and(maskdata, origdata1)
#             origdata2 = np.logical_and(maskdata, origdata2)

        if origdata1.max() == 0 or origdata2.max() == 0:
            return np.NaN

        border1 = _find_border(origdata1)
        border2 = _find_border(origdata2)

        set1_coordinates = _get_coordinates(border1, nb.load(nii1).affine)
        set2_coordinates = _get_coordinates(border2, nb.load(nii2).affine)
        distances = cdist(set1_coordinates.T, set2_coordinates.T)
        mins = np.concatenate((np.amin(distances, axis=0),
                               np.amin(distances, axis=1)))

        return np.percentile(mins, percentile)


def _find_border(data):

        eroded = binary_erosion(data)
        border = np.logical_and(data, np.logical_not(eroded))
        return border


def _get_coordinates(data, affine):
    if len(data.shape) == 4:
        data = data[:, :, :, 0]
    indices = np.vstack(np.nonzero(data))
    indices = np.vstack((indices, np.ones(indices.shape[1])))
    coordinates = np.dot(affine, indices)
    return coordinates[:3, :]
