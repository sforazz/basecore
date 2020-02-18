import glob
import pydicom
import os
import shutil
import subprocess as sp
from collections import defaultdict
from nipype.interfaces.base import (
    BaseInterface, TraitedSpec, Directory,
    BaseInterfaceInputSpec)
from nipype.interfaces.base import isdefined


ExplicitVRLittleEndian = '1.2.840.10008.1.2.1'
ImplicitVRLittleEndian = '1.2.840.10008.1.2'
DeflatedExplicitVRLittleEndian = '1.2.840.10008.1.2.1.99'
ExplicitVRBigEndian = '1.2.840.10008.1.2.2'
NotCompressedPixelTransferSyntaxes = [ExplicitVRLittleEndian,
                                      ImplicitVRLittleEndian,
                                      DeflatedExplicitVRLittleEndian,
                                      ExplicitVRBigEndian]


class RTDataSortingInputSpec(BaseInterfaceInputSpec):
    
    input_dir = Directory(exists=True, help='Input directory to sort.')
    out_folder = Directory('RT_sorted_dir', usedefault=True,
                           desc='RT data sorted folder.')


class RTDataSortingOutputSpec(TraitedSpec):
    
    out_folder = Directory(help='RT Sorted folder.')


class RTDataSorting(BaseInterface):
    
    input_spec = RTDataSortingInputSpec
    output_spec = RTDataSortingOutputSpec
    
    def _run_interface(self, runtime):

        input_dir = self.inputs.input_dir
        out_dir = os.path.abspath(self.inputs.out_folder)

        modality_list = [ 'RTPLAN' , 'RTSTRUCT', 'RTDOSE', 'CT']
        
        input_tp_folder = list(set([x for x in glob.glob(input_dir+'/*/*')
                                    for y in glob.glob(x+'/*')
                                    for r in modality_list if r in y]))
        for tp_folder in input_tp_folder:
            sub_name, tp = tp_folder.split('/')[-2:]
            out_basedir = os.path.join(out_dir, sub_name, tp)
            print('Processing Sub: {0}, timepoint: {1}'.format(sub_name, tp))

            plan_name, rtstruct_instance, dose_cubes_instance = self.extract_plan(
                os.path.join(tp_folder, 'RTPLAN'), os.path.join(out_basedir, 'RTPLAN'))
            if plan_name is None:
                continue
            if rtstruct_instance is not None:
                ct_classInstance = self.extract_struct(os.path.join(tp_folder, 'RTSTRUCT'),
                                                       rtstruct_instance,
                                                       os.path.join(out_basedir, 'RTSTRUCT'))
            else:
                print('The RTSTRUCT was not found. With no RTSTRUCT, '
                      'the planning CT instances cannot be extracted')
            if ct_classInstance is not None:
                self.extract_BPLCT(os.path.join(tp_folder, 'CT'), ct_classInstance,
                                   os.path.join(out_basedir, 'RTCT'))
            if dose_cubes_instance is not None:
                self.extract_dose_cubes(os.path.join(tp_folder, 'RTDOSE'), dose_cubes_instance,
                                        os.path.join(out_basedir, 'RTDOSE'))

        return runtime
    
    def extract_plan(self, dir_name, out_dir):
    
        # FInding the RTplan which was used.( taking the last approved plan)
        # From the RTplan metadata, the structure and the doseCubes instance were taken
        if not os.path.isdir(dir_name):
            print('RT plan was not found. With no plan, the doseCubes, '
                  'struct, and planning CT instances cannot be extracted')
            return None, None, None
            
        plan_date, plan_time = 0, 0
        dose_cubes_instance = []
        plan_name = None
        radiation_type = defaultdict(list)

        dcm_files = glob.glob(dir_name+'/*/*.dcm')
    
        # check if multiple radiation treatment has been given
        for f in dcm_files:
            try:
                ds = pydicom.dcmread(f, force=True)
            except:
                continue
            if hasattr(ds, 'BeamSequence'):
                rt = ds.BeamSequence[0].RadiationType
            elif hasattr(ds, 'IonBeamSequence'):
                rt = ds.IonBeamSequence[0].RadiationType
            radiation_type[rt].append(f)

        for f in dcm_files:
            try:
                ds = pydicom.dcmread(f, force=True)
            except:
                continue
            # check if RT plan has plan intent attribute and approval status
                # .If no, default taken as curative and approved
            if hasattr(ds, 'ApprovalStatus'):
                status_check = ds.ApprovalStatus
            else:
                status_check = 'APPROVED'
            if hasattr(ds, 'PlanIntent '):
                plan_intent_check = ds.PlanIntent
            else:
                plan_intent_check = 'CURATIVE'
            if status_check == 'APPROVED' and plan_intent_check == 'CURATIVE':
                plan_curr_plan_date = float(ds.RTPlanDate)
                plan_curr_plan_time = float(ds.RTPlanTime)
                if plan_curr_plan_date > plan_date:
                    plan_date = plan_curr_plan_date
                    plan_time = plan_curr_plan_time
                    plan_name = f
                elif plan_curr_plan_date == plan_date:
                    if plan_curr_plan_time > plan_time:
                        plan_date = plan_curr_plan_date
                        plan_time = plan_curr_plan_time
                        plan_name = f
        if plan_name is None:
            return None,None,None

        ds = pydicom.dcmread(plan_name, force=True)
        try:
            rtstruct_instance = (ds.ReferencedStructureSetSequence[0]
                                 .ReferencedSOPInstanceUID)
        except:
            rtstruct_instance=None
        try:
            for i in range(0, len(ds.ReferencedDoseSequence)):
                singleDose_instance = (ds.ReferencedDoseSequence[i]
                                       .ReferencedSOPInstanceUID + '.dcm')
                dose_cubes_instance.append(singleDose_instance)
        except:
            dose_cubes_instance = None

        plan_dir_old = os.path.split(plan_name)[0]
        plan_dir = os.path.join(out_dir, '1-RTPLAN_Used')
        os.makedirs(plan_dir)
        shutil.copy2(plan_name, plan_dir)
        other_plan = [x for x in glob.glob(dir_name+'/*') if x != plan_dir_old]
        if other_plan:
            other_dir = os.path.join(out_dir, 'Other_RTPLAN')
            os.makedirs(other_dir)
            [shutil.copytree(x, os.path.join(other_dir, x.split('/')[-1]))
             for x in other_plan]

        return plan_name, rtstruct_instance, dose_cubes_instance

    def extract_struct(self, dir_name, rtstruct_instance, out_dir):
        # FInding the RTstruct which was used.( based on the RTsrtuct reference instance in
        # the RTplan metadata)
        ct_class_instance = None
        if not os.path.exists(dir_name) and not os.path.isdir(dir_name):
            print('RTStruct was not found..')
            return None
        dcm_files=glob.glob(dir_name+'/*/*.dcm')
        for f in dcm_files:
            ds = pydicom.dcmread(f,force=True)
            if ds.SOPInstanceUID == rtstruct_instance:
                try:
                    ct_class_instance = ds.ReferencedFrameOfReferenceSequence[0] \
                    .RTReferencedStudySequence[0].RTReferencedSeriesSequence[0] \
                    .SeriesInstanceUID
                except:
                    ct_class_instance = None          
                struct_dir = os.path.join(out_dir, '1-RTSTRUCT_Used')
                os.makedirs(struct_dir)
                shutil.copy2(f, struct_dir)
                break
        struct_old_dir = os.path.split(f)[0]
        other_rt = [x for x in glob.glob(dir_name+'/*') if x != struct_old_dir]
        if other_rt:
            other_dir = os.path.join(out_dir, 'Other_RTSTRUCT')
            os.makedirs(other_dir)
            [shutil.copytree(x, os.path.join(other_dir, x.split('/')[-1]))
             for x in other_rt]

        return ct_class_instance

    def extract_BPLCT(self, dir_name, ct_class_instance, out_dir):

        if not os.path.exists(dir_name) and not os.path.isdir(dir_name):
            print('BPLCT was not found..')
            return None

        dcm_folders = glob.glob(dir_name+'/*')
        for image in dcm_folders:
            img_name = image.split('/')[-1]
            dcm_files=[os.path.join(image, item) for item in os.listdir(image)
                       if ('.dcm' in item)]
            try:
                ds = pydicom.dcmread(dcm_files[0],force=True)
                series_instance_uid = ds.SeriesInstanceUID
            except:
                series_instance_uid = ''
            if  series_instance_uid == ct_class_instance:
                BPLCT_dir = os.path.join(out_dir, '1-BPLCT_Used_'+img_name)
                os.makedirs(BPLCT_dir)
                for f in dcm_files:
                    shutil.copy2(f, BPLCT_dir)
                break
        ct_old_dir = os.path.split(f)[0]
        other_ct = [x for x in glob.glob(dir_name+'/*') if x != ct_old_dir]
        if other_ct:
            other_dir = os.path.join(out_dir, 'Other_CT')
            os.makedirs(other_dir)
            [shutil.copytree(x, os.path.join(other_dir, x.split('/')[-1]))
             for x in other_ct]

    def extract_dose_cubes(self, dir_name, dose_cubes_instance, out_dir):

        dose_physical_found = False
        dose_rbe_found = False
        if not os.path.isdir(dir_name):
            print('RTDOSE was not found..')
            return None

        dcm_files = glob.glob(dir_name+'/*/*.dcm')

        for f in dcm_files:
