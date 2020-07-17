from copy import deepcopy

from dcdatabase.mimir.mongo import MimirMongo

from service.utils.lock import Lock


class QueryHelper:
    """
    This class works with dcdatabase to obtain DCU infraction data
    """

    """
    The time to live (TTL) imposed on the lock key, so that it is automatically deleted if the
    TTL expires. The TTL value is in milliseconds.
    """
    TTL = 10000

    def __init__(self, settings):
        self.mongo = MimirMongo(settings.DBURL, settings.DB, settings.COLLECTION)

    @staticmethod
    def _create_composite_key(infraction):
        """
        Creates a composite key.
        :param infraction:
        :return composite key:
        """
        infraction_type = infraction.get('infractionType', '')
        domain = infraction.get('sourceDomainOrIp', '')
        shopper_id = infraction.get('shopperId', '')
        hosting_guid = infraction.get('hostingGuid', '')
        abuse_type = infraction.get('abuseType', '')
        domain_id = infraction.get('domainId', '')

        if hosting_guid:
            return ','.join([domain, shopper_id, hosting_guid, infraction_type, abuse_type])
        elif domain_id:
            return ','.join([domain, shopper_id, domain_id, infraction_type, abuse_type])
        else:
            return ','.join([domain, shopper_id, '', infraction_type, abuse_type])

    def _check_duplicate_and_persist(self, data):
        infraction_query = deepcopy(data)

        # Popping infractionType from the post request and replacing with a list of infractionTypes
        # as the get infractions requires an infractionTypes key.
        infraction_type = infraction_query.pop('infractionType', '')
        if infraction_type:
            infraction_query['infractionTypes'] = [infraction_type]

        # Popping abuseType from the post request and replacing with a list of abuseTypes
        # as the get infractions requires an abuseTypes key.
        abuse_type = infraction_query.pop('abuseType', '')
        if abuse_type:
            infraction_query['abuseTypes'] = [abuse_type]

        # Popping hostedStatus since its required to add an infraction, but will break the query when getting
        infraction_query.pop('hostedStatus', '')

        duplicate_infraction = self.mongo.get_duplicate_infractions_before_add(infraction_query)
        if duplicate_infraction:
            return duplicate_infraction, True
        else:
            return self.mongo.add_infraction(data), False

    def insert_infraction(self, data):
        """
        :param data: Dictionary containing infraction model k/v pairs for insertion into mimir collection
        :return: event id of new infraction or existing infraction if same data created within 24 hours
        """
        with Lock().lock.create_lock(QueryHelper._create_composite_key(data), ttl=self.TTL):
            return self._check_duplicate_and_persist(data)

    def get_infraction_from_id(self, infraction_id):
        """
        Obtain infraction data upon submission of an Infraction ID
        :param infraction_id: ObjectId of request as string
        :return:
        """
        query = self.mongo.get_infraction(infraction_id)
        if query:
            query['infractionId'] = str(query.pop('_id'))
            query['createdDate'] = str(query.get('createdDate'))
        return query

    def get_infractions(self, data):
        """
        Obtain list of infractions matching provided data dict.
            Data dict must have at least one of sourceDomainOrIp, hostingGuid, or shopperId.
            Optional query params to further limit search results are:
            infractionType: (For full list of supported infraction types please refer to service.rest.api)
            startDate: string YYYY-MM-DD Specify date from which infractions are retrieved.
                       Default 6 months prior to current date.
            endDate: string YYYY-MM-DD Specify date up to which infractions are retrieved.
                     Default to current date.
        :param data: Dict of infraction fields and values
        :return: List of infractions
        """

        infractions = self.mongo.get_infractions(data)

        for infraction in infractions:
            infraction['infractionId'] = str(infraction.pop('_id'))
            infraction['createdDate'] = str(infraction.get('createdDate'))

        return infractions

    def count_infractions(self, infraction_data):
        """
        Provide infraction data and get a count of the number of infractions matching that data
        :param infraction_data:
        :return:
        """
        return self.mongo.get_infraction_count(infraction_data)
