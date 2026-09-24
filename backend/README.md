# Ubuntu Terra — Early Water Stress Warning System

Welcome to **Ubuntu Terra**!

Ubuntu Terra is an easy-to-use map tool built for South African farmers, farm managers, and agricultural advisors. It combines **satellite imagery**, **weather updates**, and **temperature tracking** to give you early warnings when crops face water stress—well before visible damage shows up on your fields.

---

## What Does Ubuntu Terra Do?

Instead of forcing you to read complex satellite maps or spreadsheet tables, Ubuntu Terra organizes everything visually:

1. **View Fields on an Interactive Map:** Find and select farm blocks (such as citrus or vegetable crops) in regions like the Gamtoos and Sundays River Valleys.
2. **Check Crop Health & Water Stress:** Instantly see a simple risk badge (**Low**, **Medium**, or **High**) alongside a plain-English summary explaining _why_ that risk level was detected.
3. **Track Simple Trends:** View simple graphs for vegetation index (NDVI), recent rainfall, and temperature over time.
4. **Preview Mobile Alerts:** See exact sample SMS or WhatsApp notification messages tailored for farm managers and field crews.

---

## What You Need to Download & Install

Before starting, make sure your computer has the following 3 free tools installed:

### 1. Node.js (Version 18 or newer)

- **What it does:** Runs the visual user interface (frontend).
- **Download link:** [https://nodejs.org](https://nodejs.org) (Download the "LTS" version).

### 2. Python (Version 3.10 or newer)

- **What it does:** Runs the intelligent calculations and data service (backend).
- **Download link:** [https://www.python.org](https://www.python.org)
- **Important Note:** During installation on Windows, make sure to check the box that says **"Add Python to PATH"**.

### 3. PostgreSQL (with PostGIS extension)

- **What it does:** Stores spatial map shapes (polygons) and field readings.
- **Download link:** [https://www.postgresql.org](https://www.postgresql.org)

---

## How to Set Up & Run Ubuntu Terra

Follow these step-by-step instructions after downloading or cloning the project folder to your computer.

### Step 1: Open Terminal or Command Prompt

- **Windows:** Press `Win + R`, type `cmd`, and press Enter.
- **Mac:** Press `Cmd + Space`, type `Terminal`, and press Enter.

Navigate into the cloned folder:

```bash
cd ubuntu-terra
```

---

### Step 2: Start the Backend (Data Engine)

1. Open your terminal and move into the `backend` folder:

   ```bash
   cd backend
   ```

2. Create and activate a clean virtual environment:
   - **Windows:**
     ```bash
     python -m venv venv
     venv\Scripts\activate
     ```
   - **Mac / Linux:**
     ```bash
     python3 -m venv venv
     source venv/bin/activate
     ```

3. Install required software libraries:

   ```bash
   pip install -r requirements.txt
   ```

4. Launch the server:
   ```bash
   uvicorn app.main:app --reload
   ```

   - You will see a message confirming the server is live at `http://127.0.0.1:8000`. Leave this terminal open.

---

### Step 3: Start the Frontend (Interactive Map App)

1. Open a **second** terminal window or tab (keep the backend terminal running).
2. Navigate into the `frontend` directory:

   ```bash
   cd ubuntu-terra/frontend
   ```

3. Install the application dependencies:

   ```bash
   npm install
   ```

4. Start the app:

   ```bash
   npm run dev
   ```

5. Click or open the web link shown in your terminal (usually `http://localhost:5173`) in your internet browser.

---

## How to Use the Application

1. **Select a Field:**
   - Navigate around the interactive map.
   - Click on any field polygon (e.g., _Patensie Citrus Block 4_ or _Hankey Vegetable Field_).

2. **Review Field Health:**
   - Look at the sidebar panel on the right.
   - Check the **Risk Rating** (Green = Low Risk, Yellow = Moderate Risk, Red = High Risk).
   - Read the plain-language explanation of environmental drivers (e.g., _"14-day rainfall deficit combined with elevated land surface temperature"_).

3. **Inspect Trends & Mobile Notifications:**
   - Scroll down the panel to view 30-day vegetation, rainfall, and temperature trend charts.
   - Review the **Alert Preview** box at the bottom to see what an automated SMS/WhatsApp warning would look like when sent to field workers.

---

## Troubleshooting & FAQs

- **The map display is blank:**  
  Make sure your computer is connected to the internet so background map imagery can load.

- **Data is not showing up for fields:**  
  Verify that both terminal windows (Backend in Step 2 and Frontend in Step 3) are actively running without errors.

- **What happens if live satellite/weather APIs go offline?**  
  Ubuntu Terra automatically falls back to pre-loaded local readings so the application continues working reliably offline or in remote areas.

---
