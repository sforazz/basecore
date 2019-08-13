from skimage.filters.thresholding import threshold_otsu
from scipy.spatial.distance import cdist
import numpy as np
import nibabel as nb
from scipy.ndimage.morphology import binary_erosion
from skimage.transform import resize
from skimage import img_as_bool
import subprocess as sp


def binarization(image):
    
    th = threshold_otsu(image)
    image[image>=th] = 1
    image[image!=1] = 0
    
    return image


def cluster_correction(image, th=0.5, min_extent=10000):
    
    out_image = image.split('.nii.gz')[0]+'_cc.nii.gz'
    out_text = image.split('.nii.gz')[0]+'_cc.txt'
    outname = image.split('.nii.gz')[0]+'_corrected.nii.gz'
    cmd = 'cluster -i {0} -t {1} -o {2} --minextent={3} --olmax={4}'.format(
        image, th, out_image, min_extent, out_text)
    _ = sp.check_output(cmd, shell=True)
    with open(out_text, 'r') as f:
        res = [x.split() for x in f]
    mat = np.asarray(res[1:]).astype('float')
    clusters = list(set(mat[mat[:, 1] > 0.95][:, 0]))
    add_cmd = None
    for i, cl in enumerate(clusters):
        if len(clusters) > 2:
            print('Found {0} clusters for image {1}, please check because the'
                  ' usual number of clusters should be not greater than 2.'.format(len(clusters), image))
        out_cl = image.split('.nii.gz')[0]+'_cc_{}.nii.gz'.format(cl)
        if len(clusters) > 1:
            cmd = 'fslmaths {0} -uthr {1} -thr {1} -bin {2}'.format(out_image, cl, out_cl)
        else:
            cmd = 'fslmaths {0} -uthr {1} -thr {1} -bin {2}'.format(out_image, cl, outname)
        sp.check_output(cmd, shell=True)
        if len(clusters) > 1:
            if i == 0:
                add_cmd = 'fslmaths {} -add'.format(out_cl)
            elif i == len(clusters)-1:
                add_cmd = add_cmd + ' {0} {1}'.format(out_cl, outname)
            else:
                add_cmd = add_cmd + ' {0} -add'.format(out_cl)
    if add_cmd is not None:
        sp.check_output(add_cmd, shell=True)


def resize_image(image, old_spacing, order=0, new_spacing=(3, 3, 3)):

    resampling_factor = (new_spacing[0]/old_spacing[0], new_spacing[1]/old_spacing[1], new_spacing[2]/old_spacing[2])
    new_shape = (image.shape[0]//resampling_factor[0], image.shape[1]//resampling_factor[1], image.shape[2]//resampling_factor[2])
    return resize(image, new_shape, order=order, mode='edge', cval=0, anti_aliasing=False)



def eucl_max(nii1, nii2, percentile=100, new_spacing=(3, 3, 3)):

        hd1 = nb.load(nii1).header
        origdata1 = nb.load(nii1).get_data()
        print(np.max(origdata1))
        origdata1 = resize_image(origdata1, old_spacing=(0.08, 0.08, 0.08), new_spacing=new_spacing)
#         origdata1 = resize_image(origdata1, old_spacing=hd1.get_zooms(), new_spacing=new_spacing)
        origdata1[origdata1>0] = 1.0
        im2save = nb.Nifti1Image(origdata1, affine=np.eye(4))
        nb.save(im2save, '/home/fsforazz/Desktop/resampled_2.nii.gz')
        print(origdata1.shape)
        print(np.max(origdata1))
        origdata1 = np.logical_not(
            np.logical_or(origdata1 == 0, np.isnan(origdata1)))
        hd2 = nb.load(nii2).header
        origdata2 = nb.load(nii2).get_data()
        origdata2 = resize_image(origdata2, old_spacing=(0.08, 0.08, 0.08), new_spacing=new_spacing)
#         origdata2 = resize_image(origdata2, old_spacing=hd2.get_zooms(), new_spacing=new_spacing)
        origdata2[origdata2>0] = 1.0
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
#         with open('/home/fsforazz/Desktop/mins.txt', 'w') as f:
#             for m in mins:
#                 f.write(str(m)+'\n')
#         with open('/home/fsforazz/Desktop/mins.txt', 'r') as f: 
#             l = [float(x.strip()) for x in f]

        return np.percentile(mins, percentile)


def eucl_max_orig(nii1, nii2, percentile=100):

        origdata1 = nb.load(nii1).get_data()
        origdata1 = origdata1.astype('uint16')
        origdata1 = np.logical_not(
            np.logical_or(origdata1 == 0, np.isnan(origdata1)))
        origdata2 = nb.load(nii2).get_data()
        origdata2 = origdata2.astype('uint16')
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
