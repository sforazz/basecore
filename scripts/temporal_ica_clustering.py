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
import matplotlib.pyplot as plt
from sklearn import manifold
from scipy import stats
import subprocess as sp


def gl_distribution_calculation(labels, sm_path, tps_dict):

    pdf_info = []
    gvs = []
    for cluster_num in list(set(labels)):
        spatial_maps = [sm_path[x] for x in np.where(labels == cluster_num)[0]]
        grey_levels_val = None
        for sm in spatial_maps:
            sub_name = sm.split('/')[-1].split('_')[0]
            sub_name = sm.split('/')[-2]
            try:
                ica_map = nib.load(sm).get_data()
            except:
                print(sm)
            x, y, z = np.where(ica_map >= 1.7)
            try:
                ref_path = tps_dict[sub_name]['REF']['image']

                ref_data = nib.load(ref_path).get_data()
#                 ref_data = zscoring_image(ref_data)
                gls = ref_data[x, y, z]
                if grey_levels_val is None:
                    grey_levels_val = gls
                else:
                    grey_levels_val = np.concatenate([grey_levels_val, gls])
            except:
                print(sm)
        gvs.append(grey_levels_val)    
        plot.hist(grey_levels_val, bins=100)
        pdf_info.append([np.mean(grey_levels_val), np.std(grey_levels_val)])
    stats.ttest_ind(gvs[0], gvs[1])
    stats.ttest_ind(gvs[0], gvs[2])
    stats.ttest_ind(gvs[1], gvs[2])
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

#     gtv = '/media/fsforazz/Samsung_T5/GBM_project/features_temporal_ICA/data/data_for_ICA/ICA_validation/0000100727/20100331_REF/brain_mask.nii.gz'
#     image = '/media/fsforazz/Samsung_T5/GBM_project/features_temporal_ICA/data/data_for_ICA/ICA_validation/0000100727/20100331_REF/CT1_reg2T1_ref_masked.nii.gz'
    gtv = nib.load(gtv).get_data()
    x, y, z = np.where(gtv > 0)
    if x.any():
        data = nib.load(image).get_data()
#         data = zscoring_image(data)
        gtv_data = data[x, y, z]
        cluster = np.zeros((gtv.shape+(len(pdf_info),)))
        for i in range(x.shape[0]):
            z_scores = [(gtv_data[i] - x[0])/x[1] for x in pdf_info]
            if np.min(np.abs(z_scores)) < 1:
                index = np.where(np.abs(np.asarray(z_scores)) == np.min(np.abs(z_scores)))[0][0]
                cluster[x[i], y[i], z[i], index] = 1
            else:
                print()
        for i in range(cluster.shape[-1]):
            outname = image.split('.nii.gz')[0]+'_cluster_{}.nii.gz'.format(i+1)
            im2save = nib.Nifti1Image(cluster[:, :, :, i], affine=nib.load(image).affine)
            nib.save(im2save, outname)


subs = sorted(glob.glob('/media/fsforazz/Samsung_T5/GBM_project/features_temporal_ICA/'
                        'data/data_for_ICA/GBM_sorted_manually_segmentation_results/*'))
result_dir = '/home/fsforazz/Desktop/GBM_sorted_manually_ICA_results_melodic/'
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
#         image_path = session.replace('GBM_sorted_manually_segmentation_results',
#                                      'GBM_sorted_manually_warps')
#         image_path = image_path.replace('_REF', '')
        session_name = session.split('/')[-1]
        if '_REF' in session:
                session_name = 'REF'
        if os.path.isfile(os.path.join(session, '..','CT1_bc_zscored_mc_confreg.nii.gz')):
#         if os.path.isfile(os.path.join(session, 'CT1_reg2T1_ref_masked_bc_zscored.nii.gz')):
            data_dict[sub_name][session_name] = {}
            data_dict[sub_name][session_name]['tumor'] = os.path.join(
                session, 'Tumor_predicted.nii.gz')
            data_dict[sub_name][session_name]['image'] = os.path.join(
                    session, '..', 'CT1_bc_zscored_mc_confreg.nii.gz')
#             data_dict[sub_name][session_name]['image'] = os.path.join(
#                     session, 'CT1_reg2T1_ref_masked_bc_zscored.nii.gz')
        else:
            print(sub_name)
    if not data_dict[sub_name]:
        del data_dict[sub_name]
            

def plot_tc(tc):
    cl = ['b', 'y', 'g', 'r']
    for i, c in enumerate(cl):
        plot.plot(tc[i, :].T, c, lw=3, label='component {}'.format(i+1))
    plot.xticks(range(9), range(1, 10))
    plot.tick_params(axis='both', labelsize=20)
    plot.legend(prop={'size': 20})

def plot_centroids(tc):
    cl = ['r', 'b', 'g', 'purple', 'orange']
    for i, c in enumerate(cl):
        plot.plot(np.mean(tc[labels==i+1,:].T, axis=1), c, lw=4, label='centroid {}'.format(i+1))
#         plot.plot(tc[i, :].T, c, lw=3, label='component {}'.format(i+1))
    plot.xticks(range(9), range(1, 10))
    plot.tick_params(axis='both', labelsize=30)
    plot.legend(prop={'size': 30})
        
# tc, sm_path = ICA_calculation(data_dict, 4, result_dir)
# np.save(os.path.join(result_dir, 'timecourses.npy'), tc)
# with open(os.path.join(result_dir, 'spatial_map_paths.txt'), 'w') as f:
#     for el in sm_path:
#         f.write(el+'\n')
tc = np.load(os.path.join(result_dir, 'timecourses_confreg_comp4.npy'))
# plot_tc(tc)
with open(os.path.join(result_dir, 'sm_conferg_tumor_comp4.txt'), 'r') as f:
    sm_path = [x.strip() for x in f]
