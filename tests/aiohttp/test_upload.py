import json
from io import BytesIO

import aiohttp


async def test_single_file_upload(aiohttp_app_client):
    query = """mutation($textFile: Upload!) {
        readText(textFile: $textFile)
    }"""

    f = BytesIO(b"strawberry")
    operations = json.dumps({"query": query, "variables": {"textFile": None}})
    file_map = json.dumps({"textFile": ["variables.textFile"]})

    form_data = aiohttp.FormData()
    form_data.add_field("textFile", f, filename="textFile.txt")
    form_data.add_field("operations", operations)
    form_data.add_field("map", file_map)

    response = await aiohttp_app_client.post("/graphql", data=form_data)
    assert response.status == 200

    data = await response.json()

    assert not data.get("errors")
    assert data["data"]["readText"] == "strawberry"


async def test_file_list_upload(aiohttp_app_client):
    query = "mutation($files: [Upload!]!) { readFiles(files: $files) }"
    operations = json.dumps({"query": query, "variables": {"files": [None, None]}})
    file_map = json.dumps(
        {"file1": ["variables.files.0"], "file2": ["variables.files.1"]}
    )

    file1 = BytesIO(b"strawberry1")
    file2 = BytesIO(b"strawberry2")

    form_data = aiohttp.FormData()
    form_data.add_field("file1", file1, filename="file1.txt")
    form_data.add_field("file2", file2, filename="file2.txt")
    form_data.add_field("operations", operations)
    form_data.add_field("map", file_map)

    response = await aiohttp_app_client.post("/graphql", data=form_data)
    assert response.status == 200

    data = await response.json()

    assert not data.get("errors")
    assert len(data["data"]["readFiles"]) == 2
    assert data["data"]["readFiles"][0] == "strawberry1"
    assert data["data"]["readFiles"][1] == "strawberry2"


async def test_nested_file_list(aiohttp_app_client):
    query = "mutation($folder: FolderInput!) { readFolder(folder: $folder) }"
    operations = json.dumps(
        {"query": query, "variables": {"folder": {"files": [None, None]}}}
    )
    file_map = json.dumps(
        {"file1": ["variables.folder.files.0"], "file2": ["variables.folder.files.1"]}
    )

    file1 = BytesIO(b"strawberry1")
    file2 = BytesIO(b"strawberry2")

    form_data = aiohttp.FormData()
    form_data.add_field("file1", file1, filename="file1.txt")
    form_data.add_field("file2", file2, filename="file2.txt")
    form_data.add_field("operations", operations)
    form_data.add_field("map", file_map)

    response = await aiohttp_app_client.post("/graphql", data=form_data)
    assert response.status == 200

    data = await response.json()

    assert not data.get("errors")
    assert len(data["data"]["readFolder"]) == 2
    assert data["data"]["readFolder"][0] == "strawberry1"
    assert data["data"]["readFolder"][1] == "strawberry2"


async def test_extra_form_data_fields_are_ignored(aiohttp_app_client):
    query = """mutation($textFile: Upload!) {
        readText(textFile: $textFile)
    }"""

    f = BytesIO(b"strawberry")
    operations = json.dumps({"query": query, "variables": {"textFile": None}})
    file_map = json.dumps({"textFile": ["variables.textFile"]})
    extra_field_data = json.dumps({})

    form_data = aiohttp.FormData()
    form_data.add_field("textFile", f, filename="textFile.txt")
    form_data.add_field("operations", operations)
    form_data.add_field("map", file_map)
    form_data.add_field("extra_field", extra_field_data)

    response = await aiohttp_app_client.post("/graphql", data=form_data)
    assert response.status == 200


async def test_sending_invalid_form_data(aiohttp_app_client):
    headers = {"content-type": "multipart/form-data; boundary=----fake"}
    response = await aiohttp_app_client.post("/graphql", headers=headers)
    reason = await response.text()

    assert response.status == 400
    assert reason == "400: Unable to parse the multipart body"


async def test_malformed_query(aiohttp_app_client):
    f = BytesIO(b"strawberry")
    operations = json.dumps({"qwary": "", "variables": {"textFile": None}})
    file_map = json.dumps({"textFile": ["variables.textFile"]})

    form_data = aiohttp.FormData()
    form_data.add_field("textFile", f, filename="textFile.txt")
    form_data.add_field("operations", operations)
    form_data.add_field("map", file_map)

    response = await aiohttp_app_client.post("/graphql", data=form_data)
    reason = await response.text()

    assert response.status == 400
    assert reason == "400: No GraphQL query found in the request"


async def test_sending_invalid_json_body(aiohttp_app_client):
    f = BytesIO(b"strawberry")
    operations = "}"
    file_map = json.dumps({"textFile": ["variables.textFile"]})

    form_data = aiohttp.FormData()
    form_data.add_field("textFile", f, filename="textFile.txt")
    form_data.add_field("operations", operations)
    form_data.add_field("map", file_map)

    response = await aiohttp_app_client.post("/graphql", data=form_data)
    reason = await response.text()

    assert response.status == 400
    assert reason == "400: Unable to parse the multipart body"


async def test_upload_with_missing_file(aiohttp_app_client):
    # The aiohttp test client prevents us from sending invalid aiohttp.FormData.
    # To test invalid data anyway we construct it manually.
    data = (
        "------Boundary\r\n"
        'Content-Disposition: form-data; name="operations"\r\n'
        "\r\n"
        "{"
        '"query": "mutation($textFile: Upload!){readText(textFile: $textFile)}",'
        '"variables": {"textFile": null}'
        "}\r\n"
        "------Boundary\r\n"
        'Content-Disposition: form-data; name="map"\r\n'
        "\r\n"
        '{"textFile": ["variables.textFile"]}\r\n'
        "------Boundary--"
    )
    headers = {"content-type": "multipart/form-data; boundary=----Boundary"}

    response = await aiohttp_app_client.post("/graphql", data=data, headers=headers)
    reason = await response.text()

    assert response.status == 400
    assert reason == "400: File(s) missing in form data"
