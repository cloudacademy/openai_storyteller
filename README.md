
### Requirements

- Python 3.11+
- OpenAI API key


### Setup

1. Clone the repository.
    ```bash
    git clone "https://github.com/cloudacademy/openai_storyteller.git"

2. Change directory to the root of the project.
    ```bash
    cd openai_storyteller
    ```
    
3. Create a new virtual environment.
    ```bash
    python -m venv .venv
    ```

4. Activate the virtual environment.
    ```bash
    source .venv/bin/activate
    ```

5. Change directory to the root of the project.
    ```bash
    cd stories
    ```

6. Install the dependencies.
    ```bash
    pip install -r requirements.txt
    ```

7. Create a `.env` file in the root of the project and add the following environment variables.
    ```bash
    echo "OPENAI_API_KEY=<your-openai-api-key>" > .env
    ```

8. Add the current module to the Python path.
    ```bash
    export PYTHONPATH=$PYTHONPATH:$(pwd)/src
    ```

9. Start the UI.
    ```bash
    streamlit run src/stories/ui.py
    ```

10. Open the URL listed in the console.