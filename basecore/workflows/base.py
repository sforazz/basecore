from basecore.database.base import BaseDatabase

class BaseWorkflow(BaseDatabase):

    def datasource(self):

        self.database()
        if self.xnat_source or self.cluster_source:
            self.input_needed = list(
                set([self.field_template[it].split('/')[-1].split('.')[0]
                     for it in self.field_template]))
            if self.xnat_source:
                self.xnat_datasource()
            elif self.cluster_source:
                self.cluster_datasource()

        self.data_source = self.create_datasource()

    def workflow(self):
        raise NotImplementedError
    
    def workflow_setup(self):
        return self.workflow()

    def runner(self, cores=0):

        workflow = self.workflow_setup()

        if cores == 0:
            print('Workflow will run linearly')
            workflow.run()
        else:
            print('Workflow will run in parallel using {} cores'.format(cores))
            workflow.run(plugin='MultiProc', plugin_args={'n_procs' : cores})

        if self.cluster_sink:
            self.cluster_datasink()
        if self.xnat_sink:
            self.xnat_datasink()
    