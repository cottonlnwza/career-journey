import py_trees
from py_trees.common import Status, Access

class CheckCondition(py_trees.behaviour.Behaviour):
    def __init__(self, name="CheckCondition", 
                 blackboard_key_name="default", 
                 condtion_value=None):
        
        super(CheckCondition, self).__init__(name)

        self.condition_name = blackboard_key_name
        self.condtion_value = condtion_value

        # get value from blackboard
        self.blackboard = self.attach_blackboard_client(name=self.name)
        self.blackboard.register_key(key=blackboard_key_name, access=py_trees.common.Access.READ)

    def update(self):
        # check condition
        if self.condition_name == "default":
            self.logger.error("Condition name is not set. Please set condition_name to check.")
            return Status.FAILURE
        
        # get current value from blackboard
        current_value = getattr(self.blackboard, self.condition_name, None)

        # check if current value is None (not exist in blackboard)
        if current_value is None:
            self.logger.error(f"Condition '{self.condition_name}' does not exist in the blackboard.")
            return Status.FAILURE
        
        # compare current value with condition value
        if current_value == self.condtion_value:
            return Status.SUCCESS
        else:
            return Status.FAILURE
        
        

        
        
        