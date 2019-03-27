from dcdatabase.mimir.mongo import MimirMongo


class QueryHelper:
    """
    This class works with dcdatabase to obtain DCU infraction data
    """
    def __init__(self, settings):
        self.mongo = MimirMongo(settings.DBURL, settings.DB, settings.COLLECTION)

    def insert_infraction(self, data):
        """
        :param data: Dictionary containing infraction model k/v pairs for insertion into mimir collection
        :return: event id of new infraction or existing infraction if same data created within 24 hours
        """
        duplicate_infraction = self.mongo.get_duplicate_infractions_before_add(**data)
        if duplicate_infraction:
            return duplicate_infraction, True
        else:
            return self.mongo.add_infraction(data), False

    def get_infraction_from_id(self, infractionId):
        """
        Obtain infraction data upon submission of an Infraction ID
        :param infractionId: ObjectId of request as string
        :return:
        """
        query = self.mongo.get_infraction(infractionId)
        if query:
            query['infractionId'] = str(query.pop('_id'))
            query['createdDate'] = str(query.get('createdDate'))
        return query

    def get_infractions(self, data):
        """
        Obtain list of infractions matching provided data dict.
            Data dict must have at least one of sourceDomainOrIp, hostingGuid, or shopperId.
            Optional query params to further limit search results are:
            infractionType: (INTENTIONALLY_MALICIOUS, SUSPENDED, CUSTOMER_WARNING, and CONTENT_REMOVED)
            startDate: string YYYY-MM-DD Specify date from which infractions are retrieved. Default 6 months prior to current date.
            endDate: string YYYY-MM-DD Specify date up to which infractions are retrieved. Default to current date.
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
