from nipype.interfaces.base import (
    TraitedSpec, traits, File, CommandLineInputSpec, CommandLine)
import os.path as op


class CLGlobalFeaturesInputSpec(CommandLineInputSpec):
    
    in_file = File(
        exists=True, mandatory=True, argstr='-i %s',
        desc='Existing file from where the features will be extracted.')
    mask = File(
        exists=True, mandatory=True, argstr='-m %s',
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
