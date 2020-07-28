import pandas as pd
from sklearn.cluster import KMeans
import matplotlib.pyplot as plt
import glob
import numpy as np
from sklearn.decomposition import PCA
from sklearn.preprocessing import scale, normalize
# from gap_statistic import OptimalK
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn import manifold
from matplotlib import offsetbox
import os
import csv
import pydicom
import datetime
from datetime import datetime as dd
import shutil
import pickle


def create_dict_cimp(csv_file, row_id, row_element):

    with open(csv_file, mode='r') as infile:
        reader = csv.reader(infile)
        mydict = {}
        for rows in reader:
            sub_id = rows[row_id].strip().zfill(10) 
            if rows[row_element] and sub_id not in list(mydict.keys()) and 'mutant' not in rows[17] and rows[row_element]!='NA':
                if row_element == 18:
                    if 'mesenchymal' in rows[row_element]:
                        val = 0
                    elif 'RTK' in rows[row_element] and 'II' in rows[row_element]:
                        val = 1
                    elif 'RTK' in rows[row_element] and 'I' in rows[row_element]:
                        val = 2
                    elif 'NP_GLIOMA' in rows[row_element]:
                        val = 'NP_GLIOMA'
                    else:
                        val = 3
                    mydict[sub_id] = val
                else:
                    mydict[sub_id] = rows[row_element]

    return mydict

def create_dict(csv_file, row_id, row_element):

    with open(csv_file, mode='r') as infile:
        reader = csv.reader(infile)
        mydict = {}
        for rows in reader:
            sub_id = rows[row_id].strip().zfill(10) 
#             if (rows[row_element] and sub_id not in list(mydict.keys()) and 
#                     ('glioblastoma' in rows[18] and
#                      ('mesenchymal' in rows[18] or 'RTK' in rows[18]))
#                     and rows[row_element]!='NA'):
            if (rows[row_element] and 
                    ('glioblastoma' in rows[18] and
                     ('mesenchymal' in rows[18] or 'RTK' in rows[18]))
                    and rows[row_element]!='NA'):
                if row_element == 18:
                    if 'mesenchymal' in rows[row_element]:
                        val = 0
                    elif 'RTK' in rows[row_element] and 'II' in rows[row_element]:
                        val = 1
                    elif 'RTK' in rows[row_element] and 'I' in rows[row_element]:
                        val = 2
                    elif 'NP_GLIOMA' in rows[row_element]:
                        val = 'NP_GLIOMA'
                    else:
                        val = 3
                    mydict[sub_id] = val
                else:
                    mydict[sub_id] = rows[row_element]

    return mydict


def create_dict2(csv_file, row_id, row_element):

    with open(csv_file, mode='r') as infile:
        reader = csv.reader(infile)
        mydict = {}
        for rows in reader:
            sub_id = rows[row_id].strip().zfill(10) 
            if rows[row_element] and sub_id not in list(mydict.keys()):
                mydict[sub_id] = rows[row_element]

    return mydict

class BreakIt(Exception): pass

