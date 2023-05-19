from datetime import datetime, timedelta

from python_graphql_client import GraphqlClient

GRAPH_QL_ENDPOINT = "https://api.oees-kraken.energy/v1/graphql/"
SOLAR_WALLET_LEDGER = "SOLAR_WALLET_LEDGER"
ELECTRICITY_LEDGER = "SPAIN_ELECTRICITY_LEDGER"


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

        client = GraphqlClient(endpoint=GRAPH_QL_ENDPOINT)
        response = await client.execute_async(mutation, variables)
        self._token = response["data"]["obtainKrakenToken"]["token"]

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
        client = GraphqlClient(endpoint=GRAPH_QL_ENDPOINT, headers=headers)
        response = await client.execute_async(query)

        return list(map(lambda a: a["number"], response["data"]["viewer"]["accounts"]))

    async def account(self, account: str):
        query = """
            query ($account: String!) {
              accountBillingInfo(accountNumber: $account) {
                ledgers {
                  ledgerType
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
        client = GraphqlClient(endpoint=GRAPH_QL_ENDPOINT, headers=headers)
        response = await client.execute_async(query, {"account": account})
        ledgers = response["data"]["accountBillingInfo"]["ledgers"]
        solar_wallet_ledger = None
        electricity_ledger = None
        for ledger in ledgers:
            if ledger["ledgerType"] == SOLAR_WALLET_LEDGER:
                solar_wallet_ledger = ledger
            elif ledger["ledgerType"] == ELECTRICITY_LEDGER:
                electricity_ledger = ledger
        if not electricity_ledger:
            raise Exception("Electricity ledger not found")
        invoice = electricity_ledger["statementsWithDetails"]["edges"][0]["node"]

        # Los timedelta son bastante chapuzas, habrá que arreglarlo
        data = {
            "solar_wallet": (float(solar_wallet_ledger["balance"]) / 100)
            if solar_wallet_ledger
            else 0,
            "last_invoice": {
                "amount": invoice["amount"] if invoice["amount"] else 0,
                "issued": datetime.fromisoformat(invoice["issuedDate"]).date(),
                "start": (
                    datetime.fromisoformat(invoice["consumptionStartDate"])
                    + timedelta(hours=2)
                ).date(),
                "end": (
                    datetime.fromisoformat(invoice["consumptionEndDate"])
                    - timedelta(seconds=1)
                ).date(),
            },
        }

        return data
