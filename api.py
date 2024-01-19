import httpx
import json
import asyncio
import re
import logging
import http.cookiejar as cookiejar

gql_url = "https://gaming.amazon.com/graphql"

logging.getLogger("httpx").setLevel(logging.WARNING)
log = logging.getLogger()

RED = '\033[91m'
BLUE = '\033[94m'
CYAN = '\033[96m'
MAGENTA = '\033[95m'
GREEN = '\033[92m'
RESET = '\033[0m'

list_payload = {
    "operationName": "OffersContext_Offers_And_Items",
    "variables": {"pageSize": 999},
    "extensions": {},
    "query": """
      query OffersContext_Offers_And_Items($dateOverride: Time, $pageSize: Int) {
        inGameLoot: items(collectionType: LOOT, dateOverride: $dateOverride, pageSize: $pageSize) {
          items {
            ...Item
            __typename
          }
          __typename
        }
        expiring: items(collectionType: EXPIRING, dateOverride: $dateOverride) {
          items {
            ...Item
            __typename
          }
          __typename
        }
        popular: items(collectionType: FEATURED, dateOverride: $dateOverride) {
          items {
            ...Item
            __typename
          }
          __typename
        }
        games: items(collectionType: FREE_GAMES, dateOverride: $dateOverride, pageSize: $pageSize) {
          items {
            ...Item
            __typename
          }
          __typename
        }
      }
      
      fragment Item on Item {
        id
        isFGWP
        isDirectEntitlement
        isRetailLinkItem
        grantsCode
        priority
        pixels {
          ...Pixel
          __typename
        }
        assets {
          id
          title
          externalClaimLink
          cardMedia {
            defaultMedia {
              src1x
              src2x
              type
              __typename
            }
            __typename
          }
          __typename
        }
        offers {
          id
          startTime
          endTime
          offerSelfConnection {
            eligibility {
              offerState
              isClaimed
              conflictingClaimAccount {
                obfuscatedEmail
                __typename
              }
              __typename
            }
            __typename
          }
          __typename
        }
        game {
          id
          isActiveAndVisible
          assets {
            title
            __typename
          }
          __typename
        }
        __typename
      }
      
      fragment Pixel on Pixel {
        type
        pixel
        __typename
      }
    """,
}

user_payload = {
    "operationName": "Entry_Points_User",
    "extensions": {},
    "variables": {"weblabTreatmentList": [
      "PG_326549",
      "PG_TO_THE_MOON_372912",
      "PG_CHEESY_GORDITA_439922",
      "PG_CLAIM_CONSOLIDATION_MILESTONE_3_582648",
      "PG_SCRAMBLED_EGGS_446919",
      "PG_PCONS_V1_541640",
      "PG_ZAPDOS_555379",
      "HUMBLE_HYLIAN_713107",
      "PG_BANANA_STAND_607245",
      "PG_INTEG_BANANAPHONE_803595",
      "PG_CARBONITE_PRIME_BENEFITS_BANNER_722856",
      "PG_CARBONITE_747927",
      "PG_KEYBEARERS_HALLOWEEN_PAGE_778298",
      "PG_OBSIDIAN_794242",
      "PG_THANK_YOU_RECS_TWO_796685",
      "PG_EU_COOKIE_BANNER_COMPLIANCE_803731",
      "PG_CARBONITE_REMAINING_FTUE_GLOBAL_LAUNCH_825106",
      "PG_KEEP_IT_CASUAL_818343",
      "IMPROVED_DISCOVERY_736602",
      "PG_OCI_765028"
    ]},
    "query": """
        fragment EntryPointsUser_TwitchAccount on TwitchAccount {
            tuid
            __typename
        }

        fragment EntryPointsUser_CurrentUser on CurrentUser {
            id
            isTwitchPrime
            isAmazonPrime
            isSignedIn
            firstName
            twitchAccounts {
                ...EntryPointsUser_TwitchAccount
                __typename
            }
            __typename
        }

        fragment EntryPointsUser_Weblab on Weblab {
            name
            treatment
            __typename
        }

        fragment EntryPointsUser_PrimeMarketplace on PrimeMarketplace {
            id
            marketplaceCode
            __typename
        }

        fragment EntryPointsUser_CountryOfResidence on Country {
            countryCode
            primeGamingEligibility
            __typename
        }

        fragment EntryPointsUser_GeographicalCountry on Country {
            countryCode
            primeGamingEligibility
            __typename
        }

        query Entry_Points_User($weblabTreatmentList: [String!]!) {
            currentUser {
                ...EntryPointsUser_CurrentUser
                __typename
            }
            primeMarketplace {
                ...EntryPointsUser_PrimeMarketplace
                __typename
            }
            countryOfResidence {
                ...EntryPointsUser_CountryOfResidence
                __typename
            }
            geographicalCountry {
                ...EntryPointsUser_GeographicalCountry
                __typename
            }
            weblabTreatmentList(weblabNameList: $weblabTreatmentList) {
                ...EntryPointsUser_Weblab
                __typename
            }
        }
    """,
}

