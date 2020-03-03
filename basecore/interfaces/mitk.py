import os.path as op
import glob
from nipype.interfaces.base import (
    TraitedSpec, traits, File, CommandLineInputSpec, CommandLine)
from nipype.interfaces.base.traits_extension import InputMultiPath,\
    OutputMultiPath


class CLGlobalFeaturesInputSpec(CommandLineInputSpec):

    in_file = File(
        exists=True, mandatory=True, argstr='-i %s',
        desc='Existing file from where the features will be extracted.')
    mask = File(exists=True, mandatory=True, argstr='-m "%s"',
        desc='Binary mask to be used to extract the features.')
    out_name = traits.Str(
        'mitk_features.csv', argstr='-o %s', usedefault=True, mandatory=True,
        desc='Name of the output file.')
    use_header = traits.Bool(
        False, argstr='--header',
        desc='Whether or not to write the header in the result file.')
    first_order = traits.Bool(
        False, argstr='-fo',
        desc='Calculates volume based features.')
    cooccurence = traits.Bool(
        False, argstr='-cooc2',
        desc='Calculates Co-occurence based features.')
    run_length = traits.Bool(
        False, argstr='-rl',
        desc='Calculates Run-Length based features.')
    int_vol_hist = traits.Bool(
        False, argstr='-ivoh',
        desc='Calculates local intensity based features.')
    local_intensity = traits.Bool(
        False, argstr='-loci',
        desc='Calculates local intensity based features.')
    volume = traits.Bool(
        False, argstr='-vol',
        desc='Calculates volume based features.')
    id = traits.Bool(
        False, argstr='-id',
        desc='Calculates image description features.')
    ngld = traits.Bool(
        False, argstr='-ngld',
        desc='Calculate Neighbouring grey level dependence based features.')
    ngtd = traits.Bool(
        False, argstr='-ngtd',
        desc='Calculates Neighborhood Grey Tone based features.')


class CLGlobalFeaturesOutputSpec(TraitedSpec):

    out_file = File(exists=True)


class CLGlobalFeatures(CommandLine):

    _cmd = 'MitkCLGlobalImageFeatures'
    input_spec = CLGlobalFeaturesInputSpec
    output_spec = CLGlobalFeaturesOutputSpec

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs['out_file'] = op.abspath(self.inputs.out_name)

        return outputs


class VoxelizerInputSpec(CommandLineInputSpec):

    struct_file = File(exists=True, mandatory=True, argstr='-s %s',
                       desc='Filename of the structfile.')
    reference = File(exists=True, mandatory=True, argstr='-r %s',
                     desc='Filename of the reference image.')
    out_name = traits.Str('out_struct.nii', usedefault=True, argstr='-o %s',
                          desc='Output file name. if it used in conjunction '
                          'with flag -m, it is only regarded as hint for the '
                          'file name pattern. VoxelizerTool will add a '
                          'suffix indicating the voxelized structure to each filename.',
                          mandatory=True,)
    regular_expression = traits.Str(argstr='-e "%s"',
                                    desc='set a regular expression describing the'
                                         'structs of interest')
    load_style = traits.Str('itk', argstr='-y %s', usedefault=True,
                            desc='set the load style for the reference'
                                 'file. Available styles are:'
                                 'dicom: normal dicom dose'
                                 'itk: use itk image loading'
                                 'itkDicom: use itk dicom image loading',
                            mandatory=True,)
    multi_structs = traits.Bool(argstr='-m', desc='If provided and if multiple '
                                'structs match the regular regular_expression, '
                                'save all in files')
    binarization = traits.Bool(argstr='-z', desc='Determines if the voxelization should '
                               'be binarized (only values 0 or 1), the threshold value is by 0.5')
    no_strict_voxelization = traits.Bool(argstr='-i', desc='Deviations of wrong voxel volumes are '
                                         'tolerated and corrected.')


class VoxelizerOutputSpec(TraitedSpec):

    out_files = OutputMultiPath(File(exists=True))


class Voxelizer(CommandLine):

    _cmd = 'VoxelizerTool'
    input_spec = VoxelizerInputSpec
    output_spec = VoxelizerOutputSpec

    def _list_outputs(self):
        outputs = self._outputs().get()
        out_name = op.abspath(self.inputs.out_name).split('.nii')[0]
        out_files = sorted(glob.glob(out_name+'*'))
        outputs['out_files'] = out_files

        return outputs