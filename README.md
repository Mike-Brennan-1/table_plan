# To do:

- Documentaiton
    - README
    - Docstring
- Unit tests
- Demo data

# Quickstart

## Clone the repo
To try the app for yourself, start by cloning the repo.
```bash
git clone https://github.com/Mike-Brennan-1/table_plan.git
cd table_plan
```

## Install dependencies
### With Poetry
This project uses [Poetry](https://python-poetry.org/) for dependency management. If you have Poetry installed, simply run the following.
```bash
poetry install
```
This also initialises a virtual environment.
### Using pip
```bash
pip install requirements.txt
```
## Launch the app
Once you have installed dependencies, you are ready to launch the app. The frontend is built using [Streamlit](https://streamlit.io/), and defined in [`app.py`](src/table_plan/app.py). To launch the app, run the following in terminal.
**If you're using Poetry**
```bash
poetry run streamlit run src/table_plan/app.py
```
**Using pip**
```bash
streamlit run src/table_plan/app.py
```

# Datasets
>The datasets used in this repo are dummy data. An LLM was used to generate names of organisaitons and individuals; any similarity to real-world people or entities is cooincidental.

The project uses three datasets:
- Delegates: guests at the conference
- Exhibitors: companies who are sponsoring the conference and want to network with certain delegates
- Interactions: QR scanning logs showing which delegates visited with exhibitors' stands
