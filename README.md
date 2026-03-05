myCharger EV Center ⚡🚗

myCharger is an end-to-end electric vehicle (EV) charging point management system designed to streamline EV charging operations. It serves as a comprehensive hybrid microservices solution, allowing users to effortlessly book charging sessions through a WhatsApp Bot interface while providing administrators with real-time analytics and robust control over physical chargers.

✨ Key Features

🤖 WhatsApp Bot Interface

Seamless Booking: Users can easily book and manage their EV charging sessions directly through WhatsApp.

Automated Logic: Powered by a robust FastAPI backend that handles user interactions, webhooks, and core system management.

🔌 Java OCPP Server

High Concurrency: A highly scalable server capable of managing up to 100,000 concurrent physical connections.

Hardware Control: Utilizes the industry-standard WebSockets and OCPP 1.6 protocol to directly control and communicate with physical EV charging stations.

📊 Admin Dashboard

Real-Time Analytics: Visual dashboard providing instant insights into energy metrics, revenue tracking, and overall system health.

Modern Interface: Built with React and Vite for a lightning-fast, responsive administrative experience.

💾 Data Management

Persistent Storage: Centralized state management utilizing PostgreSQL to track charger availability, session histories, and financial data securely.

🛠️ Tech Stack

Backend: Python (FastAPI), Java (Maven)

Frontend: React, Vite, Tailwind CSS

Database: PostgreSQL

DevOps & Cloud: Docker, Azure DevOps (CI/CD), Microsoft Azure

Communication: WhatsApp Business API, WebSockets (OCPP)

🚀 Getting Started

To get a local copy up and running, follow these steps.

Prerequisites

Docker and Docker Compose (Docker Desktop recommended).

Java 17 or newer (for local OCPP server development).

Python 3.9 or newer (for backend API).

Node.js 22 (for frontend development).

Installation

Clone the repository

Bash
git clone https://github.com/tt703/EV-CHARGING.git
Run the entire stack using Docker Compose

Bash
docker-compose up --build
This will automatically spin up the PostgreSQL database (port 5433), the Java OCPP Server (port 8887), the FastAPI backend (port 8000), and the React frontend (accessible at http://localhost:3000).