class AuthException(Exception):
    pass

async def authenticate(client: httpx.AsyncClient, headers: dict) -> True:
    try:
        user_response = await client.post(gql_url, headers=headers, data=json.dumps(user_payload))
        user_response.raise_for_status()

        user_data = user_response.json()["data"]["currentUser"]
        if not user_data["isSignedIn"]:
            raise AuthException("Authentication: Not signed in. (Please recreate the cookie.txt file)")
        elif not user_data["isAmazonPrime"]:
            raise AuthException("Authentication: Not a valid Amazon Prime account.")
        elif not user_data["isTwitchPrime"]:
            raise AuthException("Authentication: Not a valid Twitch Prime account.")

        log.info(f"Authentication: Success! User: {user_data['firstName']}")

    except Exception as e:
        log.error(f"Authentication error: {e}")
        raise

async def offers_list(client: httpx.AsyncClient, headers: dict):
    try:
        list_response = await client.post(gql_url, headers=headers, data=json.dumps(list_payload))
        list_response.raise_for_status()
        
        loot_items = list_response.json()["data"]["inGameLoot"]["items"]
        games_items = list_response.json()["data"]["games"]["items"]

        async def process_items(items_list, item_type):
            claimed_count = 0
            unclaimed_count = 0
            can_claim = []

            for item in items_list:
                eligibility = item["offers"][0]["offerSelfConnection"]["eligibility"]
                is_claimed = eligibility.get("isClaimed", False)

                if is_claimed:
                    log.info(f"{BLUE}{item['game']['assets']['title']} - {item['assets']['title']} - {item_type}: Already collected.{RESET}")
                    claimed_count += 1
                else:
                    log.info(f"{CYAN}{item['game']['assets']['title']} - {item['assets']['title']} - {item_type}: Trying to claim.{RESET}")
                    unclaimed_count += 1
                    can_claim.append(item)

            log.info(f"{MAGENTA}Number of {item_type}: {len(items_list)}{RESET}")
            log.info(f"{MAGENTA}Claimed: {claimed_count}{RESET}")
            log.info(f"{MAGENTA}Unclaimed: {unclaimed_count}{RESET}\n")

            return can_claim
        
        loot_can_claim = await process_items(loot_items, "Loot")
        games_can_claim = await process_items(games_items, "Game")

        return loot_can_claim + games_can_claim

    except Exception as e:
        log.error(f"Offer list error: {e}")
        raise

