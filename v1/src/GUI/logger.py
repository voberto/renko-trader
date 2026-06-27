import os

class Logger():
    path = None

    def __init__(self, dict_config_arg: dict):
        self.params_update(dict_config_arg)
        self.logfile_create()

    def params_update(self, dict_config_arg: dict):
        self.path = dict_config_arg['logger']['path']

    def logfile_create(self):
        path_exists = os.path.isfile(self.path)
        if(path_exists is False):
            with open(self.path, "w") as logfile:
                logfile_line_first = "### ----- LOGFILE ----- ###\n"
                logfile.write(logfile_line_first)

    def logfile_append(self, line_arg):
        path_exists = os.path.isfile(self.path)
        if(path_exists is True):
            with open(self.path, "a") as logfile:
                line = f"{line_arg}\n"
                logfile.write(line)
