import glob
import os
import shutil
from datetime import datetime as dd
import numpy as np
import nibabel as nib
from sklearn.decomposition import FastICA
import matplotlib.pyplot as plot
from sklearn.cluster import KMeans
from gap_statistic import OptimalK


def gl_distribution_calculation(labels, sm_path, tps_dict):

    pdf_info = []
    for cluster_num in list(set(labels)):
        spatial_maps = [sm_path[x] for x in np.where(labels == cluster_num)[0]]
        grey_levels_val = None
        for sm in spatial_maps:
            sub_name = sm.split('/')[-1].split('_')[0]
            ica_map = nib.load(sm).get_data()
            x, y, z = np.where(ica_map >= 1.6)
            ref_path = tps_dict[sub_name]['REF']['image']
            ref_data = nib.load(ref_path).get_data()
            ref_data = zscoring_image(ref_data)
            gls = ref_data[x, y, z]
            if grey_levels_val is None:
                grey_levels_val = gls
            else:
                grey_levels_val = np.concatenate([grey_levels_val, gls])
        pdf_info.append([np.mean(grey_levels_val), np.std(grey_levels_val)])
    return pdf_info


def clustering(array, n_clusters):

#     n_clusters = elbow_estimation(array, True)
    est = KMeans(n_clusters)
    est.fit(array)
    labels = est.labels_
    centroids = est.cluster_centers_.T
    return labels, centroids


def zscoring_ica(sm, tc):

    ica_zscore = np.zeros((sm.shape[0], sm.shape[1])) 
    ica_tc = np.zeros((tc.shape[0], tc.shape[1]))
    for i in range(sm.shape[1]): 
        dt = sm[:, i]-np.mean(sm[:, i]) 
        num = np.mean(dt**3) 
        denom = (np.mean(dt**2))**1.5 
        s = num / denom
        if np.sign(s) == -1: 
            print('Flipping sign of component {}'.format(str(i))) 
            sm[:, i] = -1*sm[:, i]
            tc[:, i] = -1*tc[:, i]
        pc = sm[:, i] 
        vstd = np.linalg.norm(sm[:, i])/np.sqrt(sm.shape[0]-1) 
        if vstd != 0: 
            pc_zscore = sm[:,i]/vstd 
        else: 
            print('Not converting to z-scores as division by zero' 
                  ' warning may occur.')
            pc_zscore = pc
        ica_zscore[:, i] = pc_zscore
        ica_tc[:, i] = zscoring_image(tc[:, i])

    return ica_zscore, ica_tc


def zscoring_image(image):

    image = np.asanyarray(image)
    image = image.astype('float64')
    mns = image.mean()
    sstd = image.std()
    res = (image - mns)/sstd
    return res


def ICA_calculation(data_dict, ica_components, result_dir):
 
    plot_col = ['b', 'r', 'g', 'y', 'k', 'c', 'm']
    tc = []  #ICA time courses
    sm_path = []
    for sub in data_dict:
        try:
            ref_tumor = data_dict[sub]['REF']['tumor']
            ref_image = data_dict[sub]['REF']['image']
        except:
            print()
        ref = nib.load(ref_tumor)
        ref_tumor_data = nib.load(ref_tumor).get_data()
        ref_image_data = nib.load(ref_image).get_data()
        if ref_tumor_data.any():
            ref_x, ref_y, ref_z = np.where(ref_tumor_data > 0)
            ref_tumor_voxels = ref_x.shape[0]
            data_mat = np.zeros((len(data_dict[sub]), ref_tumor_voxels))
            data_mat[0, :] = zscoring_image(ref_image_data[ref_x, ref_y, ref_z])
            for i, session in enumerate(data_dict[sub]):
                if session != 'REF':
                    print(session)
                    image_path = data_dict[sub][session]['image']
#                     tumor_path = data_dict[sub][session]['tumor']
#                     tumor_data = nib.load(tumor_path).get_data()
                    image_data = nib.load(image_path).get_data()
#                     x, y, z = np.where(tumor_data > 0)
                    data_mat[i, :] = zscoring_image(image_data[ref_x, ref_y, ref_z])