# with open('/home/fsforazz/Desktop/GBM_sorted_manually_ICA_results/indexes.txt', 'r') as f:
#     indexes = [int(x.strip()) for x in f]
# indexes = [x-1 for x in indexes]
# tokeep = [x for y in indexes for x in list(range(y, y+4))]
# # remove = [1, 4, 11, 13, 17, 26, 33, 40, 42, 56]
# sm_path = [sm_path[x] for x in tokeep]
# tsne = manifold.TSNE(n_components=2, init='random', perplexity=30, n_iter=5000)
# tsne_2d = tsne.fit_transform(tc)
# plt.scatter(tsne_2d[:, 0], tsne_2d[:, 1])
# optimalK = OptimalK(n_jobs=2, parallel_backend='joblib')
# n_clusters = optimalK(tc, cluster_array=np.arange(1, 20))
# print('Optimal number of clusters: {}'.format(n_clusters))
# labels, centroids = clustering(tc, 4)

with open('/home/fsforazz/Desktop/GBM_sorted_manually_ICA_results_melodic/kmeans_labels_52_subjects_perp25_5cl_confreg_tumor_comp4.txt', 'r') as f:
    labels = [int(x.strip()) for x in f]
# labels = [int(x.split('/')[-1].split('_')[1]) for x in sm_path]
labels = np.asarray(labels)
plot_centroids(tc)
# pdf_info = gl_distribution_calculation(labels, sm_path, data_dict)
# # for sub in data_dict:
# #     image_path = data_dict[sub]['REF']['image']
# #     gtv_path = data_dict[sub]['REF']['tumor']
# #     tp_0_clustering(image_path, gtv_path, pdf_info)
# # subs = [x for x in glob.glob('/home/fsforazz/Desktop/features_extraction/database_cache/*') if os.path.isdir(x)]
# subs = [x for x in glob.glob('/media/fsforazz/Samsung_T5/GBM_project/features_temporal_ICA/data/data_for_ICA/ICA_validation/*') if os.path.isdir(x)]
# images = [sorted(glob.glob(x+'/*_REF/CT1_reg2T1_ref_masked_bc_zscored.nii.gz'))[0] for x in subs]
# # images = [sorted(glob.glob(x+'/merged_CT1_bc_zscored_mc_confreg.nii.gz'))[0] for x in subs]
# gtvs = [sorted(glob.glob(x+'/*_REF/Tumor_predicted.nii.gz'))[0] for x in subs]
# # images = sorted(glob.glob('/home/fsforazz/Desktop/GBM_TP0_only_MR_validation/*/*/T1KM_preproc.nii.gz'))
# # gtvs = sorted(glob.glob('/home/fsforazz/Desktop/features_extraction/database_cache/*/*/GTV_predicted.nii.gz'))
# for i in range(len(images)):
#     image_path = images[i]
#     gtv_path = gtvs[i]
#     tp_0_clustering(image_path, gtv_path, pdf_info)

dirs = ['/media/fsforazz/Samsung_T5/GBM_project/features_temporal_ICA/data/data_for_ICA/ICA_validation/0000100727',
        '/media/fsforazz/Samsung_T5/GBM_project/features_temporal_ICA/data/data_for_ICA/ICA_validation/0000306999',
        '/media/fsforazz/Samsung_T5/GBM_project/features_temporal_ICA/data/data_for_ICA/ICA_validation/0000964781',
        '/media/fsforazz/Samsung_T5/GBM_project/features_temporal_ICA/data/data_for_ICA/ICA_validation/0001048002',
        '/media/fsforazz/Samsung_T5/GBM_project/features_temporal_ICA/data/data_for_ICA/ICA_validation/0001338467',
        '/media/fsforazz/Samsung_T5/GBM_project/features_temporal_ICA/data/data_for_ICA/ICA_validation/0001622199',
        '/media/fsforazz/Samsung_T5/GBM_project/features_temporal_ICA/data/data_for_ICA/ICA_validation/0001743876',
        '/media/fsforazz/Samsung_T5/GBM_project/features_temporal_ICA/data/data_for_ICA/ICA_validation/0002086044']

for i, curr_dir in enumerate(dirs):
    print('Processing {}'.format(curr_dir))
    os.chdir(curr_dir)
    ref_sess = glob.glob('*_REF')[0]
    for i in range(5):
        cmd = ('fslmeants -i merged_CT1_bc_zscored_mc_confreg.nii.gz -o cluster_{0}_n.txt '
               '-m {1}/CT1_reg2T1_ref_masked_bc_zscored_cluster_{0}.nii.gz'.format(i+1, ref_sess))
        sp.check_output(cmd, shell=True)
        cmd = 'fsl_tsplot -i cluster_{0}_n.txt -o cluster_{0}_n.png'.format(i+1)
        sp.check_output(cmd, shell=True)

os.chdir('/media/fsforazz/Samsung_T5/GBM_project/features_temporal_ICA/data/data_for_ICA/ICA_validation/')

for j in range(3):
    mat = np.zeros((8, 9))
    timecourse = sorted(glob.glob('*/cluster_{}_n.txt'.format(j+1))) 
    for i,t in enumerate(timecourse): 
        tt = np.loadtxt(t) 
        mat[i, :] = (tt - np.min(tt))/(np.max(tt)-np.min(tt))
    print(np.corrcoef(np.mean(tc[labels==j+1,:].T, axis=1), np.mean(mat, axis=0)))
    plt.plot(np.mean(mat,axis=0))
plt.show()
save_clusters(labels, tc, centroids, sm_path, result_dir)

print('Done!')
