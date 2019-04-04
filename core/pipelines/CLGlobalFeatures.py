from builtins import str
import os
import logging
import re
import avid.common.artefact.defaultProps as artefactProps
import avid.common.artefact as artefactHelper

from avid.common import osChecker, AVIDUrlLocater
from avid.externals.matchPoint import FORMAT_VALUE_MATCHPOINT

from avid.actions import BatchActionBase
from avid.actions.cliActionBase import CLIActionBase
from avid.linkers import CaseLinker
from avid.selectors import TypeSelector
from avid.actions.simpleScheduler import SimpleScheduler

logger = logging.getLogger(__name__)


class FeatureExtractionAction(CLIActionBase):
    '''Class that wrapps the single action for the tool CLGlobalFeatures.'''

    def __init__(self, targetImage, segmentedMask, features='all', resampling=None, actionTag="CLGlobalFeatures",
                 alwaysDo=False, session=None, additionalActionProps=None, actionConfig=None,
                 propInheritanceDict=None):
         
        CLIActionBase.__init__(self, actionTag, alwaysDo, session, additionalActionProps,
                               actionConfig=actionConfig, propInheritanceDict=propInheritanceDict)
        self._addInputArtefacts(targetImage=targetImage, segmentedMask=segmentedMask)
        
        self._targetImage = targetImage
        self._segmentedMask= segmentedMask
        self._features = features
        self._resampling = resampling
        
        cwd = os.path.dirname(AVIDUrlLocater.getExecutableURL(self._session, "CLGlobalFeatures",
                                                              actionConfig))
        self._cwd = cwd

    def _generateName(self):

        name = "features_calc_from_"+str(artefactHelper.getArtefactProperty(self._targetImage,
                                                                            artefactProps.CASE))\
                +"_"+str(artefactHelper.getArtefactProperty(self._targetImage,
                                                            artefactProps.ACTIONTAG))\
                +"_#"+str(artefactHelper.getArtefactProperty(self._targetImage,
                                                             artefactProps.TIMEPOINT))

        name += "_using_mask_"+str(artefactHelper.getArtefactProperty(self._segmentedMask,
                                                                      artefactProps.CASE))
        name += "_"+str(artefactHelper.getArtefactProperty(self._segmentedMask,
                                                           artefactProps.ACTIONTAG))\
                +"_#"+str(artefactHelper.getArtefactProperty(self._segmentedMask,
                                                             artefactProps.TIMEPOINT))\
                +"_"+str(artefactHelper.getArtefactProperty(self._segmentedMask,
                                                            artefactProps.OBJECTIVE))
        if self._resampling is not None:
            name += "_after_resampling_to_{}mm".format(self._resampling)
        
        pattern = re.compile('[\W]+')
        name = pattern.sub('', name)    
#         name = name.replace('(','_').replace(')','_')
          
        return name
    
    def _indicateOutputs(self):
      
        artefactRef = self._targetImage
        
        #Specify result artefact                
        self._resultArtefact = self.generateArtefact(artefactRef,
                                                     userDefinedProps={artefactProps.TYPE:artefactProps.TYPE_VALUE_RESULT,
                                                                       artefactProps.FORMAT: FORMAT_VALUE_MATCHPOINT},
                                                     urlHumanPrefix=self._generateName(),
                                                     urlExtension='csv')
        return [self._resultArtefact]

    def _prepareCLIExecution(self):
      
        resultPath = artefactHelper.getArtefactProperty(self._resultArtefact, artefactProps.URL)
        
        osChecker.checkAndCreateDir(os.path.split(resultPath)[0])
          
        try:
            execURL = AVIDUrlLocater.getExecutableURL(self._session, "CLGlobalFeatures",
                                                      self._actionConfig)
            targetImageURL = artefactHelper.getArtefactProperty(self._targetImage, artefactProps.URL)
            segmentedMaskURL = artefactHelper.getArtefactProperty(self._segmentedMask, artefactProps.URL)
            
            content = '"' + execURL + '"'
            content += ' -i "' + targetImageURL + '"'
            content +=  ' -m "' + segmentedMaskURL + '"'
            content += ' -o "' + resultPath + '"'
            content += ' -header'
            if self._features == 'all':
                content += ' -fo -ivoh -loci -vol -volden -cooc2 -ngld -rl -id -ngtd'
            else:
                for feature in self._features:
                    content += ' -{}'.format(feature)
            if self._resampling is not None:
                content += ' -fi {}'.format(self._resampling)
                content += ' -rm'
        
        except:
            logger.error("Error for getExecutable.")
            raise
        
        return content


class FeatureExtractionBatchAction(BatchActionBase):
    '''Action for batch processing of the CLGlobalImageFeatures.'''
    
    def __init__(self,  targetSelector, maskSelector, same_tp=True, features='all', resampling=None,
                 maskLinker = CaseLinker(), actionTag = "CLGlobalFeatures", alwaysDo = False,
                 session = None, additionalActionProps = None, scheduler = SimpleScheduler(), **singleActionParameters):
      
        BatchActionBase.__init__(self, actionTag, alwaysDo, scheduler, session, additionalActionProps)
        
        self._targetImages = targetSelector.getSelection(self._session.artefacts)
        
        self._segmentedMasks = maskSelector.getSelection(self._session.artefacts)
        
        self._maskLinker = maskLinker
        self._singleActionParameters = singleActionParameters
        self._features = features
        self._resampling = resampling
        self._same_tp = same_tp
        
    def _generateActions(self):
        resultSelector = TypeSelector(artefactProps.TYPE_VALUE_RESULT)
        
        targets = self.ensureRelevantArtefacts(self._targetImages, resultSelector,
                                               "CLGlobalFeatures targets")
        masks = self.ensureRelevantArtefacts(self._segmentedMasks, resultSelector,
                                             "CLGlobalFeatures masks")
        features = self._features
        resampling = self._resampling
        same_tp = self._same_tp
        
        global logger
        
        actions = list()
        
        for (pos, target) in enumerate(targets):
            linkedMasks = self._maskLinker.getLinkedSelection(pos, targets, masks)
            
            for lm in linkedMasks:
                if lm['timePoint'] == target['timePoint'] and same_tp:
                    action = FeatureExtractionAction(target, lm, features=features, resampling=resampling,
                                                     actionTag=self._actionTag, alwaysDo=self._alwaysDo,
                                                     session=self._session,
                                                     additionalActionProps=self._additionalActionProps,
                                                     **self._singleActionParameters)
                    actions.append(action)
                elif not same_tp:
                    action = FeatureExtractionAction(target, lm, features=features, resampling=resampling,
                                                     actionTag=self._actionTag, alwaysDo=self._alwaysDo,
                                                     session=self._session,
                                                     additionalActionProps=self._additionalActionProps,
                                                     **self._singleActionParameters)
                    actions.append(action)
        
        return actions