#                     if x.shape[0] > ref_tumor_voxels:
#                         data_mat[i, :] = zscoring_image(
#                             image_data[x[:ref_tumor_voxels], y[:ref_tumor_voxels],
#                                        z[:ref_tumor_voxels]])
#                     else:
#                         data_mat[i, :x.shape[0]] = zscoring_image(image_data[x, y, z])
     
            ica = FastICA(n_components=ica_components)
            S_ = ica.fit_transform(data_mat.T)
            A_ = ica.mixing_
            S_zscored, tc_normalized = zscoring_ica(S_, A_)
            tc.append(tc_normalized.T)
            for c in range(ica_components):
                cluster = np.zeros((ref_tumor_data.shape))
                outname = sub+'_component_{}.nii.gz'.format(c+1)
                for i in range(ref_tumor_voxels):
                    cluster[ref_x[i], ref_y[i], ref_z[i]] = S_zscored[i, c]
                im2save = nib.Nifti1Image(cluster, affine=ref.affine)
                nib.save(im2save, os.path.join(result_dir, outname))
                sm_path.append(os.path.join(result_dir, outname))
                plot.plot(tc_normalized[:, c], '-{}'.format(plot_col[c]),
                          label='component_{}'.format(c+1))
            plot.legend()
            plot.savefig(os.path.join(result_dir, sub+'_timecourses.png'))
            plot.close()
    #     else:
    #         print('Empty gtv for subject {}'.format(sub))
     
    tc = np.asarray(tc)
    tc = tc.reshape(tc.shape[0]*tc.shape[1], tc.shape[2])
 
    return tc, sm_path

# def ICA_calculation(data_dict, ica_components, result_dir):
#  
#     plot_col = ['b', 'r', 'g', 'y', 'k']
#     tc = []  #ICA time courses
#     sm_path = []
#     for sub in data_dict:
#         ref_tumor = data_dict[sub]['REF']['tumor']
#         ref_image = data_dict[sub]['REF']['image']
#         ref = nib.load(ref_tumor)
#         ref_tumor_data = nib.load(ref_tumor).get_data()
#         ref_image_data = nib.load(ref_image).get_data()
#         if ref_tumor_data.any():
#             ref_x, ref_y, ref_z = np.where(ref_tumor_data > 0)
#             ref_tumor_voxels = ref_x.shape[0]
#             data_mat = np.zeros((len(data_dict[sub]), ref_tumor_voxels))
#             data_mat[0, :] = zscoring_image(ref_image_data[ref_x, ref_y, ref_z])
#             for i, session in enumerate(data_dict[sub]):
#                 if session != 'REF':
#                     print(session)
#                     image_path = data_dict[sub][session]['image']
#                     tumor_path = data_dict[sub][session]['tumor']
#                     tumor_data = nib.load(tumor_path).get_data()
#                     image_data = nib.load(image_path).get_data()
#                     x, y, z = np.where(tumor_data > 0)
#                     if x.shape[0] > ref_tumor_voxels:
#                         data_mat[i, :] = zscoring_image(
#                             image_data[x[:ref_tumor_voxels], y[:ref_tumor_voxels],
#                                        z[:ref_tumor_voxels]])
#                     else:
#                         data_mat[i, :x.shape[0]] = zscoring_image(image_data[x, y, z])
#      
#             ica = FastICA(n_components=ica_components)
#             S_ = ica.fit_transform(data_mat.T)
#             A_ = ica.mixing_
#             S_zscored, tc_normalized = zscoring_ica(S_, A_)
#             tc.append(tc_normalized.T)
#             for c in range(ica_components):
#                 cluster = np.zeros((ref_tumor_data.shape))
#                 outname = sub+'_component_{}.nii.gz'.format(c+1)
#                 for i in range(ref_tumor_voxels):
#                     cluster[ref_x[i], ref_y[i], ref_z[i]] = S_zscored[i, c]
#                 im2save = nib.Nifti1Image(cluster, affine=ref.affine)
#                 nib.save(im2save, os.path.join(result_dir, outname))
#                 sm_path.append(os.path.join(result_dir, outname))
#                 plot.plot(tc_normalized[:, c], '-{}'.format(plot_col[c]),
#                           label='component_{}'.format(c+1))
#             plot.legend()
#             plot.savefig(os.path.join(result_dir, sub+'_timecourses.png'))
#             plot.close()
#     #     else:
#     #         print('Empty gtv for subject {}'.format(sub))
#      
#     tc = np.asarray(tc)
#     tc = tc.reshape(tc.shape[0]*tc.shape[1], tc.shape[2])
#  
#     return tc, sm_path


def save_clusters(labels, tc, centroids, sm_path, working_dir, out_prefix=''):

    for cluster_num in list(set(labels)):
        save_dir = os.path.join(working_dir, '{}_cluster_{}'.format(out_prefix, cluster_num))
        if not os.path.isdir(save_dir):
            os.mkdir(save_dir)
        plot.plot(tc[labels==cluster_num].T)
        plot.savefig(os.path.join(save_dir, 'all_tcs.png'))
        plot.close()
        plot.plot(centroids[:, cluster_num])
        plot.savefig(os.path.join(save_dir, 'cluster_centroid_tc.png'))
        plot.close()
        for f in [sm_path[x] for x in np.where(labels == cluster_num)[0]]:
            shutil.copy2(f, save_dir)


