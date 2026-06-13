import requests

BASE_URL = "http://localhost:7860"

def test_contact_api():
    # 1. Post a new contact message
    payload = {
        "name": "Test User",
        "email": "test@example.com",
        "message": "Hello from automated test!"
    }
    
    print("Posting message...")
    response = requests.post(f"{BASE_URL}/api/contact", json=payload)
    print("Status code:", response.status_code)
    print("JSON:", response.json())
    assert response.status_code == 200
    assert response.json()["success"] is True
    msg_id = response.json()["message_id"]

    # 2. Get all contact messages
    print("\nRetrieving messages...")
    response = requests.get(f"{BASE_URL}/api/contact")
    print("Status code:", response.status_code)
    msgs = response.json()
    print("Messages list size:", len(msgs))
    assert response.status_code == 200
    
    # Verify the message we inserted exists
    found = False
    for m in msgs:
        if m["id"] == msg_id:
            found = True
            assert m["name"] == "Test User"
            assert m["email"] == "test@example.com"
            assert m["message"] == "Hello from automated test!"
            break
    assert found is True
    print("Verified message exists in database!")

    # 3. Test vCard download
    print("\nDownloading vCard...")
    response = requests.get(f"{BASE_URL}/api/contact/vcard")
    print("Status code:", response.status_code)
    print("Content-Type:", response.headers.get("Content-Type"))
    print("Content-Disposition:", response.headers.get("Content-Disposition"))
    print("Content preview:\n", response.text)
    assert response.status_code == 200
    assert "BEGIN:VCARD" in response.text
    assert "Prathamesh Jadhav" in response.text

    # 4. Delete the test contact message
    print("\nDeleting message...")
    response = requests.delete(f"{BASE_URL}/api/contact/{msg_id}")
    print("Status code:", response.status_code)
    print("JSON:", response.json())
    assert response.status_code == 200
    
    # 5. Verify deletion
    response = requests.get(f"{BASE_URL}/api/contact")
    msgs = response.json()
    found = any(m["id"] == msg_id for m in msgs)
    assert found is False
    print("Verified message deleted successfully!")
    print("\nALL CONTACT API TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_contact_api()