# wanted = ['T1KM', 'ADC', 'T2', 'T1', 'SWI']
# work_dir = ''
# with open('filename', 'rb') as f:
#     data_dict = pickle.load(f)
# input_dir = '/media/fsforazz/portable_hdd/data_sorted/GBM/GBM_sorted/'
# subs_folder = list(set(sorted(glob.glob(input_dir+'/*/*'))))
# for sub_id in data_dict:
#     match = [x for x in subs_folder if sub_id in x][0]
#     sessions = data_dict[sub_id]
#     for session in sessions:
#         if not os.path.isdir(os.path.join(work_dir, sub_id, session)):
#             os.makedirs(os.path.join(work_dir, sub_id, session))
#         sess_path = os.path.join(match, session)
#         scans = [x for x in os.listdir(sess_path) if x in wanted]
#         for scan in scans:
#             tocopy = os.path.join(sess_path, scan)
#             shutil.copytree(tocopy, os.path.join(work_dir, sub_id, session, scan))
# input_dir = '/media/fsforazz/portable_hdd/data_sorted/GBM/GBM_sorted/'
# csv_file = '/run/user/1000/gvfs/smb-share:server=ad,share=fs/E210-Projekte/Projects/Radiomics/patientData/glioma/metadata_20200128_2.csv'
# dict_training = create_dict(csv_file, 5, 9)
# 
# csv_file = '/run/user/1000/gvfs/smb-share:server=ad,share=fs/E210-Projekte/Projects/Radiomics/patientData/glioma/metadata_20200128_expanded.csv'
# dict_age = create_dict(csv_file, 1, 8)
# 
# for sub_id in dict_training:
#     del dict_age[sub_id]
# 
# dict_surgical = {}
# subs_folder = list(set(sorted(glob.glob(input_dir+'/*/*'))))
# no_imaging_data = []
# for sub_id in dict_age:
#     match = [x for x in subs_folder if sub_id in x]
#     if match:
#         try:
#             for path, _, files in os.walk(match[0]):
#                 for f in files:
#                     if f.endswith('.dcm'):
#                         hd = pydicom.read_file(os.path.join(path, f))
#                         try:
#                             birth_date = hd.PatientBirthDate
#                             birth_date = dd.strptime(birth_date, '%Y%m%d')
#                             age_days = int(float(dict_age[sub_id]) * 365)
#                             surgical_date = birth_date + datetime.timedelta(days=age_days)
#                             dict_surgical[sub_id] = surgical_date
#                             raise BreakIt
#                         except KeyError:
#                             print('No birth date in this DICOM')
#                         except ValueError:
#                             print('Wrong date format')
#                             raise BreakIt
#         except BreakIt:
#             pass
#     else:
#         no_imaging_data.append(sub_id)
# 
# dict_im_sessions = {}
# for sub_id in dict_surgical:
#     match = [x for x in subs_folder if sub_id in x]
#     sessions = sorted(os.listdir(match[0]))
#     surgical_date = dict_surgical[sub_id]
#     for session in sessions:
#         sess_date = dd.strptime(session, '%Y%m%d')
#         if (sess_date-surgical_date).days > -30 and (sess_date-surgical_date).days < 0:
#             scans = os.listdir(os.path.join(match[0], session))
#             if 'T1KM' in scans and 'FLAIR' in scans:
#                 dict_im_sessions[sub_id] = os.path.join(match[0], session)
# wd = '/mnt/sdb/GBM_TP0_only_MR_validation'
# for sub_id in dict_im_sessions:
#     to_copy = dict_im_sessions[sub_id]
#     sess_name = to_copy.split('/')[-1]
#     dst = os.path.join(wd, sub_id, sess_name)
#     if not os.path.isdir(dst):
#         os.makedirs(dst)
#     for im in ['T1KM', 'FLAIR']:
#         shutil.copytree(os.path.join(to_copy, im),
#                         os.path.join(dst, im))

# subs1 = [x for x in glob.glob('/home/fsforazz/Desktop/GBM_TP0_only_MR/workflows_output/RadiomicsWorkflow/*') if os.path.isdir(x)]
# subs2 = [x for x in glob.glob('/home/fsforazz/Desktop/GBM_TP0_only_MR_validation_features/workflows_output/RadiomicsWorkflow/*') if os.path.isdir(x)]
# subs = subs1+subs2
# # subs = [x for x in glob.glob('/home/fsforazz/Desktop/GBM_data_ICA_modelling_features/GBM_TP0_validation/workflows_output/RadiomicsWorkflow/*') if os.path.isdir(x)]
#   
# subs = [x for x in glob.glob('/home/fsforazz/Desktop/GBM_TP0_only_MR/workflows_output/only_recurrent/*') if os.path.isdir(x)]
#  
# csvs = []
# for sub in subs:
#     try:
#         csvs.append(sorted(glob.glob(sub+'/*/Features_pyradiomics_T1KM_preproc_N4_zscore_GTV_predicted.csv'))[0])
#     except:
#         continue
# # csvs = [sorted(glob.glob(x+'/*/Features_pyradiomics_ADC_preproc_zscore_GTV_predicted.csv'))[0] for x in subs]
# # csv = glob.glob('/mnt/sdb/GBM_TP0_MRI_only/workflows_output/RadiomicsWorkflow/*/*/Features_pyradiomics_*.csv')
#   
# # sub_names = [x.split('/')[-3] for x in csv]
# csv_file = '/home/fsforazz/Documents/glioma/metadata_20200128_expanded_np_glioma.csv'
# csv_file2 = '/home/fsforazz/Documents/glioma/missing_ica_20200331_filled.csv'
# mydict = create_dict(csv_file, 1, 5)
# # mydict1 = create_dict2(csv_file2, 2, 9)
# # mydict.update(mydict1)
# mydict_s = create_dict(csv_file, 1, 6)
# # mydict_s1 = create_dict2(csv_file2, 2, 10)
# # mydict_s.update(mydict_s1)
# mydict_pv = create_dict(csv_file, 1, 2)
# mydict_mgmt = create_dict(csv_file, 1, 14)
# mydict_mgmt_hd = create_dict(csv_file, 1, 13)
# mydict_pdl1 = create_dict(csv_file, 1, 19)
# mydict_pd1 = create_dict(csv_file, 1, 20)
# mydict_age = create_dict(csv_file, 1, 8)
# mydict_sex = create_dict(csv_file, 1, 9)
# mydict_svz = create_dict(csv_file, 1, 11)
# mydict_npglio = create_dict(csv_file, 1, 18)
#   
# features = []
# to_concat = []
# mat = np.zeros((len(csvs), 1132))
# for f in csvs:
#     sub_id = f.split('/')[-3]
#     db = pd.read_csv(f)
#     db['PID'] = sub_id
#     try:
#         db['TIME'] = mydict[sub_id]
#         db['STATUS'] = mydict_s[sub_id]
#         db['PROGNOSIS'] = mydict_pv[sub_id]
#         db['MGMT'] = mydict_mgmt[sub_id]
#         db['MGMT_HD'] = mydict_mgmt_hd[sub_id]
#         db['PDL1'] = mydict_pdl1[sub_id]
#         db['PD1'] = mydict_pd1[sub_id]
#         db['AGE'] = mydict_age[sub_id]
#         db['SEX'] = mydict_sex[sub_id]
#         db['NP_GLIOMA'] = mydict_npglio[sub_id]
#         db['SVZ'] = mydict_svz[sub_id]
#         db = db[[c for c in db if c in ['PID', 'TIME', 'STATUS', 'PROGNOSIS', 'MGMT', 'MGMT_HD',
#                                         'PDL1', 'PD1', 'AGE', 'SEX', 'SVZ', 'NP_GLIOMA']]+
#                 [c for c in db if c not in ['PID', 'TIME', 'STATUS', 'PROGNOSIS', 'MGMT', 'MGMT_HD',
#                                         'PDL1', 'PD1', 'AGE', 'SEX', 'SVZ', 'NP_GLIOMA']
#                  and 'diagnostic' not in c
#                  and 'Subject' not in c and 'Mask' not in c]]
# #         db = db[[c for c in db if c in ['PID', 'TIME', 'STATUS']]+
# #                 [c for c in db if c not in ['PID', 'TIME', 'STATUS']
# #                  and 'diagnostic' not in c
# #                  and 'Subject' not in c and 'Mask' not in c]]
#         to_concat.append(db)
#     except KeyError:
#         print('{} probably mutant?'.format(sub_id))
#   
# combined_csv = pd.concat(to_concat)
# # combined_csv = pd.concat([pd.read_csv(f) for f in csv])
# combined_csv.to_csv('/home/fsforazz/Documents/survival_analysis_R'
#                     '/combined_csv_npglio_recurrent_tp.csv',
#                     index=False, encoding='utf-8-sig')


