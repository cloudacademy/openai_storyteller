
### Requirements

- Python 3.11+
- OpenAI API key


### Setup

1. Create a new virtual environment.
    ```bash
    python -m venv .venv
    ```

2. Activate the virtual environment.
    ```bash
    source .venv/bin/activate
    ```

3. Change directory to the root of the project.
    ```bash
    cd stories
    ```

4. Install the dependencies.
    ```bash
    pip install -r requirements.txt
    ```

5. Create a `.env` file in the root of the project and add the following environment variables.
    ```bash
    echo "OPENAI_API_KEY=<your-openai-api-key>" > .env
    ```

6. Add the current module to the Python path.
    ```bash
    export PYTHONPATH=$PYTHONPATH:$(pwd)/src
    ```

7. Start the UI.
    ```bash
    streamlit run src/stories/ui.py
    ```