async def get_offer(item: dict, client: httpx.AsyncClient, headers: dict):
    offer_payload = {
        "operationName": "ItemV2Context",
        "variables": {
            "itemId": item["assets"]["id"],
            "stringDebug": False,
            "redirectUrl": item["assets"]["externalClaimLink"]
        },
        "extensions": {},
        "query": "query ItemV2Context($itemId: String!, $dateOverride: Time, $stringDebug: Boolean, $previewId: String, $redirectUrl: String) {\n  itemV2(itemId: $itemId, dateOverride: $dateOverride, stringDebug: $stringDebug, previewId: $previewId) {\n    item {\n      ...ItemPageItem\n      __typename\n    }\n    error {\n      code\n      __typename\n    }\n    __typename\n  }\n}\n\nfragment ItemMediaAsset on MediaAsset {\n  src1x\n  src2x\n  type\n  __typename\n}\n\nfragment Item_Media on Media {\n  alt\n  description\n  defaultMedia {\n    ...ItemMediaAsset\n    __typename\n  }\n  desktop {\n    ...ItemMediaAsset\n    __typename\n  }\n  tablet {\n    ...ItemMediaAsset\n    __typename\n  }\n  videoPlaceholderImage {\n    ...ItemMediaAsset\n    __typename\n  }\n  __typename\n}\n\nfragment ItemHeroAsset on MediaAsset {\n  src1x\n  src2x\n  type\n  __typename\n}\n\nfragment ItemContextHeroAssets on Media {\n  defaultMedia {\n    ...ItemHeroAsset\n    __typename\n  }\n  tablet {\n    ...ItemHeroAsset\n    __typename\n  }\n  desktop {\n    ...ItemHeroAsset\n    __typename\n  }\n  videoPlaceholderImage {\n    ...ItemHeroAsset\n    __typename\n  }\n  alt\n  __typename\n}\n\nfragment Item_Assets on ItemAssets {\n  additionalMedia {\n    ...Item_Media\n    __typename\n  }\n  claimInstructions\n  mobileClaimInstructions\n  claimVisualInstructions {\n    ...Item_Media\n    __typename\n  }\n  thumbnailImage {\n    ...Item_Media\n    __typename\n  }\n  externalClaimLink\n  faqList {\n    question\n    answer\n    __typename\n  }\n  heroMedia {\n    ...ItemContextHeroAssets\n    __typename\n  }\n  cardMedia {\n    ...Item_Media\n    __typename\n  }\n  id\n  itemDetails\n  longformDescription\n  platforms\n  platformsDisplay\n  shortformDescription\n  title\n  urlSlug\n  redemptionPlatforms\n  __typename\n}\n\nfragment Game on GameV2 {\n  id\n  accountLinkConfig(redirectUrl: $redirectUrl) {\n    accountType\n    linkingUrl\n    thirdPartyAccountManagementUrl\n    __typename\n  }\n  assets {\n    title\n    publisher\n    accountName\n    primaryDeveloper\n    otherDevelopers\n    longformDescription\n    genres\n    localizedGenres\n    gameModes\n    localizedGameModes\n    releaseDate\n    platformsDisplay\n    purchaseGameText\n    faqList {\n      question\n      answer\n      __typename\n    }\n    vendorIcon {\n      ...GameVendorIcon\n      __typename\n    }\n    ageRating {\n      ...Age_Rating\n      __typename\n    }\n    coverArt {\n      ...Item_Media\n      __typename\n    }\n    additionalMedia {\n      ...Item_Media\n      __typename\n    }\n    __typename\n  }\n  gameSelfConnection {\n    isSubscribedToNotifications\n    accountLink {\n      id\n      accountType\n      displayName\n      status\n      __typename\n    }\n    __typename\n  }\n  officialWebsite\n  thirdPartySupportPageUrl\n  isActiveAndVisible\n  __typename\n}\n\nfragment GameVendorIcon on Media {\n  alt\n  defaultMedia {\n    src1x\n    src2x\n    type\n    __typename\n  }\n  __typename\n}\n\nfragment Item_Offer on Offer {\n  id\n  startTime\n  endTime\n  legalInformation {\n    longLegal\n    shortLegal\n    __typename\n  }\n  offerSelfConnection {\n    eligibility {\n      ...Item_Offer_Eligibility\n      __typename\n    }\n    orderInformation {\n      ...Item_Offer_Order_Info\n      __typename\n    }\n    __typename\n  }\n  __typename\n}\n\nfragment Age_Rating on AgeRating {\n  rating\n  ratingDisplay\n  tags\n  ratingMediaAssetUrl\n  ratingLearnMoreUrl\n  ratingSystem\n  __typename\n}\n\nfragment Item_Alert on Alert {\n  id\n  type\n  button {\n    text\n    url\n    __typename\n  }\n  message\n  order\n  __typename\n}\n\nfragment Item_Pixel on Pixel {\n  type\n  pixel\n  __typename\n}\n\nfragment ItemPageItem on Item {\n  id\n  isDirectEntitlement\n  requiresLinkBeforeClaim\n  grantsCode\n  isDeepLink\n  isFGWP\n  redirectPath\n  portalEntityUrl\n  assets {\n    ...Item_Assets\n    __typename\n  }\n  game {\n    ...Game\n    __typename\n  }\n  offers {\n    ...Item_Offer\n    __typename\n  }\n  alertList {\n    ...Item_Alert\n    __typename\n  }\n  pixels {\n    ...Item_Pixel\n    __typename\n  }\n  __typename\n}\n\nfragment Item_Offer_Order_Info on OfferOrderInformation {\n  id\n  entitledAccountId\n  entitledAccountName\n  orderDate\n  claimCode\n  deepLinkUrl\n  orderState\n  __typename\n}\n\nfragment Item_Offer_Eligibility on OfferEligibility {\n  isClaimed\n  canClaim\n  claimTime\n  conflictingClaimAccount {\n    fullName\n    obfuscatedEmail\n    __typename\n  }\n  isPrimeGaming\n  missingRequiredAccountLink\n  gameAccountDisplayName\n  offerState\n  inRestrictedMarketplace\n  inRestrictedCountry\n  maxOrdersExceeded\n  __typename\n}\n",
    }
    
    try:
        offer_response = await client.post(gql_url, headers=headers, data=json.dumps(offer_payload))
        offer_response.raise_for_status()
        
        offer = offer_response.json()["data"]["itemV2"]["item"]
        
        if offer_response.json()["data"]["itemV2"]["error"] is not None:
            log.error(f"Error: {offer_response.json()['data']['itemV2']['error']}")
        
        return offer

    except Exception as e:
        log.error(f"Offer error: {e}")
        raise

