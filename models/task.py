class Task:

   def __init__(self,task_id,capability, description, context=None,depends_on=None):
        
        self.task_id = task_id
        self.capability = capability
        self.description = description
        self.context = context or {}
        self.depends_on=depends_on or []