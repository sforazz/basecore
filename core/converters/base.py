from core.utils.filemanip import split_filename

class BaseConverter(object):
    
    def __init__(self, toConvert, clean=False):
        
        self.basedir, self.filename, _ = split_filename(self.toConvert)
        self.toConvert = toConvert
        self.clean = clean
    
    def convert(self):

        raise NotImplementedError