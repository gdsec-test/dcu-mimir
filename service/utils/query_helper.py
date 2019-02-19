from dcdatabase.mimir.mongo import MimirMongo


class QueryHelper:
    """
    This class works with dcdatabase to obtain DCU infraction data
    """

    def __init__(self, settings):
        self.mongo = MimirMongo(settings.DBURL, settings.DB, settings.COLLECTION)

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

    def count_infractions(self, infraction_data):
        """
        Provide infraction data and get a count of the number of infractions matching that data
        :param infraction_data:
        :return:
        """
        return self.mongo.get_infraction_count(infraction_data)
