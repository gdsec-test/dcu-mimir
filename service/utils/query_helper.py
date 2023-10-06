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
    mongo = None

    def __init__(self, settings):
        self.mongo = MimirMongo(settings.DBURL, settings.DB, settings.COLLECTION)

    @staticmethod
    def _create_composite_key(data: dict) -> str:
        """
        Creates a composite key.
        :param data: infraction dictionary
        :return: string composite key
        """
        abuse_type = data.get('abuseType', '')
        domain = data.get('sourceSubDomain', data.get('sourceDomainOrIp', ''))
        domain_id = data.get('domainId', '')
        hosting_guid = data.get('hostingGuid', '')
        infraction_type = data.get('infractionType', '')
        shopper_id = data.get('shopperId', '')

        if hosting_guid:
            return ','.join([domain, shopper_id, hosting_guid, infraction_type, abuse_type])
        elif domain_id:
            return ','.join([domain, shopper_id, domain_id, infraction_type, abuse_type])
        else:
            return ','.join([domain, shopper_id, '', infraction_type, abuse_type])

    def _check_duplicate_and_persist(self, data: dict) -> tuple:
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

    def insert_infraction(self, data: dict) -> tuple:
        """
        :param data: Dictionary containing infraction model k/v pairs for insertion into mimir collection
        :return: event id of new infraction or existing infraction if same data created within 24 hours
        """
        with Lock().lock.create_lock(QueryHelper._create_composite_key(data), ttl=self.TTL):
            return self._check_duplicate_and_persist(data)

    def insert_non_infraction(self, data: dict) -> str:
        """
        :param data: Dictionary containing non infraction model k/v pairs for insertion into mimir collection
        :return: record id of new record
        """
        return self.mongo.add_non_infraction(data)

    def get_infraction_from_id(self, infraction_id: str) -> dict:
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

    def get_history(self, history_query: dict) -> list:
        """
        Obtain list of infractions/non-infractions matching provided data dict.
            Data dict must have at least one of sourceDomainOrIp, hostingGuid, or shopperId.
            Optional query params to further limit search results are:
            infractionType: (For full list of supported infraction types please refer to service.rest.api)
            startDate: string YYYY-MM-DD Specify date from which infractions are retrieved.
                       Default 6 months prior to current date.
            endDate: string YYYY-MM-DD Specify date up to which infractions are retrieved.
                     Default to current date.
        :param history_query: Dict of infraction fields and values
        :return: List of historical infractions and non-infractions
        """

        history = self.mongo.get_history(history_query)

        for historical_entry in history:
            historical_entry['infractionId'] = str(historical_entry.pop('_id'))
            historical_entry['createdDate'] = str(historical_entry.get('createdDate'))

        return history

    def count_infractions(self, infraction_data: dict) -> int:
        """
        Provide infraction data and get a count of the number of infractions matching that data
        :param infraction_data:
        :return:
        """
        return self.mongo.get_infraction_count(infraction_data)
