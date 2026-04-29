import requests
import config

api_key = config.WALGREENS_API_KEY
aff_id = config.WALGREENS_AFF_ID
app_ver = config.APP_VER
dev_inf = config.DEV_INF
product_group_id = config.WALGREENS_PRODUCT_GROUP_ID



def get_4x6_product_id():
    """
    Calls the Product Details endpoint to get the catalog and filters for the 4x6 print product.
    Returns the productId if found.
    """
    url = config.WALGREENS_PRODUCTS_URL
    payload = {
        "apiKey": api_key,
        "affId": aff_id,
        "productGroupId": product_group_id,
        "act": "getphotoprods",
        "appVer": app_ver,
        "devInf": dev_inf
    }
    headers = {"Content-Type": "application/json"}

    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()

    data = response.json()
    # Check if there is any error reported in the response.
    if data.get("err") or data.get("errDesc"):
        raise Exception(f"API error: {data.get('errDesc', data.get('err'))}")

    products = data.get("products", [])
    # Iterate over the products to find a 4x6 print.
    for product in products:
        product_size = product.get("productSize", "").lower()
        product_desc = product.get("productDesc", "").lower()
        if "4x6" in product_size or "4x6" in product_desc:
            return product.get("productId")

    raise Exception("No 4x6 product found in the catalog.")


def search_walgreens_stores(latitude, longitude, product_id, qty="1"):
    """
    Searches for nearby Walgreens photo stores.
    Returns a list of stores (the API response’s "photoStores" array).
    """
    url = config.WALGREENS_STORE_URL  # Use production URL if ready
    payload = {
        "apiKey": api_key,
        "affId": aff_id,
        "latitude": str(latitude),
        "longitude": str(longitude),
        "act": "photoStores",
        "appVer": app_ver,
        "devInf": dev_inf,
        "productDetails": [{
            "productId": product_id,
            "qty": qty
        }]
    }
    headers = {"Content-Type": "application/json"}
    response = requests.post(url, json=payload, headers=headers)

    if response.status_code != 200:
        raise Exception(f"Store search failed: {response.status_code}, {response.text}")

    result = response.json()
    if result.get("status") != "success":
        raise Exception(f"Store search error: {result.get('errDesc')}")

    # Return the list of photoStores (which includes details such as store number and promiseTime)
    return result.get("photoStores", [])


def submit_walgreens_order(first_name, last_name, phone, email, store_num, promise_time,
                           product_details, aff_notes="Passport photo", publisher_id=None):
    """
    Submits a photo order for local pickup.

    Returns the JSON response from the order submit endpoint.
    """
    url = config.WALGREENS_ORDER_URL  # Use production URL when ready
    payload = {
        "apiKey": api_key,
        "affId":  aff_id,
        "firstName": first_name,
        "lastName": last_name,
        "phone": phone,
        "email": email,
        "storeNum": store_num,
        "promiseTime": promise_time,
        "affNotes": aff_notes,
        "act": "submitphotoorder",
        "appVer": app_ver,
        "devInf": dev_inf,
        "productDetails": product_details
    }
    print("Walgreen payload: ", payload)
    if publisher_id:
        payload["publisherId"] = publisher_id

    headers = {"Content-Type": "application/json"}
    response = requests.post(url, json=payload, headers=headers)
    if response.status_code != 200:
        raise Exception(f"Order submission failed: {response.status_code}, {response.text}")

    result = response.json()
    print("Walgreens response: ", result)
    if result.get("status") != "success":
        raise Exception(f"Order submission error: {result.get('errDesc')}")

    return result


# Example usage (for testing purposes)
if __name__ == "__main__":
    try:
        product_id = get_4x6_product_id()
        print("Found 4x6 Product ID:", product_id)
        # You can now use product_id in subsequent API calls such as the store locator call.
    except Exception as e:
        print("Error:", str(e))

    try:
        # For the purposes of this example, we assume you have already converted the ZIP code to latitude and longitude.
        # You might use a geocoding service (like Google Geocoding API) to get these values.
        latitude = 38.257778  # Example: Los Angeles latitude
        longitude = -122.054169  # Example: Los Angeles longitude

        # Search for nearby Walgreens photo stores.
        stores = search_walgreens_stores(latitude, longitude, product_id)
        if not stores:
            print("No stores found.")
        else:
            # Pick the first store from the list.
            store = stores[0]
            print("Nearest store details:", store)
            store_num = store["photoStoreDetails"]["storeNum"]
            promise_time = store["photoStoreDetails"]["promiseTime"]
            print("promise_time: ", promise_time)


            # checking for closed stores.
            if promise_time == "01-01-3000 00:00 AM":
                display_pickup_time = "Within 48 hours"
            else:
                display_pickup_time = promise_time

            # Prepare the product details for the order.
            # Here, we assume a single product (with productId "0000001") and one image.
            # product_details = [{
            #     "productId": product_id,
            #     "imageDetails": [{
            #         "qty": "1",
            #         "url": "https://storage.cloud.google.com/passportphotos1/orders/composite_6_processed_cb5664aa-b21c-4813-9aa1-efa9e3d5b4c8.jpg?authuser=1"
            #         # Replace with your actual processed image URL
            #     }]
            # }]

            # # Submit the order.
            # order_response = submit_walgreens_order(
            #     first_name="Jane",
            #     last_name="Doe",
            #     phone="5555555555",
            #     email="customer@example.com",
            #     store_num=store_num,
            #     promise_time=promise_time,
            #     product_details=product_details,
            #     aff_notes="Passport Photo Order"
            # )
            # print("Order submitted successfully:", order_response)
    except Exception as e:
        print("Error:", e)
