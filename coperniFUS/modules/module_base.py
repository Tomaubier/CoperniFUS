
class Module:
    """
    Base class for CoperniFUS Modules
    """

    _DEFAULT_PARAMS = {}

    def __init__(self, parent_viewer, module_id, **kwargs) -> None:
        self.parent_viewer = parent_viewer
        self._module_id = None
        self.module_id = module_id
    
    @property
    def module_id(self):
        if not isinstance(self._module_id, str):
            raise ValueError('Please make sure that self.module_id is defined in the __init__ of the module. module_id should be a string without any dot characters.')
        elif isinstance(self._module_id, str) and '.' in self._module_id:
            raise ValueError('Please make sure that self.module_id does not contain any dot characters.')
        else:
            return self._module_id
        
    @module_id.setter
    def module_id(self, value):
        if not isinstance(value, str):
            raise ValueError('Please make sure that self.module_id is defined in the __init__ of the module. module_id should be a string without any dot characters.')
        elif isinstance(value, str) and '.' in value:
            raise ValueError('Please make sure that self.module_id does not contain any dot characters.')
        else:
            self._module_id = value

    # --- cache wrapper for modules parameters ---

    def get_user_param(self, param_name, default_value=None, additional_identifiers=[]):
        """ Cache wrapper for modules parameters
        Get parameters by their name using `param_name`.
        If the requested parameter is not found in the cache, default values provided in the static attribute `_DEFAULT_PARAMS` will be returned.
        """
        if default_value is None and param_name in self._DEFAULT_PARAMS:
            default_value = self._DEFAULT_PARAMS[param_name]
        param_value = self.parent_viewer.cache.get_attr(
            [self.module_id, *additional_identifiers, param_name],
            default_value = default_value
        )
        return param_value

    def set_user_param(self, param_name, param_value, additional_identifiers=[]):
        self.parent_viewer.cache.set_attr(
            [self.module_id, *additional_identifiers, param_name],
            param_value
        )

    # --- Required module attributes ---
    
    def init_dock(self):
        """ Sets up a dock GUI for the module """
        pass

    def add_rendered_object(self):
        """ Called when adding module-specific elements to the 3D viewer """
        pass

    def update_rendered_object(self):
        """ Called for the update of module-specific elements already present in the 3D viewer """
        pass

    def delete_rendered_object(self):
        """ Called for the removal of module-specific elements from the 3D viewer """
        pass

    # @propertys
    # def status_bar_widget_list(self):
    #     return []