async def claim_offer(item: dict, link: str, client: httpx.AsyncClient, headers: dict) -> True:
    eligibility = item["offers"][0]["offerSelfConnection"]["eligibility"]
    
    if not eligibility["isClaimed"]:
        if not eligibility["canClaim"] and eligibility["missingRequiredAccountLink"]:
            log.error(f"{RED}{item['game']['assets']['title']} - {item['assets']['title']}: Account link required. Link:{GREEN} {link}{RESET}")
            return
        
        log.info(f"Collecting {item['game']['assets']['title']} - {item['assets']['title']}")
        claim_payload = {
            "operationName": "placeOrdersDetailPage",
            "variables": {
                "input": {
                    "offerIds": item["offers"][0]["id"],
                    "attributionChannel": f'{{"eventId":"ItemDetailRootPage:{item["offers"][0]["id"]}","page":"ItemDetailPage"}}',
                }
            },
            "extensions": {},
            "query": """
                fragment Place_Orders_Payload_Order_Information on OfferOrderInformation {
                  catalogOfferId
                  claimCode
                  entitledAccountId
                  entitledAccountName
                  id
                  orderDate
                  orderState
                  __typename
                }
                
                mutation placeOrdersDetailPage($input: PlaceOrdersInput!) {
                  placeOrders(input: $input) {
                    error {
                      code
                      __typename
                    }
                    orderInformation {
                      ...Place_Orders_Payload_Order_Information
                      __typename
                    }
                    __typename
                  }
                }
            """,
        }

        claim_response = await client.post(gql_url, headers=headers, data=json.dumps(claim_payload))
        if claim_response.json()["data"]["placeOrders"]["error"] is not None:
            log.error(f"Error: {claim_response.json()['data']['placeOrders']['error']}")
        
        offer = await get_offer(item, client, headers)
        if offer.get("grantsCode") is True:
            await get_code(item, client, headers)

async def get_code(item: dict, client: httpx.AsyncClient, headers: dict) -> True:
    max_retries = 5
    retry_count = 0

    while retry_count < max_retries:
        if client.is_closed:
            client = httpx.AsyncClient()

        offer = await get_offer(item, client, headers)
        order_information = offer["offers"][0]["offerSelfConnection"]["orderInformation"]

        if order_information and order_information[0].get("claimCode"):
            write_to_file(offer)
            break

        retry_count += 1
        await asyncio.sleep(3)

    if retry_count == max_retries:
        log.error(f"{RED} Unable to retrieve the code after {max_retries} retries for {item['game']['assets']['title']} - {item['assets']['title']}{RESET}")

def write_to_file(item, separator_string=None):
    separator_string = separator_string or "========================\n========================"
    with open("./game_codes.txt", "a", encoding="utf-8") as f:
        claim_code = item["offers"][0]["offerSelfConnection"]["orderInformation"][0]["claimCode"]
        instructions = item["assets"]["claimInstructions"].replace('\\n', ' ')
        
        log.info(f"{item['game']['assets']['title']} - {item['assets']['title']} Saving Code: {claim_code}")
        
        f.write(
            f"{item['game']['assets']['title']} - {item['assets']['title']} Code: {claim_code}\n\n"
            f"{instructions}\n{separator_string}\n"
        )
        
async def filter_offers(client: httpx.AsyncClient, headers: dict, publishers: dict) -> True:
    offer_list = await offers_list(client, headers)

    for item in offer_list:
        offer = await get_offer(item, client, headers)
            
        if "game" in offer and "publisher" in offer["game"]["assets"]:
            publisher = offer["game"]["assets"]["publisher"]

            if "all" not in publishers and publisher not in publishers:
                continue
                
            await claim_offer(offer, item["assets"]["externalClaimLink"], client, headers)

async def primelooter(cookie_file, publisher_file):
    jar = cookiejar.MozillaCookieJar(cookie_file)
    jar.load()
    
    async with httpx.AsyncClient() as client:
        base_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/117.0",
        }

        json_headers = base_headers | {
            "Content-Type": "application/json",
        }
        
        for _c in jar:
            client.cookies.jar.set_cookie(_c)

        html_body = (await client.get("https://gaming.amazon.com/home", headers=base_headers)).text
        matches = re.findall(r"name='csrf-key' value='(.*)'", html_body)
        json_headers["csrf-token"] = matches[0]
        
        await authenticate(client, json_headers)
        await filter_offers(client, json_headers, publisher_file)
