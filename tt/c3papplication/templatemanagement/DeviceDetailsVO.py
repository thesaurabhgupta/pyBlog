class DeviceDetails:
    def __init__(self,vendor,family,os,osversion,region,networktype):
        self.vendor = vendor
        self.family = family
        self.os = os
        self.osversion = osversion
        self.region = region
        self.networkType = networktype

    def __init__(self):
        pass

    def get_vendor(self):
        return self.vendor

    def set_vendor(self,vendor):
        self.vendor = vendor

    def get_family(self):
        return self.family

    def set_family(self,family):
        self.family = family

    def get_os(self):
        return self.os

    def set_os(self,os):
        self.os = os

    def get_osversion(self):
        return self.osversion

    def set_osversion(self,osversion):
        self.osversion = osversion

    def get_region(self):
        return self.region

    def set_region(self,region):
        self.region = region

    def get_networktype(self):
        return self.networktype

    def set_networktype(self,networktype):
        self.networktype = networktype

