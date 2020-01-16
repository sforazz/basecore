from builtins import str
import os
import logging
import avid.common.artefact.defaultProps as artefactProps
import avid.common.artefact as artefactHelper
from avid.common import osChecker, AVIDUrlLocater
from avid.actions import BatchActionBase
from avid.actions.cliActionBase import CLIActionBase
from avid.selectors import TypeSelector
from avid.actions.simpleScheduler import SimpleScheduler

logger = logging.getLogger(__name__)


class BrainExtractionAction(CLIActionBase):
    '''Class that wrapps the single action for the tool HD-BET.'''

    def __init__(self, targetImage, mode='accurate', device='cpu', tta='1', pp='1', actionTag="HD-BET",
                 alwaysDo=False, session=None, additionalActionProps=None, actionConfig=None,
                 propInheritanceDict=None):
         
        CLIActionBase.__init__(self, actionTag, alwaysDo, session, additionalActionProps,
                               actionConfig=actionConfig, propInheritanceDict=propInheritanceDict)
        self._addInputArtefacts(targetImage=targetImage)
        
        self._targetImage = targetImage
        self._mode = mode
        self._device = device
        self._tta = tta
        self._pp = pp
        
        cwd = os.path.dirname(AVIDUrlLocater.getExecutableURL(self._session, "HD-BET",
                                                              actionConfig))
        self._cwd = cwd

    def _generateName(self):

        name = "bet_"+str(artefactHelper.getArtefactProperty(self._targetImage,
                                                                            artefactProps.CASE))\
                +"_"+str(artefactHelper.getArtefactProperty(self._targetImage,
                                                            artefactProps.ACTIONTAG))\
                +"_#"+str(artefactHelper.getArtefactProperty(self._targetImage,
                                                             artefactProps.TIMEPOINT))

        name = name.replace('(','_').replace(')','_')
          
        return name
    
    def _indicateOutputs(self):
      
        artefactRef = self._targetImage
        
        #Specify result artefact                
        self._resultArtefact = self.generateArtefact(
            artefactRef, userDefinedProps={artefactProps.TYPE:artefactProps.TYPE_VALUE_RESULT,
                                           artefactProps.RESULT_SUB_TAG: 'BET'},
            urlHumanPrefix=self._generateName(), urlExtension='nii.gz')
        
        self._resultMask = self.generateArtefact(
            artefactRef, userDefinedProps={artefactProps.TYPE:artefactProps.TYPE_VALUE_RESULT,
                                           artefactProps.RESULT_SUB_TAG: 'MASK'},
            urlHumanPrefix=self._generateName(), urlExtension='nii.gz')

        return [self._resultArtefact, self._resultMask]

    def _prepareCLIExecution(self):
      
        resultPath = artefactHelper.getArtefactProperty(self._resultArtefact, artefactProps.URL)
        
        osChecker.checkAndCreateDir(os.path.split(resultPath)[0])
          
        try:
            execURL = AVIDUrlLocater.getExecutableURL(self._session, "HD-BET",
                                                      self._actionConfig)
            targetImageURL = artefactHelper.getArtefactProperty(self._targetImage, artefactProps.URL)
            
            content = '"' + execURL + '"'
            content += ' -i "' + targetImageURL + '"'
            content += ' -o "' + resultPath + '"'
            content += ' -device ' + self._device
            content += ' -mode ' + self._mode
            content += ' -tta ' + self._tta
            content += ' -pp ' + self._pp
        
        except:
            logger.error("Error for getExecutable.")
            raise
        
        return content


class BrainExtractionBatchAction(BatchActionBase):
    '''Action for batch processing of the HD-BET.'''
    
    def __init__(self,  targetSelector, mode='accurate', device='cpu', tta='1', pp='1', actionTag="HD-BET",
                 alwaysDo = False, session = None, additionalActionProps = None, scheduler = SimpleScheduler(),
                 **singleActionParameters):
      
        BatchActionBase.__init__(self, actionTag, alwaysDo, scheduler, session, additionalActionProps)
        
        self._targetImages = targetSelector.getSelection(self._session.artefacts)
        
        self._mode = mode
        self._device = device
        self._tta = tta
        self._pp = pp
        self._singleActionParameters = singleActionParameters

    def _generateActions(self):
        resultSelector = TypeSelector(artefactProps.TYPE_VALUE_RESULT)
        
        targets = self.ensureRelevantArtefacts(self._targetImages, resultSelector,
                                               "HD-BET targets")
        mode = self._mode
        device = self._device
        tta = self._tta
        pp = self._pp
        
        global logger
        
        actions = list()
        
        for target in targets:

            action = BrainExtractionAction(target, mode=mode, device=device, tta=tta, pp=pp,
                                           actionTag=self._actionTag, alwaysDo=self._alwaysDo,
                                           session=self._session,
                                           additionalActionProps=self._additionalActionProps,
                                           **self._singleActionParameters)
            actions.append(action)
        
        return actions
