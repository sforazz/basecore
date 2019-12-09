import nrrd
import glob
import os
import numpy as np
import nibabel as nib


sub_dir = '/run/user/1000/gvfs/smb-share:server=ad,share=fs/E210-Projekte/Projects/Radiomics/tumor_segmentation/validation_set_brats_seg/'
base_seg = '/run/user/1000/gvfs/smb-share:server=ad,share=fs/E210-Projekte/Projects/Radiomics/tumor_segmentation/validation_set_brats_seg/max'
subjects = [os.path.join(sub_dir, x) for x in os.listdir(sub_dir)
            if os.path.isdir(os.path.join(sub_dir, x)) and 'jenny' not in x
            and 'max' not in x]

for sub in subjects:
    sub_name = sub.split('/')[-1]
    seg_dir = os.path.join(base_seg, sub_name)
    if os.path.isdir(seg_dir):
        ref = nib.load(os.path.join(sub, 'T1KM_bet.nii.gz'))
        ref_data = ref.get_data()
        if os.path.isfile(os.path.join(seg_dir, 'GTV.nrrd')):
            gtv, _ = nrrd.read(os.path.join(seg_dir, 'GTV.nrrd'))
        else:
            print('No GTV for subject {}'.format(sub_name))
            gtv = np.zeros(ref_data.shape, dtype=np.uint16)
        if os.path.isfile(os.path.join(seg_dir, 'necrotic_core.nrrd')):
            necrotic, _ = nrrd.read(os.path.join(seg_dir, 'necrotic_core.nrrd'))
        else:
            print('No necrotic for subject {}'.format(sub_name))
            necrotic = np.zeros(ref_data.shape, dtype=np.uint16)
        if os.path.isfile(os.path.join(seg_dir, 'edema.nrrd')):
            edema, _ = nrrd.read(os.path.join(seg_dir, 'edema.nrrd'))
        else:
            print('No edema for subject {}'.format(sub_name))
            edema = np.zeros(ref_data.shape, dtype=np.uint16)
        if os.path.isfile(os.path.join(seg_dir, 'enhancing_core.nrrd')):
            ec, _ = nrrd.read(os.path.join(seg_dir, 'enhancing_core.nrrd'))
        else:
            print('No ec for subject {}'.format(sub_name))
            ec = np.zeros(ref_data.shape, dtype=np.uint16)
        
        
        intersection1 = necrotic + ec + gtv
        intersection1[intersection1>0] = 1
        inter = edema & intersection1                                                                                                                                                                               
        edema1 = edema*(1-inter)
         
        intersection1 = necrotic +ec                                                                                                                                                                              
        intersection1[intersection1>0] = 1                                                                                                                                                                        
        inter = gtv & intersection1                                                                                                                                                                               
        gtv1 = gtv*(1-inter)
        
        inter = ec & necrotic
        ec1 = ec*(1-inter)
        
        final_mask = necrotic + 2*edema1 + 3*gtv1 + 4*ec1
        
        im2save = nib.Nifti1Image(final_mask, affine=ref.affine)
        nib.save(im2save, os.path.join(sub, 'segmented_tumor_gt.nii.gz'))
    else:
        print('No seg_dir {}'.format(seg_dir))

