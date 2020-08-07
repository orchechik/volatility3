# This file is Copyright 2019 Volatility Foundation and licensed under the Volatility Software License 1.0
# which is available at https://www.volatilityfoundation.org/license/vsl-v1.0
#
import logging
from typing import List

from volatility.framework import constants, exceptions, renderers, interfaces
from volatility.framework.configuration import requirements
from volatility.framework.objects import utility
from volatility.plugins.windows import pslist
from ntpath import basename

vollog = logging.getLogger(__name__)


class Check_peb_spoof(interfaces.plugins.PluginInterface):
    """Lists Peb-masquerading spoofed processes."""

    @classmethod
    def get_requirements(cls) -> List[interfaces.configuration.RequirementInterface]:
        # Since we're calling the plugin, make sure we have the plugin's requirements
        return [
            requirements.TranslationLayerRequirement(name = 'primary',
                                                     description = 'Memory layer for the kernel',
                                                     architectures = ["Intel32", "Intel64"]),
            requirements.SymbolTableRequirement(name = "nt_symbols", description = "Windows kernel symbols"),
            requirements.PluginRequirement(name = 'pslist', plugin = pslist.PsList, version = (1, 0, 0)),
            requirements.ListRequirement(name = 'pid',
                                         element_type = int,
                                         description = "Process IDs to include (all other processes are excluded)",
                                         optional = True)
        ]

    def _generator(self, procs):

        for proc in procs:
            eprocess_process_name = utility.array_to_string(proc.ImageFileName)
            proc_id = "Unknown"
            try:
                proc_id = proc.UniqueProcessId
                proc_layer_name = proc.add_process_layer()
            except exceptions.InvalidAddressException as excp:
                vollog.debug("Process {}: invalid address {} in layer {}".format(proc_id, excp.invalid_address,
                                                                                 excp.layer_name))
                continue

            try:
                peb = self._context.object(self.config["nt_symbols"] + constants.BANG + "_PEB",
                                           layer_name = proc_layer_name,
                                           offset = proc.Peb)

                peb_process_name = basename(peb.ProcessParameters.ImagePathName.get_string())

                # Continue if peb.ProcessParameters.ImagePathName or _EPROCESS.ImageFileName are null or no equal.
                if not peb_process_name or not eprocess_process_name or peb_process_name == eprocess_process_name:
                    continue

            except exceptions.SwappedInvalidAddressException as exp:
                peb_process_name = "Required memory at {0:#x} is inaccessible (swapped)".format(exp.invalid_address)

            except exceptions.PagedInvalidAddressException as exp:
                peb_process_name = "Required memory at {0:#x} is not valid (process exited?)".format(exp.invalid_address)

            except exceptions.InvalidAddressException as exp:
                peb_process_name = "Required memory at {0:#x} is not valid (incomplete layer {1}?)".format(
                    exp.invalid_address, exp.layer_name)

            yield (0, (proc.UniqueProcessId, eprocess_process_name, peb_process_name))

    def run(self):
        filter_func = pslist.PsList.create_pid_filter(self.config.get('pid', None))

        return renderers.TreeGrid([("PID", int), ("Original Process name", str), ("Spoofed Process name", str)],
                                  self._generator(
                                      pslist.PsList.list_processes(context = self.context,
                                                                   layer_name = self.config['primary'],
                                                                   symbol_table = self.config['nt_symbols'],
                                                                   filter_func = filter_func)))
