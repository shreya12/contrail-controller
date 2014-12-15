from snmp import SnmpSession
import copy, traceback, time, ConfigParser
from vnc_api.vnc_api import VncApi

class DeviceConfig(object):
    __pat = None

    def __init__(self, name, cfg={}, mibs=[], flow_export_source_ip=None):
        self._raw = cfg
        self.name = name
        self.mibs = mibs or SnmpSession.TABLES() #all
        self.flow_export_source_ip = flow_export_source_ip
        self.snmp_name = None

    def set_snmp_name(self, name):
        self.snmp_name = name

    def get_snmp_name(self):
        return self.snmp_name

    def set_mibs(self, mib):
        if mib in SnmpSession.TABLES() and mib not in self.mibs:
            self.mibs.append(mib)

    def get_mibs(self):
        return self.mibs

    def get_flow_export_source_ip(self):
        return self.flow_export_source_ip

    def snmp_cfg(self):
        cfg = copy.copy(self._raw)
        cfg['DestHost'] = self.name
        cfg['Version'] = int(cfg['Version'])
        return cfg

    @classmethod
    def _pat(self):
        if self.__pat is None:
           self.__pat = re.compile(', *| +')
        return self.__pat

    @staticmethod
    def _get_and_remove_key(data_dict, key, default=None):
        val = default
        if key in data_dict:
            val = data_dict[key]
            del data_dict[key]
        return val

    @classmethod
    def _mklist(self, s):
        if isinstance(s, str):
            return self._pat().split(s)
        return s

    @staticmethod
    def fom_file(filename):
        devices = []
        devcfg = ConfigParser.SafeConfigParser()
        devcfg.optionxform = str
        devcfg.read([filename])
        for dev in devcfg.sections():
            nd = dict(devcfg.items(dev))
            mibs = DeviceConfig._mklist(DeviceConfig._get_and_remove_key(nd,
                        'Mibs', []))
            flow_export_source_ip = DeviceConfig._get_and_remove_key(nd,
                    'FlowExportSourceIp')
            devices.append(DeviceConfig(dev, nd, mibs,
                        flow_export_source_ip))
        return devices

    @staticmethod
    def get_vnc(usr, passwd, tenant, ip, port):
        for rt in (5, 2, 7, 9, 16, 25):
            try:
                print usr, passwd, tenant, ip, port
                return VncApi(usr, passwd, tenant, ip, port)
            except Exception as e:
                traceback.print_exc()
                time.sleep(rt)
        raise e

    @staticmethod
    def fom_api_server(api_server, usr, passwd, tenant):
        devices = []
        srv = api_server.split(':')
        if len(srv) == 2:
            ip, port = srv[0], int(srv[1])
        else:
            ip, port = srv[0], 8082

        vnc = DeviceConfig.get_vnc(usr, passwd, tenant, ip, port)
        for x in vnc.physical_routers_list()['physical-routers']:
            pr = vnc.physical_router_read(id=x['uuid'])
            snmp = pr.get_physical_router_snmp_credentials()
            if snmp:
                nd = { 'Version': snmp.get_version() }
                if snmp.get_local_port():
                    nd['RemotePort'] = snmp.get_local_port()
                if snmp.get_retries():
                    nd['Retries'] = snmp.get_retries()
                if snmp.get_timeout():
                    nd['Timeout'] = snmp.get_timeout()
                if nd['Version'] in (1, 2):
                    nd['Community'] = snmp.get_v2_community()
                elif nd['Version'] == 3:
                    if snmp.get_v3_security_name():
                        nd['SecName'] = snmp.get_v3_security_name()
                    if snmp.get_v3_security_level():
                        nd['SecLevel'] = snmp.get_v3_security_level()
                    if snmp.get_v3_security_engine_id():
                        nd['SecEngineId'] = snmp.get_v3_security_engine_id()
                    if snmp.get_v3_context():
                        nd['Context'] = snmp.get_v3_context()
                    if snmp.get_v3_context_engine_id():
                        nd['ContextEngineId'] = snmp.get_v3_context_engine_id()
                    if snmp.get_v3_authentication_protocol():
                        nd['AuthProto'] = snmp.get_v3_authentication_protocol()
                    if snmp.get_v3_authentication_password():
                        nd['AuthPass'] = snmp.get_v3_authentication_password()
                    if snmp.get_v3_privacy_protocol():
                        nd['PrivProto'] = snmp.get_v3_privacy_protocol()
                    if snmp.get_v3_privacy_password():
                        nd['PrivProto'] = snmp.get_v3_privacy_password()
                devices.append(DeviceConfig(
                            pr.get_physical_router_management_ip(),
                            nd, [], pr.get_physical_router_dataplane_ip()))
        return devices