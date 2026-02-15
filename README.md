# skillswap
SkillSwap is a web application that enables people to exchange skills using the “Matching” function, request help from other users, and communicate through an online chat, fostering collaborative learning.

## Features

- **User Profiles**: Add personal information, skills you can teach, and skills you want to learn.
- **Matching System**: Automatically find users who can teach the skills you want to learn.
- **Requests**: Send and accept skill exchange requests.
- **Chat Function**: Communicate with matched users in real time.
- **Dashboard**: Overview of your activity, matches, requests, and chats.
- **Responsive Design**: Works on mobile and desktop devices.

## Technologies

- **Backend**: Python, Flask
- **Database**: SQLite
- **Frontend**: HTML, CSS, Jinja2 templates
- **Authentication**: Password hashing with Werkzeug

## Installation

1. Clone the repository:
bash
git clone https://github.com/kakamah/skillswap.git
cd skillswap

2.	Create a virtual environment:
python -m venv venv
source venv/bin/activate   # Linux/Mac
venv\Scripts\activate      # Windows

3.	Install required packages:
pip install flask werkzeug

4.	Run the app:
python app.py

5.	Open your browser and go to:

http://127.0.0.1:5000/

License

This project is licensed under the MIT License.
