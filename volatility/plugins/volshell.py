import code
import inspect

from volatility.framework import renderers
from volatility.framework.configuration import requirements
from volatility.framework.interfaces import plugins


class Volshell(plugins.PluginInterface):
    """Shell environment to directly interact with a memory image"""

    @classmethod
    def get_requirements(cls):
        return [requirements.TranslationLayerRequirement(name = 'primary',
                                                         description = 'Kernel Address Space',
                                                         architectures = ["Intel32", "Intel64"])]

    def run(self, additional_locals = None):

        # Provide some OS-agnostic convenience elements for ease
        context = self.context
        config = self.config
        layer_name = self.config['primary']
        kvo = context.memory[layer_name].config.get('kernel_virtual_offset')
        members = lambda x: list(sorted(x.vol.members.keys()))

        # Determine locals
        curframe = inspect.currentframe()
        vars = curframe.f_globals.copy()
        vars.update(curframe.f_locals)
        if additional_locals is not None:
            vars.update(additional_locals)

        # Try to enable tab completion
        try:
            import readline
        except ImportError:
            pass
        else:
            import rlcompleter
            completer = rlcompleter.Completer(namespace = vars)
            readline.set_completer(completer.complete)
            readline.parse_and_bind("tab: complete")
            print("Readline imported successfully")

        # TODO: provide help, consider generic functions (pslist?) and/or providing windows/linux functions

        code.interact(local = vars)

        return renderers.TreeGrid([], lambda: [])