def tp_0_clustering(image, gtv, pdf_info):

    gtv = nib.load(gtv).get_data()
    x, y, z = np.where(gtv > 0)
    if x.any():
        data = nib.load(image).get_data()
        data = zscoring_image(data)
        gtv_data = data[x, y, z]
        cluster = np.zeros((gtv.shape+(len(pdf_info),)))
        for i in range(x.shape[0]):
            z_scores = [(gtv_data[i] - x[0])/x[1] for x in pdf_info]
            index = np.where(np.abs(np.asarray(z_scores)) == np.min(np.abs(z_scores)))[0][0]
            cluster[x[i], y[i], z[i], index] = 1
        for i in range(cluster.shape[-1]):
            outname = image.split('.nii.gz')[0]+'_cluster_{}.nii.gz'.format(i+1)
            im2save = nib.Nifti1Image(cluster[:, :, :, i], affine=nib.load(image).affine)
            nib.save(im2save, outname)


subs = sorted(glob.glob('/mnt/sdb/GBM_sorted_manually_segmentation_results/*'))
result_dir = '/mnt/sdb/GBM_sorted_manually_ICA_results/'
data_dict = {}

# for sub in subs:
#     sub_name = sub.split('/')[-1]
#     data_dict[sub_name] = {}
#     sessions = [x for x in sorted(glob.glob(os.path.join(sub, '*')))
#                 if os.path.isdir(x) and 'T10' not in x]
#     for session in sessions:
#         session_name = session.split('/')[-1]
#         if '_REF' in session:
#             session_name = 'REF'
#         data_dict[sub_name][session_name] = {}
#         if '_REF' in session:
#             data_dict[sub_name]['REF']['tumor'] = os.path.join(
#                 session, 'Tumor_predicted.nii.gz')
#         else:
#             data_dict[sub_name][session_name]['tumor'] = os.path.join(
#                 session, 'Reference_tumor_normalized.nii.gz')
#         data_dict[sub_name][session_name]['image'] = os.path.join(
#                 session, 'T1_preproc.nii.gz')

for sub in subs:
    sub_name = sub.split('/')[-1]
    data_dict[sub_name] = {}
    sessions = [x for x in sorted(glob.glob(os.path.join(sub, '*')))
                if os.path.isdir(x) and 'T10' not in x]
    for session in sessions:
        image_path = session.replace('GBM_sorted_manually_segmentation_results',
                                     'GBM_sorted_manually_warps')
        image_path = image_path.replace('_REF', '')
        session_name = session.split('/')[-1]
        if '_REF' in session:
                session_name = 'REF'
        if os.path.isfile(os.path.join(image_path, 'T1_reg2T1_ref.nii.gz')):
            data_dict[sub_name][session_name] = {}
            data_dict[sub_name][session_name]['tumor'] = os.path.join(
                session, 'Tumor_predicted.nii.gz')
            data_dict[sub_name][session_name]['image'] = os.path.join(
                    image_path, 'T1_reg2T1_ref.nii.gz')
        else:
            print(sub_name)
    if not data_dict[sub_name]:
        del data_dict[sub_name]
            


tc, sm_path = ICA_calculation(data_dict, 4, result_dir)
np.save(os.path.join(result_dir, 'timecourses.npy'), tc)
with open(os.path.join(result_dir, 'spatial_map_paths.txt'), 'w') as f:
    for el in sm_path:
        f.write(el+'\n')
# tc = np.load(os.path.join(result_dir, 'timecourses.npy'))
# with open(os.path.join(result_dir, 'spatial_map_paths.txt'), 'r') as f:
#     sm_path = [x.strip() for x in f]
optimalK = OptimalK(n_jobs=2, parallel_backend='joblib')
n_clusters = optimalK(tc, cluster_array=np.arange(1, 20))
print('Optimal number of clusters: {}'.format(n_clusters))
labels, centroids = clustering(tc, 8)
pdf_info = gl_distribution_calculation(labels, sm_path, data_dict)
for sub in data_dict:
    image_path = data_dict[sub]['REF']['image']
    gtv_path = data_dict[sub]['REF']['tumor']
    tp_0_clustering(image_path, gtv_path, pdf_info)
save_clusters(labels, tc, centroids, sm_path, result_dir)

print('Done!')
