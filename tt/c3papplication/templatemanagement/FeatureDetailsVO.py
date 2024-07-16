class FeatureDetails:
    def __init__(self,f_rowid,f_id,f_name,f_replicationind,f_version,f_vendor,f_family,
                     f_os,f_osversion,f_networkfun,f_region,f_created_by,f_created_date,f_parent_id):

        self.f_id = f_id
        self.f_row_id = f_rowid
        self.f_name = f_name
        self.f_replicationind = f_replicationind
        self.f_vendor = f_vendor
        self.f_version = f_version
        self.f_family = f_family
        self.f_os = f_os
        self.f_osversion = f_osversion
        self.f_networkfun = f_networkfun
        self.f_region = f_region
        self.f_created_by = f_created_by
        self.f_created_date = f_created_date
        self.f_parent_id = f_parent_id


    def __init__(self):
        pass

    def get_f_row_id(self):
        return self.f_row_id

    def set_f_row_id(self,f_row_id):
        self.f_row_id=f_row_id

    def get_f_id(self):
        return self.f_id

    def set_f_id(self,f_id):
        self.f_id=f_id

    def get_f_name(self):
        return self.f_name

    def set_f_name(self, f_name):
        self.f_name = f_name

    def get_f_replicationind(self):
        return self.f_replicationind

    def set_f_replicationind(self, f_replicationind):
        self.f_replicationind = f_replicationind

    def get_f_version(self):
        return self.f_version

    def set_f_version(self, f_version):
        self.f_version = f_version

    def get_f_vendor(self):
        return self.f_vendor

    def set_f_vendor(self, f_vendor):
        self.f_vendor = f_vendor

    def get_f_family(self):
        return self.f_family

    def set_f_family(self, f_family):
        self.f_family = f_family

    def get_f_os(self):
        return self.f_os

    def set_f_os(self, f_os):
        self.f_os = f_os

    def get_f_osversion(self):
        return self.f_osversion

    def set_f_osversion(self, f_osversion):
        self.f_osversion = f_osversion


    def get_f_networkfun(self):
        return self.f_networkfun

    def set_f_networkfun(self, f_networkfun):
        self.f_networkfun = f_networkfun

    def get_f_region(self):
        return self.f_region

    def set_f_region(self, f_region):
        self.f_region = f_region

    def get_f_created_date(self):
        return self.f_created_date

    def set_f_created_date(self, f_created_date):
        self.f_created_date = f_created_date

    def get_f_created_by(self):
        return self.f_created_by

    def set_f_created_by(self, f_created_by):
        self.f_created_by = f_created_by

    def get_f_parent_id(self):
        return self.f_parent_id

    def set_f_parent_id(self, f_parent_id):
        self.f_parent_id = f_parent_id