subs = [x for x in glob.glob('/home/fsforazz/Desktop/TCGA_processed/workflows_output/RadiomicsWorkflow/*') if os.path.isdir(x)]
  
csvs = []
for sub in subs:
    try:
        csvs.append(sorted(glob.glob(sub+'/*/Features_pyradiomics_CT1_preproc_N4_zscore_GTV_predicted.csv'))[0])
    except:
        continue
# csvs = [sorted(glob.glob(x+'/*/Features_pyradiomics_ADC_preproc_zscore_GTV_predicted.csv'))[0] for x in subs]
# csv = glob.glob('/mnt/sdb/GBM_TP0_MRI_only/workflows_output/RadiomicsWorkflow/*/*/Features_pyradiomics_*.csv')
   
# sub_names = [x.split('/')[-3] for x in csv]
csv_file = '/home/fsforazz/Downloads/clinTCGAGBM450k_export_20200706.csv'
csv_file2 = '/home/fsforazz/Documents/glioma/missing_ica_20200331_filled.csv'
# mydict = create_dict2(csv_file, 2, 7)
# mydict1 = create_dict2(csv_file2, 2, 9)
# mydict.update(mydict1)
# mydict_s = create_dict2(csv_file, 2, 6)
# mydict_s1 = create_dict2(csv_file2, 2, 10)
# mydict_s.update(mydict_s1)
# mydict_pv = create_dict(csv_file, 1, 2)
# mydict_mgmt = create_dict2(csv_file, 2, 9)
# mydict_mgmt_hd = create_dict(csv_file, 1, 13)
mydict_pdl1 = create_dict2(csv_file, 2, 5)
# mydict_pd1 = create_dict(csv_file, 1, 20)
# mydict_age = create_dict(csv_file, 1, 8)
# mydict_sex = create_dict(csv_file, 1, 9)
# mydict_svz = create_dict(csv_file, 1, 11)
# mydict_npglio = create_dict(csv_file, 1, 18)
   
features = []
to_concat = []
mat = np.zeros((len(csvs), 1132))
for f in csvs:
    sub_id = f.split('/')[-3]
    db = pd.read_csv(f)
    db['PID'] = sub_id
    try:
#         db['TIME'] = mydict[sub_id]
#         db['STATUS'] = mydict_s[sub_id]
        db['PDL1'] = mydict_pdl1[sub_id]
        db = db[[c for c in db if c in ['PID', 'PDL1']]+
                [c for c in db if c not in ['PID', 'PDL1']
                 and 'diagnostic' not in c
                 and 'Subject' not in c and 'Mask' not in c]]
