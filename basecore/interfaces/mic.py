from nipype.interfaces.base import (
    TraitedSpec, traits, File, CommandLineInputSpec, CommandLine,
    BaseInterfaceInputSpec, Directory, BaseInterface)
import os
import glob
from nipype.interfaces.base import isdefined
from basecore.utils.filemanip import split_filename
try:
    from nnunet.inference.predict import predict_from_folder
    import torch
except ModuleNotFoundError:
    print('Cannot find import nnUNet, no brain extraction or tumor '
          'segmentation can be performed!')

class HDBetInputSpec(CommandLineInputSpec):
    
    _mode_types = ['accurate', 'fast']
    input_file = File(mandatory=True, desc='existing input image',
                      argstr='-i %s', exists=True)
    out_file = traits.Str(argstr='-o %s', desc='output file (or folder) name.')
    mode = traits.Enum(*_mode_types, argstr='-mode %s',
                       desc='Fast will use only one set of parameters whereas '
                             'accurate will use the five sets of parameters '
                             'that resulted from our cross-validation as an '
                             'ensemble. Default: accurate')
    device = traits.Str(argstr='-device %s',
                        desc='Used to set on which device the prediction will run.'
                             'Must be either int or str. Use int for GPU id or "cpu" '
                             'to run on CPU. When using CPU you should consider '
                             'disabling tta. Default for -device is: 0')
    tta = traits.Int(argstr='-tta %i',
                     desc='Whether to use test time data augmentation '
                          '(mirroring). 1= True, 0=False. Disable this if you are '
                          'using CPU to speed things up! Default: 1')
    post_processing = traits.Int(argstr='-pp %i',
                                 desc='Set to 0 to disabe postprocessing '
                                      '(remove all but the largest connected '
                                      'component in the prediction. Default: 1')
    save_mask = traits.Int(argstr='-s %i',
                           desc='If set to 0 the segmentation mask will not be saved')
    overwrite_existing = traits.Int(argstr='--overwrite_existing %i',
                                    desc='Set this to 0 if you do not want to'
                                    ' overwrite existing predictions')


class HDBetOutputSpec(TraitedSpec):

    out_file = File(desc='Brain extracted image.')
    out_mask = File(desc='Brain mask.')


class HDBet(CommandLine):

    _cmd = 'hd-bet'
    input_spec = HDBetInputSpec
    output_spec = HDBetOutputSpec

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs['out_file'] = self._gen_outfilename('out_file')
        if isdefined(self.inputs.save_mask and self.inputs.save_mask != 0):
            outputs['out_mask'] = self._gen_outfilename('out_mask')

        return outputs

    def _gen_outfilename(self, name):
        if name == 'out_file':
            out_file = self.inputs.out_file
            if isdefined(out_file) and isdefined(self.inputs.input_file):
                _, _, ext = split_filename(self.inputs.input_file)
                out_file = self.inputs.out_file+ext
            if not isdefined(out_file) and isdefined(self.inputs.input_file):
                pth, fname, ext = split_filename(self.inputs.input_file)
                print(pth, fname, ext)
                out_file = os.path.join(pth, fname+'_bet'+ext)
        elif name == 'out_mask':
            out_file = self.inputs.out_file
            if isdefined(out_file) and isdefined(self.inputs.input_file):
                _, _, ext = split_filename(self.inputs.input_file)
                out_file = self.inputs.out_file+'_mask'+ext
#             if isdefined(out_file):
#                 pth, fname, ext = split_filename(out_file)
#                 out_file = os.path.join(pth, fname+'_bet_mask'+ext)
            elif not isdefined(out_file) and isdefined(self.inputs.input_file):
                pth, fname, ext = split_filename(self.inputs.input_file)
                print(pth, fname, ext)
                out_file = os.path.join(pth, fname+'_bet_mask'+ext)

        return os.path.abspath(out_file)

    def _gen_filename(self, name):
        if name == 'out_file':
            return self._gen_outfilename('out_file')
        elif name == 'out_mask':
            return self._gen_outfilename('out_mask')
        return None


class HDGlioPredictInputSpec(CommandLineInputSpec):

    t1 = traits.File(mandatory=True, exists=True, argstr='-t1 %s',
                     desc='T1 weighted image')
    ct1 = traits.File(mandatory=True, exists=True, argstr='-t1c %s',
                      desc='T1 weighted image')
    t2 = traits.File(mandatory=True, exists=True, argstr='-t2 %s',
                     desc='T1 weighted image')
    flair = traits.File(mandatory=True, exists=True, argstr='-flair %s',
                        desc='T1 weighted image')
    out_file = traits.Str(argstr='-o %s', desc='output file (or folder) name.')


class HDGlioPredictOutputSpec(TraitedSpec):

    out_file = File(desc='Brain extracted image.')


class HDGlioPredict(CommandLine):

    _cmd = 'hd_glio_predict'
    input_spec = HDGlioPredictInputSpec
    output_spec = HDGlioPredictOutputSpec

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs['out_file'] = self._gen_outfilename()

        return outputs

    def _gen_outfilename(self):

        out_file = self.inputs.out_file
        if isdefined(out_file) and isdefined(self.inputs.t1):
            _, _, ext = split_filename(self.inputs.t1)
            out_file = self.inputs.out_file+ext
        if not isdefined(out_file) and isdefined(self.inputs.t1):
            pth, _, ext = split_filename(self.inputs.t1)
            print(pth, ext)
            out_file = os.path.join(pth, 'segmentation'+ext)

        return os.path.abspath(out_file)


