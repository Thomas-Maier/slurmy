
import logging

log = logging.getLogger('slurmy')


def _get_property_overwrite_0(class_obj, prop_name):
    def overwrite(self):
        log.debug('Calling "{}" of class "{}"'.format(prop_name, self))
        self._parent.update = True
        getattr(super(class_name, self), prop_name)()

    return overwrite

def _get_property_overwrite_1(class_obj, prop_name):
    def overwrite(self, value):
        log.debug('Calling "{}" of class "{}" with value "{}"'.format(prop_name, self, value))
        self._parent.update = True
        getattr(super(class_obj, self), prop_name)(value)

    return overwrite

def _overwrite_properties(class_obj):
    ## Overwrite properties with no arguments
    for prop_name in class_obj._properties_0:
        setattr(class_obj, prop_name, _get_property_overwrite_0(class_obj, prop_name))
    ## Overwrite properties with one argument
    for prop_name in class_obj._properties_1:
        setattr(class_obj, prop_name, _get_property_overwrite_1(class_obj, prop_name))

class UpdateBase:
    def __init__(self, parent):
        self._parent = parent

class UpdateSet(UpdateBase, set):
    _properties_0 = ['clear']
    _properties_1 = ['add', 'pop', 'remove', 'update']
_overwrite_properties(UpdateSet)

class UpdateList(UpdateBase, list):
    _properties_0 = ['clear']
    _properties_1 = ['append', 'extend', 'insert', 'pop', 'remove']
_overwrite_properties(UpdateList)
