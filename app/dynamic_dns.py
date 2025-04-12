import requests
import json
import requests
import re
import sys

apiConfig = json.load(open("config.json", "r"))

def getRecords(domain): #grab all the records so we know which ones to delete to make room for our record. Also checks to make sure we've got the right domain
    allRecords=json.loads(requests.post(apiConfig["endpoint"] + '/dns/retrieve/' + domain, data = json.dumps(apiConfig)).text)
    if allRecords["status"]=="ERROR":
        print('Error getting domain. Check to make sure you specified the correct domain, and that API access has been switched on for this domain.');
        sys.exit()
    return(allRecords)

def get_public_ip():
    try:
        response = requests.get("https://4.ipquail.com/ip", timeout=5)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        return response.text.strip()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching IP from ipquail: {e}")
        return None

def load_addresses_for_ddns():
    try:
        with open("ddns_addresses.txt", "r") as file:
            addresses = file.readlines()
        return [address.strip() for address in addresses if address.strip()]
    except FileNotFoundError:
        print("ddns_addresses.txt not found.")
        return []

def get_root_domain(domain):
    # Use regex to extract the root domain from a full domain name
    match = re.search(r"([^\.]+\.[^\.]+)$", domain)
    if match:
        return match.group(1)
    else:
        print(f"Invalid domain format: {domain}")
        return None

def process_root_domains(root_domains, addresses, public_ip):
    results = {"successes": [], "failures": []}
    addresses_set = set(addresses)

    for root_domain in root_domains:
        allRecords = getRecords(root_domain)
        print(f"Processing {root_domain} with {len(allRecords['records'])} records")

        known_record_names = set()

        if allRecords["status"] == "SUCCESS":
            print(f"Successfully retrieved records for {root_domain}.")

            for record in allRecords["records"]:
                # Construct the full domain name for comparison
                if record["name"] == "@":
                    full_record_name = root_domain
                elif record["name"].endswith(root_domain):
                    full_record_name = record["name"]
                else:
                    full_record_name = f"{record['name']}.{root_domain}"

                known_record_names.add(full_record_name.lower())
                skipped_count = 0
                already_correct_count = 0
                updated_count = 0
                failed_count = 0
                if full_record_name.lower() in addresses_set:
                    if record["content"] != public_ip:
                        print(f"Updating {record['name']} from {record['content']} to {public_ip}")
                        update_response = requests.post(apiConfig["endpoint"] + f'/dns/edit/{root_domain}/{record["id"]}', data=json.dumps({
                            "secretapikey": apiConfig["secretapikey"],
                            "apikey": apiConfig["apikey"],
                            "name": record["name"],
                            "type": record["type"],
                            "content": public_ip,
                            "ttl": record.get("ttl", 600)
                        }))
                        update_status = json.loads(update_response.text)
                        if update_status.get("status") == "SUCCESS":
                            updated_count += 1
                            results["successes"].append(full_record_name)
                        else:
                            failed_count += 1
                            results["failures"].append({"name": full_record_name, "error": update_status})
                    else:
                        already_correct_count += 1
                        results["successes"].append(full_record_name)
                else:
                    skipped_count += 1

            print(f"Skipped {skipped_count} records that are not in the address list.")
            print(f"Already correct {already_correct_count} records.")
            print(f"Updated {updated_count} records.")
            print(f"Failed to update {failed_count} records.")
            # Check for missing addresses and create them
            for address in addresses_set:
                if not address.endswith(root_domain):
                    continue  # Skip if the address doesn't belong to this root

                if address.lower() not in known_record_names:
                    subdomain = address.replace(f".{root_domain}", "")
                    print(f"Creating missing A record for {address} (subdomain: '{subdomain}')")

                    create_response = requests.post(apiConfig["endpoint"] + f'/dns/create/{root_domain}', data=json.dumps({
                        "secretapikey": apiConfig["secretapikey"],
                        "apikey": apiConfig["apikey"],
                        "name": "" if subdomain == root_domain else subdomain,
                        "type": "A",
                        "content": public_ip,
                        "ttl": 600
                    }))
                    create_status = json.loads(create_response.text)

                    if create_status.get("status") == "SUCCESS":
                        print(f"Successfully created A record for {address}.")
                        results["successes"].append(address)
                    else:
                        print(f"Failed to create record for {address}: {create_status}")
                        results["failures"].append({"name": address, "error": create_status})

        else:
            print(f"Error retrieving records for {root_domain}: {allRecords['status']}")
            results["failures"].append({"domain": root_domain, "error": allRecords["status"]})

    return results


def check_and_update_dns():
    print("Starting DNS update process...")
    public_ip = get_public_ip()
    if not public_ip:
        return {"status": "error", "message": "Failed to get public IP"}

    addresses = load_addresses_for_ddns()
    if not addresses:
        return {"status": "error", "message": "No addresses loaded"}


    root_domains = set()
    for address in addresses:
        root_domain = get_root_domain(address)
        if root_domain:
            root_domains.add(root_domain)
    print(addresses)
    results = process_root_domains(root_domains, addresses, public_ip)

    print(f"DNS update process completed. {len(results['successes'])} successes, {len(results['failures'])} failures.")

    return {
        "status": "success",
        "public_ip": public_ip,
        "results": results,
        "addresses": addresses,
        "root_domains": list(root_domains)
    }


if __name__ == "__main__":
    public_ip = get_public_ip()
    if public_ip:
        print(f"Public IP address: {public_ip}")
    else:
        print("Could not retrieve public IP address.")

    addresses = load_addresses_for_ddns()
    if addresses:
        print(f"Loaded addresses for DDNS, {len(addresses)} found.")
    else:
        print("No addresses loaded for DDNS.")

    # Get unique root domains
    root_domains = set()
    for address in addresses:
        root_domain = get_root_domain(address)
        if root_domain:
            root_domains.add(root_domain)

    if root_domains:
        print(f"Unique root domains found: {', '.join(root_domains)}")
    else:
        print("No valid root domains found.")

    results = process_root_domains(root_domains, addresses, public_ip)
    print("Dynamic DNS update process completed.")