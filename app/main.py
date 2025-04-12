from flask import Flask, jsonify, render_template, render_template_string
from threading import Thread
import time
import dynamic_dns

app = Flask(__name__)

status = {
    "public_ip": None,
    "last_checked_ip": None,
    "last_update": None,
    "update_results": None,
    "addresses": [],
    "root_domains": [],
    "grouped_addresses": {},
    "domain_status": {}
}

from collections import defaultdict

def group_addresses_by_domain(addresses):
    grouped = defaultdict(list)
    for address in addresses:
        root = dynamic_dns.get_root_domain(address)
        if root:
            grouped[root].append(address)
    return dict(grouped)


def classify_domain_status(root_domains, results):
    status_map = {}
    successes = set(results.get("successes", []))
    failures = results.get("failures", [])

    # Index failures by domain/address
    failure_names = set()
    for fail in failures:
        if "name" in fail:
            failure_names.add(fail["name"])
        elif "domain" in fail:
            failure_names.add(fail["domain"])

    for domain in root_domains:
        matched = [name for name in successes if name.endswith(domain)]
        failed = [name for name in failure_names if name.endswith(domain)]

        if matched and not failed:
            status_map[domain] = "success"
        elif matched and failed:
            status_map[domain] = "partial"
        else:
            status_map[domain] = "failure"
    return status_map


def monitor_loop(interval=300):
    while True:
        print("Checking DNS update...")
        result = dynamic_dns.check_and_update_dns()
        grouped_addresses = group_addresses_by_domain(result["addresses"])
        if result["status"] == "success":
            if result["public_ip"] != status["last_checked_ip"]:
                print(f"IP changed to {result['public_ip']}")
            else:
                print("IP unchanged.")


            status.update({
                "public_ip": result["public_ip"],
                "last_checked_ip": result["public_ip"],
                "last_update": time.strftime("%Y-%m-%d %H:%M:%S"),
                "update_results": result["results"],
                "addresses": result["addresses"],
                "root_domains": result["root_domains"],
                "grouped_addresses": grouped_addresses,
                "domain_status": classify_domain_status(result["root_domains"], result["results"])
            })
        else:
            print(f"Error during DDNS check: {result.get('message')}")

        time.sleep(interval)

@app.route("/")
def home():
    return render_template("status.html", s=status)

@app.route("/api/status")
def api_status():
    return jsonify(status)

if __name__ == "__main__":
    thread = Thread(target=monitor_loop, daemon=True)
    thread.start()
    app.run(host="0.0.0.0", port=8080)
