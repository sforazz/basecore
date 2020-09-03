import glob
import os
import pandas as pd
import numpy as np
import nibabel as nib


def create_bin_sphere(arr_size, center, r): 
    coords = np.ogrid[:arr_size[0], :arr_size[1], :arr_size[2]] 
    distance = np.sqrt((coords[0] - center[0])**2 +
                       (coords[1]-center[1])**2 +
                       (coords[2]-center[2])**2)  
    return 1*(distance <= r)
 
sphere_radius_mm = 3
clusters = sorted(glob.glob('/home/fsforazz/Desktop/GBM_sorted_manually_ICA_results_melodic'
                            '/data_for_features_extraction/*/session1/cluster_3_tumor_mask.nii.gz'))
 
for cluster_mask_path in clusters:
    print('Processing {}'.format(cluster_mask_path))
#     cluster_mask_path = '/home/fsforazz/Desktop/GBM_sorted_manually_ICA_results_melodic/data_for_features_extraction/0000092173/session1/cluster_1_tumor_mask.nii.gz'
    cluster_name = cluster_mask_path.split('.nii.gz')[0]
    cluster_mask = nib.load(cluster_mask_path)
    cluster_data = cluster_mask.get_fdata()
    cluster_hd = cluster_mask.header
    cluster_resolution = cluster_hd.get_zooms()
    sphere_radius_vox_x = sphere_radius_mm / cluster_resolution[0]
    sphere_radius_vox_y = sphere_radius_mm / cluster_resolution[1]
    sphere_radius_vox_z = sphere_radius_mm / cluster_resolution[2]
    sphere_radius_vox = (
        np.mean([sphere_radius_vox_x, sphere_radius_vox_y, sphere_radius_vox_z]))
    x, y, z = np.where(cluster_data>0)
    cluster_voxels = x.shape[0]
     
    included_spheres = []
    voxels = []
    for i in range(len(x)):
        sphere = create_bin_sphere(cluster_data.shape, [x[i], y[i], z[i]],
                                   sphere_radius_vox)
        diff = cluster_data - sphere
        external_voxels = np.where(diff==-1)[0].shape[0]
        if external_voxels <= cluster_voxels*0.02 and len(voxels) < 200:
            voxels.append(external_voxels)
            included_spheres.append(sphere)
     
    if voxels:
        percentile = np.percentile(voxels, 10)
        z = 1
        for i, sphere in enumerate(included_spheres):
            if voxels[i] <= percentile:
                sphere_name = cluster_name+'_sphere{}.nii.gz'.format(str(z).zfill(5))
                im2save = nib.Nifti1Image(sphere, affine=cluster_mask.affine)
                nib.save(im2save, sphere_name)
                z = z+1
    else:
        print('No included sphere detected')
 
print('Done!')

subs = [x for x in glob.glob('/home/fsforazz/Desktop/GBM_sorted_manually_ICA_results_melodic_features_spheres/workflows_output/RadiomicsWorkflow/*') if os.path.isdir(x)]
  
csvs = [x for y in subs for x in sorted(glob.glob(y+'/*/Features_pyradiomics_CT1_*.csv'))]

to_concat = []
for f in csvs:
    cluster = f.split('/')[-1].split('_')[4]
    db = pd.read_csv(f)
    db['cluster'] = int(cluster)
    try:
        db = db[[c for c in db if c in ['cluster']]+
                [c for c in db if c not in ['cluster']
                 and 'diagnostic' not in c
                 and 'Subject' not in c and 'Mask' not in c]]
        to_concat.append(db)
    except KeyError:
        print('Probably mutant?')
   
combined_csv = pd.concat(to_concat)
# combined_csv = pd.concat([pd.read_csv(f) for f in csv])
combined_csv.to_csv('/home/fsforazz/Documents/survival_analysis_R'
                    '/combined_csv_ICA_sphere.csv',
                    index=False, encoding='utf-8-sig')

print('Done!')
