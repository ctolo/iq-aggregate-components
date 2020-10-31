#!/usr/bin/python3
# ----------------------------------------------------------------------------
# Python Dependencies
import json
import argparse
import asyncio
import aiohttp

# ----------------------------------------------------------------------------
iq_url, iq_session, components = "", "", {}

def get_arguments():
    global iq_url, iq_session, iq_auth
    parser = argparse.ArgumentParser(description='Export Component')
    parser.add_argument('-u', '--url', help='', default="http://localhost:8070", required=False)
    parser.add_argument('-a', '--auth', help='', default="admin:admin123", required=False)
    args = vars(parser.parse_args())
    iq_url = args["url"]
    creds = args["auth"].split(":")
    iq_session = aiohttp.ClientSession()
    iq_auth = aiohttp.BasicAuth(creds[0], creds[1])
    return args

async def main():
    args = get_arguments()
    apps = await get_url(f'{iq_url}/api/v2/applications', "applications")
    reports = []

    for resp in asyncio.as_completed([handle_app(app) for app in apps]):
        reports.extend(await resp)

    for resp in asyncio.as_completed([handle_details(report) for report in reports]):
        report = await resp
        app_details = {"stage": report["stage"], "publicId": report["publicId"]}
        for c in report["components"]:
            hash_ = c["hash"]
            if hash_ in components:
                components[ hash_ ]["apps"].append(app_details)

    with open("results.json", "w+") as file:
        # file.write(json.dumps(components, indent=4))
        file.write(json.dumps(components))
    print("Json results saved to -> results.json")
    await iq_session.close()

#---------------------------------
def pp(page):
    print(json.dumps(page, indent=4))

async def handle_app(app):
    resp = []
    app_reports = await get_url(f'{iq_url}/api/v2/reports/applications/{app["id"]}')
    if app_reports is not None:
        for report in app_reports:
            resp.append({ 
                "publicId": app["publicId"], 
                "id": app["id"],
                "stage": report["stage"],
                "reportUrl": report["reportDataUrl"],
            })
    return resp

async def handle_details(report):
    global components
    data = await get_url(f'{iq_url}/{report["reportUrl"]}')
    for c in data["components"]:
        if c["hash"] is not None:
            if c["hash"] not in components:
                components.update({
                    c["hash"]: {
                        "packageUrl":c["packageUrl"],
                        "displayName":c["displayName"],
                        "apps":[]
                    }
                })
    report["components"] = data["components"]
    return report

async def get_url(url, root=""):
    resp = await iq_session.get(url, auth=iq_auth)
    if resp.status != 200:
        print(await resp.text())
        return None
    node = await resp.json()
    if root in node:
        node = node[root]
    if node is None or len(node) == 0:
        return None
    return node

if __name__ == "__main__":
    asyncio.run(main())