#             indices = [i for i, x in enumerate(f) if x == "/"]
            folder_name, f_name = f.split('/')[-2:]
            if all(f_name != dose_cubes_instance[i] \
                   for i in range(0, len(dose_cubes_instance))) and dose_cubes_instance!="":
#             if all(f[indices[-1]+1:] != dose_cubes_instance[i] \
#                    for i in range(0, len(dose_cubes_instance))) and dose_cubes_instance!="":

                other_dir = os.path.join(out_dir, 'Other_RTDOSE', folder_name)
                if not os.path.isdir(other_dir):
                    os.makedirs(other_dir)
                shutil.copy2(f, other_dir)
#                 if not os.listdir(f[0:indices[-1]]):
#                     os.rmdir(f[0:indices[-1]])
            else:
                try:
                    ds = pydicom.dcmread(f,force=True)
                    dose_type = ds.DoseType
                    dose_summation_type = ds.DoseSummationType
                except:
                    dose_type = ''
                    dose_summation_type = ''
                #check whether the dose is compressed, if yes decompress
                if ds.file_meta.TransferSyntaxUID not in \
                        NotCompressedPixelTransferSyntaxes:
                    self.decompress_dose(f)
                if dose_type == 'EFFECTIVE':
                    if 'PLAN' in dose_summation_type:
                        rbe_name = '1-RBE_Used'
                        dose_rbe_found = True
                    elif dose_summation_type == 'FRACTION':
                        rbe_name = '1-RBEFRACTION_Used'
                        dose_rbe_found = True
                    if dose_rbe_found:
                        rbe_dir = os.path.join(out_dir, rbe_name)
                        os.makedirs(rbe_dir)
                        shutil.copy2(f, rbe_dir)
                    else:
                        print('dose_RBE_Cube was not found.')
                if dose_type == 'PHYSICAL':
                    if 'PLAN' in dose_summation_type:
                        phy_name = '1-PHYSICAL_Used'
                        dose_physical_found=True
                    elif dose_summation_type == 'FRACTION':
                        phy_name = '1-PHYSICALFRACTION_Used'
                        dose_physical_found=True
                    if dose_physical_found:
                        phy_dir = os.path.join(out_dir, phy_name)
                        os.makedirs(phy_dir)
                        shutil.copy2(f, phy_dir)
                    else:
                        print('dose_Physical_Cube was not found.')

    def decompress_dose(self, i):

        cmd = ("dcmdjpeg {0} {1} ".format(i, i))
        sp.check_output(cmd, shell=True)

    def _list_outputs(self):
        outputs = self._outputs().get()
        if isdefined(self.inputs.out_folder):
            outputs['out_folder'] = os.path.abspath(
                self.inputs.out_folder)

        return outputs
