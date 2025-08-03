import requests


def process_pdf(
    file_path: str, server_url: str = "http://localhost:8000/api/v1/process-pdf"
) -> dict:
    """
    Sends a PDF file to the FastAPI endpoint for processing.

    Args:
        file_path (str): Path to the PDF file to process.
        server_url (str): Endpoint URL (default: http://localhost:8000/api/v1/process-pdf)

    Returns:
        dict: The JSON response from the API.
    """
    with open(file_path, "rb") as f:
        files = {"file": (file_path, f, "application/pdf")}
        headers = {
            "accept": "application/json",
        }

        response = requests.post(server_url, headers=headers, files=files)

    try:
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        print(f"HTTP error occurred: {e}")
        return {"error": str(e), "details": response.text}
    except Exception as e:
        print(f"Other error occurred: {e}")
        return {"error": str(e)}


# Example usage
if __name__ == "__main__":
    result = process_pdf("Invoice.pdf")
    print(result)
