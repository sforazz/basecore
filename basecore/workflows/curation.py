from basecore.interfaces.utils import DicomCheck, ConversionCheck, GetRefRTDose
import nipype
from nipype.interfaces.dcm2nii import Dcm2niix
from basecore.interfaces.plastimatch import DoseConverter
from basecore.workflows.base import BaseWorkflow


class DataCuration(BaseWorkflow):

    def workflow(self):
        
        self.datasource()

        datasource = self.data_source
        ref_sequence = self.ref_sequence
        t10 = self.t10
        sub_id = self.sub_id
        result_dir = self.result_dir
        sessions = self.sessions
        nipype_cache = self.nipype_cache
        sequences = self.sequences
        reference = self.reference
        rt_data = self.rt
        rt_session = self.rt['session']

        workflow = nipype.Workflow('data_convertion_workflow', base_dir=nipype_cache)
    
        datasink = nipype.Node(nipype.DataSink(base_directory=result_dir), "datasink")
        substitutions = [('subid', sub_id)]
        substitutions += [('results/', '{}/'.format(self.workflow_name))]
        if type(ref_sequence) == list:
            to_convert = sequences+ref_sequence
        else:
            to_convert = sequences+[ref_sequence]
        if rt_data is not None:
    
            rt_sequences = [x for x in rt_data.keys() if rt_data[x] and x != 'session']
#             substitutions += [('RTsession', rt_data['session'])]
#             substitutions += [('_converterdoses0/', '')]
#             substitutions += [('_converterphysical0/', '')]
#             substitutions += [('_converterrbe0/', '')]
#             substitutions += [('RTSTRUCT_used/checked_dicoms', 'RTSTRUCT_used/')]
            workflow.connect(datasource, 'rt', datasink, 'results.subid.@rt')  
            to_convert = to_convert + rt_sequences
        else:
            rt_sequences = []
    
        if reference:
            to_convert.append('reference')
        if t10:
            to_convert.append('t1_0')
    
        for seq in to_convert:
            if seq not in rt_sequences:
                dc = nipype.MapNode(interface=DicomCheck(),
                                    iterfield=['dicom_dir'],
                                    name='dc{}'.format(seq))
                workflow.connect(datasource, seq, dc, 'dicom_dir')
                converter = nipype.MapNode(interface=Dcm2niix(),
                                           iterfield=['source_dir', 'out_filename'],
                                           name='converter{}'.format(seq))
                converter.inputs.compress = 'y'
                converter.inputs.philips_float = False
                if seq == 'reference':
                    converter.inputs.merge_imgs = True
                else:
                    converter.inputs.merge_imgs = False
                check = nipype.MapNode(interface=ConversionCheck(),
                                       iterfield=['in_file', 'file_name'],
                                       name='check_conversion{}'.format(seq))
    
                workflow.connect(dc, 'outdir', converter, 'source_dir')
                workflow.connect(dc, 'scan_name', converter, 'out_filename')
                workflow.connect(dc, 'scan_name', check, 'file_name')
                workflow.connect(converter, 'converted_files', check, 'in_file')
                if seq == 'reference':
                    workflow.connect(check, 'out_file', datasink,
                                     'results.subid.REF.@{}_converted'.format(seq))
                elif seq == 't1_0':
                    workflow.connect(check, 'out_file', datasink,
                                     'results.subid.T10.@{}_converted'.format(seq))
                else:
                    workflow.connect(check, 'out_file', datasink,
                                     'results.subid.@{}_converted'.format(seq))
                    for i, session in enumerate(sessions):
                        substitutions += [(('_converter{0}{1}/'.format(seq, i), session+'/'))]
            else:
                if seq != 'rtstruct':
                    if seq == 'rtct':
                        converter = nipype.MapNode(
                            interface=Dcm2niix(),
                            iterfield=['source_dir', 'out_filename'],
                            name='converter{}'.format(seq))
                        converter.inputs.compress = 'y'
                        converter.inputs.philips_float = False
                        converter.inputs.merge_imgs = True
                    else:
                        converter = nipype.MapNode(interface=DoseConverter(),
                                               iterfield=['input_dose', 'out_name'],
                                               name='converter{}'.format(seq))
                    if seq == 'doses':
                        get_dose = nipype.MapNode(interface=GetRefRTDose(),
                                                  iterfield=['doses'],
                                                  name='get_doses')
                        workflow.connect(datasource, 'doses', get_dose, 'doses')
                        workflow.connect(get_dose, 'dose_file', converter, 'input_dose')
                        converter.inputs.out_name = 'Unused_RTDOSE.nii.gz'
                        workflow.connect(
                                converter, 'out_file', datasink,
                                'results.subid.@{}_converted'.format(seq))
                    else:
                        dc = nipype.MapNode(interface=DicomCheck(),
                                            iterfield=['dicom_dir'],
                                            name='dc{}'.format(seq))
                        workflow.connect(datasource, seq, dc, 'dicom_dir')
                        if seq == 'rtct':
                            check = nipype.MapNode(interface=ConversionCheck(),
                                                   iterfield=['in_file', 'file_name'],
                                                   name='check_conversion{}'.format(seq))
                
                            workflow.connect(dc, 'outdir', converter, 'source_dir')
                            workflow.connect(dc, 'scan_name', converter, 'out_filename')
                            workflow.connect(dc, 'scan_name', check, 'file_name')
                            workflow.connect(converter, 'converted_files', check, 'in_file')
                            workflow.connect(
                                check, 'out_file', datasink,
                                'results.subid.@{}_converted'.format(seq))
                        else:
                            workflow.connect(dc, 'dose_file', converter, 'input_dose')
                            workflow.connect(dc, 'scan_name', converter, 'out_name')
                            workflow.connect(
                                converter, 'out_file', datasink,
                                'results.subid.@{}_converted'.format(seq))
                else:
                    dc = nipype.MapNode(interface=DicomCheck(),
                                        iterfield=['dicom_dir'],
                                        name='dc{}'.format(seq))
                    workflow.connect(datasource, seq, dc, 'dicom_dir')
                    workflow.connect(dc, 'outdir', datasink,
                                     'results.subid.@rtstruct')
                    for i, session in enumerate(sessions):
                        substitutions += [(('_dc{0}{1}/checked_dicoms'.format(seq, i),
                                            session+'/RTSTRUCT_used'))]
                for i, session in enumerate(rt_session):
                    substitutions += [(('_converter{0}{1}/'.format(seq, i), session+'/'))]
    
        substitutions += [('_converterreference0/', '')]
        substitutions += [('_convertert1_00/', '')]
    
        datasink.inputs.substitutions =substitutions
    
        return workflow
