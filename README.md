#  **The Visionaries — Real-Time Crowd & Airport Screen Intelligence**

### *LabLab.ai Genesis Hackathon*

The Visionaries is a lightweight, production-ready FastAPI backend powered by **Gemini 2.5 Flash (Multimodal Vision)**.
It analyzes **images from airports, public spaces, and events** to provide:

###  **Key Capabilities**

* **Crowd Detection:**
  Identifies how many people are present (low / moderate / high density).

* **Airport Screen Understanding:**
  If the image contains a **departure/arrival screen**, it extracts:
  ✓ Flight Number
  ✓ Departure / Arrival Time
  ✓ Gate
  ✓ Status (On time / Delayed / Boarding)

* **General Vision Intelligence:**
  If the image contains something else, it explains the scene clearly.

This makes it ideal for **smart airports**, **safety monitoring**, **crowd analytics**, or **real-time operations dashboards**.

---

#  **Tech Stack**

| Component      | Technology                                  |
| -------------- | ------------------------------------------- |
| AI Model       | Google **Gemini 2.5 Flash** (Vision + Text) |
| Backend        | FastAPI                                     |
| Image Handling | python-multipart                            |
| Deployment     | Uvicorn                                     |
| Environment    | `.env`                                      |

---

#  **Project Structure**

```
the-visionaries/
│── app.py
│── requirements.txt
│── .env.example
└── README.md
```

---

#  **Setup Instructions**

### 1️⃣ Clone or Download

Download the repo or clone:

```
git clone https://github.com/<your-username>/the-visionaries.git
cd the-visionaries
```

### 2️⃣ Install Dependencies

```
pip install -r requirements.txt
```

### 3️⃣ Add Environment Variable

Create a `.env` file:

```
GEMINI_API_KEY=YOUR_KEY_HERE
```

### 4️⃣ Run the Server

```
uvicorn app:app --reload
```

Server runs at:

```
http://localhost:8000
```

---

#  **API Endpoints**

## **POST /analyze-image**

Upload any image and get:

* Crowd level
* Airport screen info (if detected)
* General scene description

### **Example Request (Postman / Swagger UI):**

1. Choose **POST** → `/analyze-image`
2. Set form-data:

   * key: `file`
   * type: **File**
   * value: *upload your image*

### **Example Response**

```json
{
  "crowdLevel": "High crowd detected (approx. 35+ people)",
  "flightInfo": {
    "flight": "EK 701",
    "gate": "A12",
    "time": "09:45",
    "status": "Boarding"
  },
  "generalDescription": "A busy airport terminal with a departure screen, passengers, luggage and overhead signs."
}
```

---

#  **Features Under the Hood**

### ✔ Smart Multimodal Prompting

Automatically guides Gemini to:

* Count people
* Detect screens
* Extract structured flight info
* Provide fallback general scene description

### ✔ Clean, production-ready FastAPI code

Includes:

* File validation
* Proper MIME handling
* Clear prompts
* JSON responses
* Error handling

### ✔ Safe Environment Handling

`.env.example` provided — actual key is never uploaded.

---

#  **Use Cases**

* Airport Operations
* Passenger Flow Monitoring
* Smart Security
* Real-Time Dashboards
* Event Management
* Public Transport Hubs
* Emergency Response

---
