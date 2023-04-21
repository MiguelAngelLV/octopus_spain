from python_graphql_client import GraphqlClient
from datetime import timedelta, datetime
import octopus_spain.const as octopus_spain_constants


class OctopusSpain:

    def __init__(self, email, password):
        self._email = email
        self._password = password
        self._token = None

    async def login(self):
        mutation = """
           mutation obtainKrakenToken($input: ObtainJSONWebTokenInput!) {
              obtainKrakenToken(input: $input) {
                token
              }
            }
        """
        variables = {"input": {"email": self._email, "password": self._password}}

        client = GraphqlClient(endpoint=octopus_spain_constants.GRAPH_QL_ENDPOINT)
        response = await client.execute_async(mutation, variables)
        self._token = response['data']['obtainKrakenToken']['token']

    async def accounts(self):
        query = """
             query getAccountNames{
                viewer {
                    accounts {
                        ... on Account {
                            number
                        }
                    }
                }
            }
            """

        headers = {"authorization": self._token}
        client = GraphqlClient(endpoint=octopus_spain_constants.GRAPH_QL_ENDPOINT, headers=headers)
        response = await client.execute_async(query)

        return list(map(lambda a: a['number'], response['data']['getAccountNames']['viewer']['accounts']))

    async def account(self, account: str):
        query = """
            query($account: String!) {
                accountBillingInfo(accountNumber: $account) {
                    ledgers {
                        statementsWithDetails(first: 1) {
                            edges {
                                node {
                                    amount
                                    consumptionStartDate
                                    consumptionEndDate
                                    issuedDate
                                    }
                                }
                            }
                            balance
                    }
                }
            }
        """
        headers = {"authorization": self._token}
        client = GraphqlClient(endpoint=octopus_spain_constants.GRAPH_QL_ENDPOINT, headers=headers)
        response = await client.execute_async(query, {"account": account})
        ledger = response['data']['accountBillingInfo']['ledgers'][0]
        invoice = ledger['statementsWithDetails']['edges'][0]['node']

        # Los timedelta son bastante chapuzas, habrá que arreglarlo
        data = {
            "solar_wallet": float(ledger['balance']) / 100,
            "last_invoice": {
                "amount": invoice['amount'],
                "issued": datetime.fromisoformat(invoice['issuedDate']).date(),
                "start": (datetime.fromisoformat(invoice['consumptionStartDate']) + timedelta(hours=2)).date(),
                "end": (datetime.fromisoformat(invoice['consumptionEndDate']) - timedelta(seconds=1)).date(),
            }
        }

        return data
