"""
Created on Thu May 23 12:39:50 2019

@author: pgsalome
"""
import nibabel as nib
import os
import numpy as np
import math
import matplotlib.pyplot as plt
from scipy import ndimage
import glob



root_dir=r'/media/fsforazz/Samsung_T5/chordoma_curated/workflows_output/DataCuration/'


def extract_middleSlice(image):
    
    x,y,z=image.shape
    s=smallest(x,y,z)
    if s==z:
        ms=math.ceil(image.shape[2]/2)-1
        return image[:, :, ms].astype('float32')
    elif s==y:
        ms=math.ceil(image.shape[1]/2)-1
        return image[:, ms, :].astype('float32')
    else:
        ms=math.ceil(image.shape[0]/2)-1
        return image[ms, :, :].astype('float32')
    
    
def smallest(num1, num2, num3):
    
    if (num1 < num2) and (num1 < num3):
        smallest_num = num1
    elif (num2 < num1) and (num2 < num3):
        smallest_num = num2
    else:
        smallest_num = num3
    return smallest_num



list_sub = glob.glob(root_dir+'/*/*/T2.nii.gz')
z=0
cnt=0


for j,img_name in enumerate(list_sub,1):
    
    l=j-z
    try:
        image = nib.load(img_name).get_data()
    except:
        os.remove(img_name)
        continue
#     indices = [i for i, x in enumerate(img_name) if x == "/"]
#     scan_d =img_name[indices[-1]+1:]
#     indices2 = [i for i, x in enumerate(scan_d) if x == "_"]
#     scan_d =scan_d[indices2[-1]+1:]
#     indices2 = [i for i, x in enumerate(scan_d) if x == "."]
#     scan_d =scan_d[0:indices2[0]]
    scan_d = img_name.split('/')[-3]+'_'+img_name.split('/')[-2]
    if len(image.shape)>3:
         image=image[:,:,:,0]
    try:
        image=extract_middleSlice(image)
    except:
        image=np.zeros((256,256))
        print(img_name)
    image=ndimage.rotate(image,90)
    ax = plt.subplot(7, 7, l )
    ax.set_title(scan_d)
    ax.axis('off')
    plt.imshow(image,cmap='gray')
    plt.pause(0.001)
    if l % 49 == 0:
        cnt = cnt +1

        plt.show()
        plt.figure()
        z=49*cnt
