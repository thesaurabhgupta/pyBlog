class TopologyEntityET(object):
    def __init__(self,t_topology_type,s_device_id,s_hostname,s_mgmtip,s_interface,s_interface_ip,
                 s_topo_type_name,s_topo_type_id,t_hostname,t_device_id,t_mgmtip,t_neighbor, t_topo_type_name,t_topo_type_id,tp_created_by,tp_created_date):
        self.t_topology_type = t_topology_type
        self.s_device_id = s_device_id
        self.s_hostname = s_hostname
        self.s_mgmtip = s_mgmtip
        self.s_interface = s_interface
        self.s_interface_ip = s_interface_ip
        self.s_topo_type_name = s_topo_type_name
        self.s_topo_type_id = s_topo_type_id
        self.t_hostname = t_hostname
        self.t_device_id = t_device_id
        self.t_mgmtip = t_mgmtip
        self.t_neighbor = t_neighbor
        self.t_topo_type_name = t_topo_type_name
        self.t_topo_type_id = t_topo_type_id
        self.tp_created_by = tp_created_by
        self.tp_created_date = tp_created_date

