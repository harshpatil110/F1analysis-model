# F1 Analysis Model (Python + FastF1 + Streamlit)

# 🏎️ Formula One Analysis Dashboard
A complete **F1 data analysis platform** built using **Python, FastF1, Streamlit, Pandas, Plotly, and Matplotlib**.  
This application allows you to explore **telemetry, race pace, strategy, sector analysis, pit stops, tyre usage**, and more for any Grand Prix and any Formula 1 season supported by **FastF1**.

---

## 🚀 Live Demo
*(Add your Streamlit Cloud URL here after deployment)*  
👉 **Live App:** [https://f1-analysis-harsh.streamlit.app/](https://f1-analysis-harsh.streamlit.app/)
---

## 🎯 Project Overview
This project includes:

- Telemetry comparison (speed, throttle, brake, gear, RPM)  
- Fastest lap analysis  
- Sector performance evaluation  
- Race pace modeling & lap-time deltas  
- Pit strategy breakdown  
- Tyre compound timelines  
- Stint analysis & tyre degradation modeling  
- Driver vs driver comparisons  
- Fully interactive Streamlit UI Dashboard  

---

## ⭐ Features

### 🔹 1. Driver Analysis
- Fastest lap detection  
- Sector breakdown  
- Rolling race-pace curves  
- Average sector comparison  
- Lap delta visualization  

### 🔹 2. Telemetry Dashboard
- Speed vs distance  
- Throttle & brake traces  
- Gear usage visualization  
- RPM curves  
- DRS activation markers  

### 🔹 3. Strategy & Tyre Analytics
- Pit stop timeline  
- Tyre compound usage charts  
- Stint analysis  
- Pit delta estimation  
- Undercut / overcut impact  

### 🔹 4. Machine Learning (Optional)
- Tyre degradation prediction  
- Race pace predictor  
- Pit-window estimation model  

### 🔹 5. Streamlit UI
- Clean UI with dropdown filters  
- Dynamic tabs  
- Interactive Plotly charts + Matplotlib telemetry overlays  
- Mobile-friendly responsive design  

---

## 📂 Project Structure
/f1_analysis_app
│── app.py
│── requirements.txt
│── /backend
│      ├── data_loader.py
│      ├── analysis.py
│      ├── telemetry.py
│      ├── compare.py
│      ├── strategy.py
│      ├── ml_model.py
│── /utils
│      ├── plotting.py
│      ├── helpers.py
│── /assets
       ├── logo.png

---

## 🛠️ Installation

### 1️⃣ Clone the repository
git clone https://github.com/yourusername/f1-analysis-app.git
cd f1-analysis-app

### 2️⃣ Install dependencies
pip install -r requirements.txt

### 3️⃣ Enable FastF1 cache
import fastf1
fastf1.Cache.enable_cache("cache")

---

## ▶️ Running Locally
streamlit run app.py

Visit:
http://localhost:8501

---

## 🌐 Deployment Guide

### ✅ 1. Deploy on Streamlit Cloud
fastf1.Cache.enable_cache('/mount/data/fastf1_cache')

### 🟦 2. Deploy to Render.com
Add `render.yaml` with proper commands.

### 🟪 3. Deploy on Railway.app
streamlit run app.py --server.port=$PORT --server.address=0.0.0.0

### 🟥 4. Docker Deployment
docker build -t f1-analysis .
docker run -p 8501:8501 f1-analysis

---

## 📌 requirements.txt
fastf1
pandas
numpy
matplotlib
plotly
streamlit
scikit-learn
seaborn

---

## 🧪 Tests
tests/
├── test_loader.py
├── test_telemetry.py

---

## 🏁 Future Improvements
- Live leaderboard  
- AI overtaking prediction  
- Monte-Carlo strategy optimizer  
- Race simulation engine  

---

## ❤️ Credits
- FastF1 Team  
- Formula 1  
- Streamlit  

---


