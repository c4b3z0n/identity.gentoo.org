# vim:fileencoding=utf8:et:ts=4:sw=4:sts=4

import base64, calendar, datetime, time

from django.utils import timezone

from openid.store.interface import OpenIDStore
from openid.association import Association
from openid.store import nonce

from . import models as db_models

class DjangoDBOpenIDStore(OpenIDStore):
    def storeAssociation(self, server_uri, assoc):
        issued_dt = datetime.datetime.utcfromtimestamp(assoc.issued)
        issued_dt = timezone.make_aware(issued_dt, timezone.utc)
        expire_delta = datetime.timedelta(seconds = assoc.lifetime)

        a = db_models.Association(
                server_uri = server_uri,
                handle = assoc.handle,
                secret = base64.b64encode(assoc.secret),
                issued = issued_dt,
                expires = issued_dt + expire_delta,
                assoc_type = assoc.assoc_type)
        a.save()

    def _db_getAssocs(self, server_uri, handle = None):
        objs = db_models.Association.objects
        objs = objs.filter(server_uri = server_uri)
        if handle is not None:
            objs = objs.filter(handle = handle)

        return objs

    def getAssociation(self, server_uri, handle = None):
        assert(server_uri is not None)

        objs = self._db_getAssocs(server_uri, handle)
        try:
            a = objs.latest('issued')
        except db_models.Association.DoesNotExist:
            return None

        # expired?
        if timezone.now() >= a.expires:
            # if latest is expired, all older are expired as well
            # so clean them all up
            objs.delete()
            return None

        return Association(
                a.handle,
                base64.b64decode(a.secret),
                calendar.timegm(a.issued.utctimetuple()),
                int((a.expires - a.issued).total_seconds()),
                a.assoc_type)

    def removeAssociation(self, server_uri, handle):
        assert(server_uri is not None)
        assert(handle is not None)

        objs = self._db_getAssocs(server_uri, handle)

        # determining whether something was deleted is a waste of time
        # and django doesn't give us explicit 'affected rows'
        return True

    def useNonce(self, server_uri, ts, salt):
        nonce_dt = datetime.datetime.utcfromtimestamp(ts)
        nonce_dt = timezone.make_aware(nonce_dt, timezone.utc)
        # copy-paste from python-openid's sqlstore
        if abs(nonce_dt - timezone.now()) > nonce.SKEW:
            return False

        objs = db_models.Nonce.objects
        n, created = objs.get_or_create(
                server_uri = server_uri,
                ts = nonce_dt,
                salt = salt)

        # if it was created, it is unique and everything's fine.
        # if we found one existing, it is duplicate and we return False.
        return created

    def cleanupNonces(self):
        skew_td = datetime.timedelta(seconds = nonce.SKEW)
        expire_dt = timezone.now() - skew_td

        db_models.Nonce.objects.filter(ts__lt = expire_dt).delete()
        return 0

    def cleanupAssociations(self):
        db_models.Association.objects.filter(
                expires__lt = timezone.now()).delete()
        return 0