#         db = db[[c for c in db if c in ['PID', 'TIME', 'STATUS']]+
#                 [c for c in db if c not in ['PID', 'TIME', 'STATUS']
#                  and 'diagnostic' not in c
#                  and 'Subject' not in c and 'Mask' not in c]]
        to_concat.append(db)
    except KeyError:
        print('{} probably mutant?'.format(sub_id))
   
combined_csv = pd.concat(to_concat)
# combined_csv = pd.concat([pd.read_csv(f) for f in csv])
combined_csv.to_csv('/home/fsforazz/Documents/survival_analysis_R'
                    '/combined_csv_TCGA_PDL1.csv',
                    index=False, encoding='utf-8-sig')

subs = [x for x in glob.glob('/home/fsforazz/Desktop/GBM_sorted_manually_ICA_results_melodic_features/workflows_output/RadiomicsWorkflow/*') if os.path.isdir(x)]

csvs = []
for sub in subs:
    try:
        csvs.append(sorted(glob.glob(sub+'/*/Features_pyradiomics_CT1_cluster_5_6tp_new_tumor_mask.csv'))[0])
    except:
        continue

csvs = ['/home/fsforazz/Downloads/gtv_ica/fs/features/features_ct1_gtv_bw10_z.csv']
csv_file = '/home/fsforazz/Documents/glioma/metadata_20200128_expanded_np_glioma.csv'
csv_file = '/home/fsforazz/Downloads/cindDump_2020-01-28_1.csv'
# csv_file2 = '/home/fsforazz/Documents/glioma/missing_ica_20200331_filled.csv'
mydict = create_dict2(csv_file, 1, 4)
# mydict1 = create_dict2(csv_file2, 2, 9)
# mydict.update(mydict1)
mydict_s = create_dict2(csv_file, 1, 6)
# mydict_s1 = create_dict2(csv_file2, 2, 10)
# mydict_s.update(mydict_s1)
features = []
to_concat = []
mat = np.zeros((len(csvs), 1132))
for f in csvs:
    db_all = pd.read_csv(f)
    for i, sub_id in enumerate(db_all['sub']):
#         sub_id = f.split('/')[-3]
#         db = pd.read_csv(f)
        db = pd.DataFrame(db_all.loc[i, :]).transpose()
        db['PID'] = str(sub_id).zfill(10)
        try:
            db['TIME'] = mydict[str(sub_id).zfill(10)]
            db['STATUS'] = mydict_s[str(sub_id).zfill(10)]
            db = db[[c for c in db if c in ['PID', 'TIME', 'STATUS']]+
                    [c for c in db if c not in ['PID', 'TIME', 'STATUS']
                     and 'diagnostic' not in c
                     and 'Subject' not in c and 'Mask' not in c]]
            to_concat.append(db)
        except KeyError:
            print('{} probably mutant?'.format(sub_id))

combined_csv = pd.concat(to_concat)
# combined_csv = pd.concat([pd.read_csv(f) for f in csv])
combined_csv.to_csv('/home/fsforazz/Documents/survival_analysis_R'
                    '/combined_csv_tcga.csv',
                    index=False, encoding='utf-8-sig')
# for i, csv_file in enumerate(csvs):
#     db = pd.read_csv(csv_file)
#     to_keep = [x for x in db.columns if 'diagnostic' not in x
#                and 'Subject' not in x and 'Mask' not in x]http://marketplace.eclipse.org/marketplace-client-intro?mpc_install=9295
#     for j, key in enumerate(to_keep):
#         mat[i, j] = db[key]
# 
# scaler = StandardScaler()
# mat_n = scaler.fit_transform(mat)
# # pipeline = Pipeline([('scaling', StandardScaler()), ('pca', PCA(n_components=2))])
# # pca_2d = pipeline.fit_transform(mat)
# pca = PCA(n_components=2).fit(mat_n)
# pca_2d = pca.transform(mat_n)
# plt.scatter(pca_2d[:, 0], pca_2d[:, 1])
# optimalK = OptimalK(n_jobs=2, parallel_backend='joblib')
# n_clusters = optimalK(mat_n, cluster_array=np.arange(1, 20))
# kmeans = KMeans(n_clusters=2)
# kmeans.fit(mat_n)
# labels = kmeans.labels_
# plt.figure('K-means with 2 clusters')
# plt.scatter(pca_2d[:, 0], pca_2d[:, 1], c=kmeans.labels_)
# plt.show()
# 
# tsne = manifold.TSNE(n_components=2, init='random', perplexity=100, n_iter=5000)
# tsne_2d = tsne.fit_transform(mat_n)
# plt.scatter(tsne_2d[:, 0], tsne_2d[:, 1])
# cl1 = [csvs[x].split('/')[-3] for x in np.where(labels==0)[0]]
# print()
