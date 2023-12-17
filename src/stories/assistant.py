import openai
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_not_exception_type, retry_if_exception_type


class RunError(Exception):
    ''' Raised when a run has an unsuccessful status. '''
    def __init__(self, run: openai.types.beta.threads.Run, *args):
        super().__init__(*args)
        self.run = run


class AssistantsAPI:
    ''' A wrapper around the OpenAI Assistant API. '''
    
    def __init__(self, client: OpenAI):
        self.client = client

     
    def assistant(self, id: str):
        try:
            return self.client.beta.assistants.retrieve(id)
        except:
            return None
    
    
    def assistants(self, order: str = 'desc', limit: str = '20', **kwargs):
        return list(self.client.beta.assistants.list(order=order, limit=limit, **kwargs))
    
    
    def add_assistant(self, name: str, **kwargs):
        return self.client.beta.assistants.create(name=name, **kwargs)
    
    
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

    
    def delete_assistant(self, assistant_id: str):
        return self.client.beta.assistants.delete(assistant_id)

    
    def thread(self, id: str):
        return self.client.beta.threads.retrieve(id)
    
    
    def add_thread(self, **kwargs):
        return self.client.beta.threads.create(**kwargs)

    
    def delete_thread(self, thread_id: str):
        return self.client.beta.threads.delete(thread_id).deleted

    
    def messages(self, thread_id: str, order: str = 'asc', **kwargs):
        return list(self.client.beta.threads.messages.list(thread_id=thread_id, order=order, **kwargs))
    
    
    def add_message(self, thread_id: str, role: str, content: str, **kwargs):
        return self.client.beta.threads.messages.create(
            thread_id=thread_id,
            role=role,
            content=content,
            **kwargs,
        )

    
    def update_message(self, message_id: str, thread_id: str, metadata: dict):
        return self.client.beta.threads.messages.update(
            message_id=message_id,
            thread_id=thread_id,
            metadata=metadata,
        )

    
    def run(self, thread_id: str, run_id: str):
        return self.client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run_id)
    
    
    def runs(self, thread_id: str, order: str = 'asc', **kwargs):
        return list(self.client.beta.threads.runs.list(thread_id=thread_id, order=order, **kwargs))
    
    
    def add_run(self, thread_id: str, assistant_id: str, **kwargs):
        return self.client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=assistant_id,
            **kwargs
        )
    
    
    def update_run(self, run_id: str, thread_id: str, metadata: dict):
        return self.client.beta.threads.runs.update(
            run_id=run_id,
            thread_id=thread_id,
            metadata=metadata,
        )

    
    def step(self, thread_id: str, run_id: str, step_id: str):
        return self.client.beta.threads.runs.steps.retrieve(thread_id=thread_id, run_id=run_id, step_id=step_id)
    
    
    def steps(self, thread_id: str, run_id: str, order: str = 'asc', **kwargs):
        return list(self.client.beta.threads.runs.steps.list(thread_id=thread_id, run_id=run_id, order=order, **kwargs))

    
    def submit_tool_outputs(self, thread_id: str, run_id: str, tool_outputs: list[dict[str, str]]):
        return self.client.beta.threads.runs.submit_tool_outputs(
            thread_id=thread_id,
            run_id=run_id,
            tool_outputs=tool_outputs
        )
    
    
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


def generate_audio(client, prompt, model='tts-1', voice='nova', format='opus', **kwargs):
    return client.audio.speech.create(
        model=model,
        voice=voice,
        input=prompt,
        response_format=format,
        **kwargs
    )