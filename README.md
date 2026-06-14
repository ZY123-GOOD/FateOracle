# 🔮 Bazi Analysis System

[![Chinese Version](https://img.shields.io/badge/中文版-README--cn.md-blue)](README-cn.md)

A professional Chinese Astrology (BaZi) analysis web application built with Streamlit.

## ✨ Features

- **BaZi Chart Calculation**: Accurate birth chart calculation based on birth date, time, and location
- **True Solar Time**: Automatic adjustment for true solar time based on longitude
- **Comprehensive Analysis**: 
  - Basic BaZi analysis
  - Day Master and Ten Gods analysis
  - DaYun (10-year luck period) and LiuNian (yearly luck) analysis
- **AI-powered Q&A**: Ask questions about your destiny and get AI-generated insights
- **Compatibility Analysis**: Analyze relationship compatibility between two people
- **User Management**: Registration, login, and credit system
- **History Records**: Save and manage your BaZi analysis history

## 🛠️ Tech Stack

- **Framework**: Streamlit
- **Language**: Python 3.8+
- **Database**: SQLite
- **API**: OpenAI-compatible API

## 📦 Installation

```bash
# Clone the repository
git clone https://github.com/your-username/BaZi.git
cd BaZi

# Install dependencies
pip install -r requirements.txt
```

## ⚙️ Configuration

Create a `.env` file in the project root with the following environment variables:

```env
# API Configuration
BAZI_API_KEY=your-api-key-here
BAZI_API_BASE_URL=https://api.example.com/v1
BAZI_MODEL=your-model-name
```

## 🚀 Running the App

```bash
# Development mode
streamlit run app.py

# Production mode
streamlit run app.py --server.headless=true
```

## 📖 Usage

1. **Register/Login**: Create an account or login with existing credentials
2. **Input Birth Information**: Enter your birth date, time, gender, and birth city
3. **Generate BaZi Chart**: Click "开始排盘" to generate your BaZi chart
4. **View Analysis**: Explore the basic analysis and Q&A sections
5. **Compatibility Analysis**: Use the "八字相合" tab to analyze relationships

## 📁 Project Structure

```
BaZi/
├── app.py                 # Main Streamlit application
├── bazi_core.py           # Core BaZi calculation logic
├── city_location.py       # City longitude database
├── api_client.py          # API client for AI analysis
├── user_manager.py        # User management module
├── prompt_builder.py      # Prompt templates for AI
├── requirements.txt       # Dependencies
└── .streamlit/
    └── config.toml        # Streamlit configuration
```

## 📄 License

This project is for personal use only.

## ⚠️ Disclaimer

This application is for entertainment purposes only. The astrological analysis provided should not be considered as professional advice for important life decisions.
