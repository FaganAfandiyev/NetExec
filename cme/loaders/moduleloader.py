#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import importlib
import os
import sys

import cme
from cme.context import Context
from cme.logger import CMEAdapter
from cme.paths import CME_PATH


class ModuleLoader:
    def __init__(self, args, db, logger):
        self.args = args
        self.db = db
        self.logger = logger

    def module_is_sane(self, module, module_path):
        """
        Check if a module has the proper attributes
        """
        module_error = False
        if not hasattr(module, "name"):
            self.logger.error(f"{module_path} missing the name variable")
            module_error = True
        elif not hasattr(module, "description"):
            self.logger.error(f"{module_path} missing the description variable")
            module_error = True
        elif not hasattr(module, "supported_protocols"):
            self.logger.error(f"{module_path} missing the supported_protocols variable")
            module_error = True
        elif not hasattr(module, "opsec_safe"):
            self.logger.error(f"{module_path} missing the opsec_safe variable")
            module_error = True
        elif not hasattr(module, "multiple_hosts"):
            self.logger.error(f"{module_path} missing the multiple_hosts variable")
            module_error = True
        elif not hasattr(module, "options"):
            self.logger.error(f"{module_path} missing the options function")
            module_error = True
        elif not hasattr(module, "on_login") and not (module, "on_admin_login"):
            self.logger.error(f"{module_path} missing the on_login/on_admin_login function(s)")
            module_error = True
        # elif not hasattr(module, 'chain_support'):
        #    self.logger.error('{} missing the chain_support variable'.format(module_path))
        #    module_error = True

        if module_error:
            return False
        return True

    def load_module(self, module_path):
        """
        Load a module, initializing it and checking that it has the proper attributes
        """
        try:
            spec = importlib.util.spec_from_file_location("CMEModule", module_path)
            module = spec.loader.load_module().CMEModule()

            if self.module_is_sane(module, module_path):
                return module
        except Exception as e:
            self.logger.error(f"Failed loading module at {module_path}: {e}")
        return None

    def init_module(self, module_path):
        """
        Initialize a module for execution
        """
        module = None
        module = self.load_module(module_path)

        if module:
            self.logger.debug(f"Supported protocols: {module.supported_protocols}")
            self.logger.debug(f"Protocol: {self.args.protocol}")
            if self.args.protocol in module.supported_protocols:
                try:
                    module_logger = CMEAdapter(extra={'module_name': module.name.upper()})
                except Exception as e:
                    self.logger.error(f"Error loading CMEAdaptor for module {module.name.upper()}: {e}")
                context = Context(self.db, module_logger, self.args)
                module_options = {}

                for option in self.args.module_options:
                    key, value = option.split('=', 1)
                    module_options[str(key).upper()] = value

                module.options(context, module_options)
                return module
            else:
                self.logger.error(f"Module {module.name.upper()} is not supported for protocol {self.args.protocol}")
                sys.exit(1)

    def get_module_info(self, module_path):
        """
        Get the path, description, and options from a module
        """
        try:
            spec = importlib.util.spec_from_file_location("CMEModule", module_path)
            module_spec = spec.loader.load_module().CMEModule

            module = {
                f"{module_spec.name.lower()}":
                    {
                        "path": module_path,
                        "description": module_spec.description,
                        "options": module_spec.options.__doc__
                    }
            }
            if self.module_is_sane(module_spec, module_path):
                return module
        except Exception as e:
            self.logger.error(f"Failed loading module at {module_path}: {e}")
        return None

    def list_modules(self):
        """
        List modules without initializing them
        """
        modules = {}
        modules_paths = [os.path.join(os.path.dirname(cme.__file__), 'modules'), os.path.join(CME_PATH, 'modules')]

        for path in modules_paths:
            for module in os.listdir(path):
                if module[-3:] == '.py' and module != 'example_module.py':
                    module_path = os.path.join(path, module)
                    module_data = self.get_module_info(module_path)
                    modules.update(module_data)
        return modules
