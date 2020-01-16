import nibabel as nib
import nrrd
import os
import numpy as np
from scipy import ndimage
import glob
from scipy.spatial.distance import euclidean
import matplotlib.pyplot as plot
import statsmodels.api as sm
from statsmodels.stats.multicomp import (pairwise_tukeyhsd,
                                         MultiComparison)
import math


def smallest(num1, num2, num3):

    if (num1 < num2) and (num1 < num3):
        smallest_num = num1
    elif (num2 < num1) and (num2 < num3):
        smallest_num = num2
    else:
        smallest_num = num3
    return smallest_num

def extract_middleSlice(image):

    x,y,z=image.shape
    s=smallest(x,y,z)
    if s==z:
        ms=math.ceil(image.shape[2]/2)-1
        return image[:, :, ms].astype('float32'), ms, 2
    elif s==y:
        ms=math.ceil(image.shape[1]/2)-1
        return image[:, ms, :].astype('float32'), ms, 1
    else:
        ms=math.ceil(image.shape[0]/2)-1
        return image[ms, :, :].astype('float32'), ms, 0


def feat_calc_miss_classified(gtvs ,mask_dir):

    distances = []
    gtv_vols = []
    for gtv in gtvs:
        gtv_name = gtv.split('/')[-1].split('.nrrd')[0]
        mask_name = gtv_name.split('Tumor_')[-1]+'_mask.nii.gz'
        mask = os.path.join(mask_dir, mask_name)
        if os.path.isfile(mask):
            gtv_data, _ = nrrd.read(gtv)
            
            mask_data = nib.load(mask).get_data()
            assert mask_data.shape == gtv_data.shape, "{0} and {1} has different dimensions!".format(gtv_name, mask_name)
            mask_middle, ms, ax = extract_middleSlice(mask_data)
            if ax == 0:
                gtv_middle = gtv_data[ms, :, :]
            elif ax == 1:
                gtv_middle = gtv_data[:, ms, :]
            else:
                gtv_middle = gtv_data[:, :, ms]
            if gtv_middle.any():
                x, _ = np.where(gtv_middle > 0)
                com_gtv = ndimage.measurements.center_of_mass(gtv_middle)
                com_mask = ndimage.measurements.center_of_mass(mask_middle)
                try:
                    dist = euclidean(com_gtv, com_mask)
                    distances.append(dist)
                    gtv_vols.append(x.shape[0])
                except:
                    print('voxels {}'.format(np.where(gtv_middle>0)[0].shape))
            else:
                print('There is no GTV in the middle slice for mask {}'.format(mask_name))
        else:
            print('No brain mask for gtv {}'.format(gtv_name))
    return gtv_vols, distances


def feat_calc_corr_classified():
    gtvs = sorted(glob.glob('/mnt/sdb/Cinderella_FU_seg_reg/'
                            'seg_reg_preprocessing/T1KM_gtv_seg_output/*.nii.gz'))
    mask_dir = '/mnt/sdb/Cinderella_FU_seg_reg/seg_reg_preprocessing/T1KM_gtv_seg/to_bet_bet/'
    distances = []
    gtv_vols = []
    for gtv in gtvs:
        gtv_name = gtv.split('/')[-1].split('.nii.gz')[0]
        mask_name = gtv_name+'_0000_mask.nii.gz'
        mask = os.path.join(mask_dir, mask_name)
        if os.path.isfile(mask):
            gtv_data = nib.load(gtv).get_data()
            x, _, _ = np.where(gtv_data > 0)
            gtv_vols.append(x.shape[0])
            mask_data = nib.load(mask[0]).get_data()
            assert mask_data.shape == gtv_data.shape, "{0} and brain mask have different dimensions!".format(gtv_name)
            com_gtv = ndimage.measurements.center_of_mass(gtv_data)
            com_mask = ndimage.measurements.center_of_mass(mask_data)
            dist = euclidean(com_gtv, com_mask)
            distances.append(dist)
        else:
            print('No brain mask for gtv {}'.format(gtv_name))
    return gtv_vols, distances

gtvs = sorted(glob.glob('/run/user/1000/gvfs/smb-share:server=ad,share=fs'
                        '/E210-Projekte/Projects/Radiomics/classifier_failed_manualContours/T2KM_FP/Tumor_*.nrrd'))
mask_dir = ('/run/user/1000/gvfs/smb-share:server=ad,share=fs'
            '/E210-Projekte/Projects/Radiomics/classifier_failed_manualContours/T2KM_FP_bet/')
 
gtv_vols_cor, distances_cor = feat_calc_miss_classified(gtvs, mask_dir)

gtvs = sorted(glob.glob('/run/user/1000/gvfs/smb-share:server=ad,share=fs'
                              '/E210-Projekte/miss-classified/big_gtv/Tumor_*.nrrd'))
mask_dir = '/run/user/1000/gvfs/smb-share:server=ad,share=fs/E210-Projekte/miss-classified/big_gtv_bet/'

gtv_vols_big, distances_big = feat_calc_miss_classified(gtvs, mask_dir)

gtvs = sorted(glob.glob('/run/user/1000/gvfs/smb-share:server=ad,share=fs'
                              '/E210-Projekte/miss-classified/gtv_middle/Tumor_*.nrrd'))
mask_dir = '/run/user/1000/gvfs/smb-share:server=ad,share=fs/E210-Projekte/miss-classified/gtv_middle_bet/'

gtv_vols_mid, distances_mid = feat_calc_miss_classified(gtvs, mask_dir)

gt_als = np.transpose(np.hstack((gtv_vols_mid, gtv_vols_big, gtv_vols_cor)))
ds_als = np.transpose(np.hstack((distances_mid, distances_big, distances_cor)))
labels = np.transpose(np.hstack((['middle']*len(gtv_vols_mid), ['big']*len(gtv_vols_big), ['corr']*len(gtv_vols_cor))))
mod_gtv = MultiComparison(gt_als, labels)
print(mod_gtv.tukeyhsd())
mod_ds = MultiComparison(ds_als, labels)
print(mod_ds.tukeyhsd())

print(distances_big)
# gtv_vols, distances = feat_calc_corr_classified()

# print('Correlation between distances and volumes: {}'.format(np.corrcoef(gtv_vols, distances)[0, 1]))
# print('Median distance: {}'.format(np.median(distances)))
# print('Median GTV volume: {}'.format(np.median(gtv_vols)))
# plot.scatter(gtv_vols, distances)
# plot.show()
# print(distances)
