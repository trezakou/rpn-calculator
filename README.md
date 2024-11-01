# rpn-calculator
RPN calculator implementation using FASTAPI

## Stack used

* Fastapi app
* Database (SQLite)

## Installation

### Creating env:

An Anaconda venv was used during the development of this project, please create your own env with **python=3.11**

like so:

```bash
conda create -n ENVNAME python=3.11
```

### Dependency installations

To install the necessary packages:

```bash
conda activate ENVNAME
pip install poetry
poetry install # --with dev : to install dev dependencies
```

This will install the required packages within your venv.

---

### Running the app

Finally, run the API itself with the following command:

```zsh
uvicorn app.main:app --reload
```

### Accessing the swagger

when the app is running, the API swagger is available here:

http://localhost:8000/


## testing:

### launch tests and coverage generation:
```zsh
pytest --cov=app --cov-report=html --cov-report=term-missing --cov-branch tests/
```

### open coverage report in browser
```zsh
open htmlcov/index.html
```
