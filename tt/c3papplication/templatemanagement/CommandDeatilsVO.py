class CommandDetails:
    def __init__(self,cmd_value,cmd_id,cmd_seq_id,cmd_template_id,cmd_master_fid,cmd_created_date,
                 cmd_command_created_by,cmd_checked):
        self.cmd_value = cmd_value
        self.cmd_id = cmd_id
        self.cmd_seq_id = cmd_seq_id
        self.cmd_template_id = cmd_template_id
        self.cmd_master_fid = cmd_master_fid
        self.cmd_created_date = cmd_created_date
        self.cmd_command_created_by = cmd_command_created_by
        self.cmd_checked = cmd_checked

    def __init__(self):
        pass

    def get_cmd_id(self):
        return self.cmd_id

    def get_cmd_seq_id(self):
        return self.cmd_seq_id

    def set_cmd_seq_id(self,cmd_seq_id):
        self.cmd_seq_id = cmd_seq_id

    def get_cmd_value(self):
        return self.cmd_value

    def set_cmd_value(self,cmd_value):
        self.cmd_value = cmd_value

    def get_cmd_template_id(self):
        return self.cmd_template_id

    def set_cmd_template_id(self,cmd_template_id):
        self.cmd_template_id = cmd_template_id

    def get_cmd_master_fid(self):
        return self.cmd_master_fid

    def set_cmd_master_fid(self,cmd_master_fid):
        self.cmd_master_fid = cmd_master_fid

    def get_cmd_created_date(self):
        return self.cmd_created_date

    def set_cmd_created_date(self,cmd_created_date):
        self.cmd_created_date = cmd_created_date

    def get_cmd_command_created_by(self):
        return self.cmd_created_date

    def set_cmd_command_created_by(self,cmd_command_created_by):
        self.cmd_command_created_by = cmd_command_created_by

    def get_cmd_checked(self):
        return self.cmd_checked

    def set_cmd_checked(self,cmd_checked):
        self.cmd_checked = cmd_checked


    