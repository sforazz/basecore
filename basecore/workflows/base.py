from basecore.database.datahandler import BaseDataHandler


class BaseWorkflow(BaseDataHandler):

    def datasource(self):

        self.database()
        if self.xnat_source:
            self.xnat_scan_ids = list(set([self.field_template[it].split('/')[-1].split('.')[0]
                                      for it in self.field_template]))
            self.xnat_datasource()
        self.data_source = self.create_datasource()

    def workflow(self):
        raise NotImplementedError
    
    def runner(self):

        workflow = self.workflow()
        workflow.run()
        if self.xnat_sink:
            self.xnat_datasink()
    