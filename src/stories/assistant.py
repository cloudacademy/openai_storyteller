import openai
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_not_exception_type, retry_if_exception_type


class RunError(Exception):
    ''' Raised when a run has an unsuccessful status. '''
    def __init__(self, run: openai.types.beta.threads.Run, *args):
        super().__init__(*args)
        self.run = run

# A decorator used to retry API calls for the AssistantsAPI, that fail on the server side.
def retry_on_server_error(func):
    @retry(
            stop=stop_after_attempt(5), 
            wait=wait_fixed(2.5), 
            retry=(
                retry_if_exception_type(openai.APITimeoutError) |
                retry_if_exception_type(openai.InternalServerError) 
            ),
            reraise=True
    )
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper

class AssistantsAPI:
    ''' A wrapper around the OpenAI Assistant API. '''
    
    def __init__(self, client: OpenAI):
        self.client = client

    @retry_on_server_error 
    def assistant(self, id: str):
        try:
            return self.client.beta.assistants.retrieve(id)
        except:
            return None
    
    @retry_on_server_error
    def assistants(self, order: str = 'desc', limit: str = '20', **kwargs):
        return list(self.client.beta.assistants.list(order=order, limit=limit, **kwargs))
    
    @retry_on_server_error
    def add_assistant(self, name: str, **kwargs):
        return self.client.beta.assistants.create(name=name, **kwargs)
    
    @retry_on_server_error
    def update_assistant(self, assistant_id: str, **kwargs):
        # Get the existing assistant.
        assistant = self.assistant(assistant_id)
        # Update the properties.
        for key, value in kwargs.items():
            setattr(assistant, key, value)
        # Save the changes.
        return self.client.beta.assistants.update(
            assistant.id, 
            **assistant.model_dump(
                exclude_unset=True,
                exclude_none=True,
                exclude=[
                    'id', 'created_at', 'object', 
                ]
            )
        )

    @retry_on_server_error
    def delete_assistant(self, assistant_id: str):
        return self.client.beta.assistants.delete(assistant_id)

    @retry_on_server_error
    def thread(self, id: str):
        return self.client.beta.threads.retrieve(id)
    
    @retry_on_server_error
    def add_thread(self, **kwargs):
        return self.client.beta.threads.create(**kwargs)

    @retry_on_server_error
    def delete_thread(self, thread_id: str):
        return self.client.beta.threads.delete(thread_id).deleted

    @retry_on_server_error
    def messages(self, thread_id: str, order: str = 'asc', **kwargs):
        return list(self.client.beta.threads.messages.list(thread_id=thread_id, order=order, **kwargs))
    
    @retry_on_server_error
    def add_message(self, thread_id: str, role: str, content: str, **kwargs):
        return self.client.beta.threads.messages.create(
            thread_id=thread_id,
            role=role,
            content=content,
            **kwargs,
        )

    @retry_on_server_error
    def update_message(self, message_id: str, thread_id: str, metadata: dict):
        return self.client.beta.threads.messages.update(
            message_id=message_id,
            thread_id=thread_id,
            metadata=metadata,
        )

    @retry_on_server_error
    def run(self, thread_id: str, run_id: str):
        return self.client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run_id)
    
    @retry_on_server_error
    def runs(self, thread_id: str, order: str = 'asc', **kwargs):
        return list(self.client.beta.threads.runs.list(thread_id=thread_id, order=order, **kwargs))
    
    @retry_on_server_error
    def add_run(self, thread_id: str, assistant_id: str, **kwargs):
        return self.client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=assistant_id,
            **kwargs
        )
    
    @retry_on_server_error
    def update_run(self, run_id: str, thread_id: str, metadata: dict):
        return self.client.beta.threads.runs.update(
            run_id=run_id,
            thread_id=thread_id,
            metadata=metadata,
        )

    @retry_on_server_error
    def step(self, thread_id: str, run_id: str, step_id: str):
        return self.client.beta.threads.runs.steps.retrieve(thread_id=thread_id, run_id=run_id, step_id=step_id)
    
    @retry_on_server_error
    def steps(self, thread_id: str, run_id: str, order: str = 'asc', **kwargs):
        return list(self.client.beta.threads.runs.steps.list(thread_id=thread_id, run_id=run_id, order=order, **kwargs))

    @retry_on_server_error
    def submit_tool_outputs(self, thread_id: str, run_id: str, tool_outputs: list[dict[str, str]]):
        return self.client.beta.threads.runs.submit_tool_outputs(
            thread_id=thread_id,
            run_id=run_id,
            tool_outputs=tool_outputs
        )
    
    @retry_on_server_error
    def cancel_run(self, thread_id: str, run_id: str):
        return self.client.beta.threads.runs.cancel(thread_id=thread_id, run_id=run_id)
    
    @retry(stop=stop_after_attempt(10), wait=wait_fixed(1.5), retry=retry_if_not_exception_type(RunError))
    def wait_for_run(self, thread_id: str, run_id: str) -> openai.types.beta.threads.Run:
        match (run := self.run(thread_id, run_id)).status:
            case 'queued' | 'in_progress' | 'cancelling':
                raise Exception(f'waiting on run with status: {run.status}')
            case 'requires_action' | 'completed':
                return run       
            case _:
                raise RunError(run)
            

###############################################################################
# Non-assistant API calls.
###############################################################################
@retry_on_server_error
def generate_image(client, prompt, style='natural', number=1, size='1024x1024', model='dall-e-3', format='b64_json', quality='standard', **kwargs):
    return client.images.generate(
        prompt=prompt, 
        style=style, 
        n=number, 
        size=size, 
        model=model, 
        response_format=format,
        quality=quality,
        **kwargs
    )

@retry_on_server_error
def generate_audio(client, prompt, model='tts-1', voice='nova', format='opus', **kwargs):
    return client.audio.speech.create(
        model=model,
        voice=voice,
        input=prompt,
        response_format=format,
        **kwargs
    )