class NNUnetInferenceInputSpec(BaseInterfaceInputSpec):

    input_folder = Directory(exist=True, mandatory=True,
                             desc='Input directory')
    output_folder = traits.Str('nnunet_inference', usedefault=True,
                                desc='Output directory')
    model_folder = Directory(mandatory=True, exist=True,
                             desc='Folder with the results of the nnUnet'
                             'training.')
    folds = traits.Int(6, usedefault=True,
                       desc="folds to use for prediction. Default is None "
                            "which means that folds will be detected "
                            "automatically in the model output folder")
    save_npz = traits.Bool(False, usedefault=True,
                           desc="use this if you want to ensemble"
                                " these predictions with those of"
                                " other models. Softmax "
                                "probabilities will be saved as "
                                "compresed numpy arrays in "
                                "output_folder and can be merged "
                                "between output_folders with "
                                "merge_predictions.py")
    lowres_segmentations = Directory(
        "None", usedefault=True,
        desc="if model is the highres stage of the cascade then you need to use "
             "-l to specify where the segmentations of the corresponding lowres "
             "unet are. Here they are required to do a prediction")
    part_id = traits.Int(0, usedefault=True,
                         desc="Used to parallelize the prediction of "
                              "the folder over several GPUs. If you "
                              "want to use n GPUs to predict this "
                              "folder you need to run this command "
                              "n times with --part_id=0, ... n-1 and "
                              "--num_parts=n (each with a different "
                              "GPU (for example via "
                              "CUDA_VISIBLE_DEVICES=X)")
    num_parts = traits.Int(1, usedefault=True,
                           desc="Used to parallelize the prediction of "
                                "the folder over several GPUs. If you "
                                "want to use n GPUs to predict this "
                                "folder you need to run this command "
                                "n times with --part_id=0, ... n-1 and "
                                "--num_parts=n (each with a different "
                                "GPU (for example via "
                                "CUDA_VISIBLE_DEVICES=X)")
    threads_preprocessing = traits.Int(
        6, usedefault=True,
        desc="Determines many background processes will be used for data "
             "preprocessing. Reduce this if you run into out of memory "
             "(RAM) problems. Default: 6")
    threads_save = traits.Int(
        2, usedefault=True,
        desc="Determines many background processes will be used for segmentation "
             "export. Reduce this if you run into out of memory "
             "(RAM) problems. Default: 2")
    tta = traits.Int(1, usedefault=True,
                     desc="Set to 0 to disable test time data augmentation "
                     "(speedup of factor 4(2D)/8(3D)), lower quality segmentations")
    overwrite = traits.Int(
        1, usedefault=True,
        desc="Set this to 0 if you need to resume a previous prediction. Default: 1 "
             "(=existing segmentations in output_folder will be overwritten)")


class NNUnetInferenceOutputSpec(TraitedSpec):

    output_folder = traits.Str(exist=True, desc='Output directory')
    output_file = File(exists=True, desc='First nifti file inside the'
                       ' output folder.')


class NNUnetInference(BaseInterface):

    input_spec = NNUnetInferenceInputSpec
    output_spec = NNUnetInferenceOutputSpec

    def _run_interface(self, runtime):

        input_folder = self.inputs.input_folder
        output_folder = os.path.abspath(self.inputs.output_folder)
        part_id = self.inputs.part_id
        num_parts = self.inputs.num_parts
        folds = self.inputs.folds
        save_npz = self.inputs.save_npz
        lowres_segmentations = self.inputs.lowres_segmentations
        num_threads_preprocessing = self.inputs.threads_preprocessing
        num_threads_nifti_save = self.inputs.threads_save
        tta = self.inputs.tta
        overwrite = self.inputs.overwrite
        model_folder = self.inputs.model_folder

        if lowres_segmentations == "None":
            lowres_segmentations = None

        if isinstance(folds, list):
            if folds[0] == 'all' and len(folds) == 1:
                pass
            else:
                folds = [int(i) for i in folds]
        elif folds == 6:
            folds = None
        else:
            raise ValueError("Unexpected value for argument folds")

        if tta == 0:
            tta = False
        elif tta == 1:
            tta = True
        else:
            raise ValueError("Unexpected value for tta, Use 1 or 0")

        if overwrite == 0:
            overwrite = False
        elif overwrite == 1:
            overwrite = True
        else:
            raise ValueError("Unexpected value for overwrite, Use 1 or 0")

        predict_from_folder(model_folder, input_folder, output_folder, folds,
                            save_npz, num_threads_preprocessing, num_threads_nifti_save,
                            lowres_segmentations, part_id, num_parts, tta,
                            overwrite_existing=overwrite)
        torch.cuda.empty_cache()

        return runtime

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs['output_folder'] = os.path.abspath(self.inputs.output_folder)
        outputs['output_file'] = sorted(glob.glob(
            os.path.join(os.path.abspath(self.inputs.output_folder), '*.nii.gz')))[0]

        return outputs
