from dataclasses import dataclass, asdict
from base64 import b64decode
import json
from pathlib import Path
from typing import Any
import toml

from openai import OpenAI

from stories import render_template, resolve_file
from stories.assistant import AssistantsAPI, generate_audio, generate_image, RunError

class Storage:
    ''' A generic base class for storing collections of objects. '''

    def __init__(self) -> None:
        self.records: dict[str, Any] = {}

    def __setitem__(self, key, value):
        self.records[key] = value

    def __getitem__(self, key):
        return self.records[key]
    
    def __delitem__(self, key):
        del self.records[key]
    
    def __contains__(self, key):
        return key in self.records
    
    def __iter__(self):
        return iter(self.records.values())
    
    def __len__(self):
        return len(self.records)
    
    def many(self, *keys):
        return [self[key] for key in keys]

    @property
    def as_list(self):
        return [entity.as_dict for entity in self]
    
    @property
    def last(self):
        return list(self.records.values())[-1]
    
    @property
    def first(self):
        return list(self.records.values())[0]

class Entity:

    def __init__(self, type: str, name: str, desc: str) -> None:
        self.type = type
        self.name = name
        self.desc = desc

    def __str__(self):
        return f'{self.name} ({self.type}) | {self.desc}'
    
    @property
    def as_dict(self):
        return {
            'type': self.type,
            'name': self.name,
            'desc': self.desc,
        }

class Entities(Storage):
    
    def add(self, entity: Entity):
        self.records[entity.name] = entity

    def add_many(self, *entities: Entity):
        for entity in entities:
            self.add(entity)

    def load(self, *entity_dict: dict):
        self.__init__()
        for entity in entity_dict:
            self.add(Entity(**entity))

class Asset:
    def __init__(self, message_id: str, name: str, type: str, data: bytes = None, base: str = 'assets'):
        self.message_id = message_id
        self.name = name
        self.type = type
        self.base = base
        self.data = data
    
    @property
    def filename(self):
        return f'{self.message_id}-{self.name}.{self.type}'
   
    @property
    def content(self):
        if self.data is None:    
            with open((Path(self.base) / self.filename).resolve(), 'rb') as f:
                self.data = f.read()
        return self.data
    
    def __hash__(self) -> int:
        return hash(self.filename)
    
    def save(self):
        with open((Path(self.base) / self.filename).resolve(), 'wb') as f:
            f.write(self.data)

    @property
    def as_dict(self):
        return {
            'message_id': self.message_id,
            'name': self.name,
            'type': self.type,
            'base': self.base,
        }
    
class Assets(Storage):

    def __init__(self, base_dir: str) -> None:
        super().__init__()
        self.base_dir = base_dir
        

    def add(self, asset: Asset):
        self.records[asset.filename] = asset

    def load(self, *assets_dict: dict):
        self.__init__(self.base_dir)
        for asset in assets_dict:
            self.add(Asset(**asset))
    
class Message:

    def __init__(self, id: str, role: str, text: str, metadata: dict):
        self.id = id
        self.role = role
        self.text = text
        self.metadata = metadata

    @property
    def as_dict(self):
        return {
            'id': self.id,
            'role': self.role,
            'text': self.text,
            'metadata': self.metadata,
        }
    
    @classmethod
    def from_api(cls, message):
        return cls(
            id=message.id,
            role=message.role,
            text=message.content[0].text.value if message.content[0].type == 'text' else str(message),
            metadata=message.metadata,
        )

class Messages(Storage):

    def add(self, message: Message):
        self.records[message.id] = message
        return message

    def load(self, *messages_dict: dict):
        # Reset the messages.
        self.__init__()
        for message in messages_dict:
            self.add(Message(**message))

    def load_messages(self, *messages):
        for message in messages:
            self.add(message)

class Session:
    def __init__(self, id: str, name: str = None, theme: str = None, guidelines: str = None, assets_dir: str = 'assets') -> None:
        self.id = id
        self.name = name
        self.theme = theme
        self.guidelines = guidelines
        self.messages = Messages()
        self.entities = Entities()
        self.assets = Assets(base_dir=assets_dir) 

    @property
    def friendly_name(self):
        return self.name or self.id[:8]
    
    def load(self, session_dict: dict):
        self.__init__(self.id, self.name, self.assets.base_dir)

        for key, value in session_dict.items():
            # Messges are not stored locally, so we need to load them from the thread.
            if key == 'entities':
                self.entities.load(*value)
            elif key == 'assets':
                self.assets.load(*value)
            else:
                setattr(self, key, value)
        return self

    @property
    def as_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'theme': self.theme,
            'guidelines': self.guidelines,
            'entities': self.entities.as_list,
            'assets': self.assets.as_list,
        }       

class Sessions(Storage):
    
    def add(self, session: Session):
        self.records[session.id] = session
    
    def load(self, *sessions_dict: dict):
        self.__init__()
        for session in sessions_dict:
            self.add(Session(session['id']).load(session))

class StoryState:
    def __init__(self) -> None:
        self.sessions = Sessions()

          
    @property
    def as_dict(self):
        return {
            'sessions': self.sessions.as_list,
        }
    
    def load(self, story_state: dict):
        self.__init__()
        for key, value in story_state.items():
            if key == 'sessions':
                self.sessions.load(*value)
            else:
                setattr(self, key, value)
        return self
    
class Functions:

    def __init__(self, *functions: callable) -> None:
        self.__functions: dict[str, callable] = {}
        self.add_many(*functions)

    def __setitem__(self, key, value):
        self.__functions[key] = value

    def __getitem__(self, key):
        return self.__functions[key]
    
    def __contains__(self, key):
        return key in self.__functions
    
    def __iter__(self):
        return iter(self.__functions.values())
    
    def __len__(self):
        return len(self.__functions)
    
    def __call__(self, func_name: str, **kwds: Any) -> Any:
        return self.__functions[func_name](**kwds)
    

    def add_many(self, *functions: callable):
        for function in functions:
            self[function.__name__] = function

@dataclass
class ImageGenArgs:
    model: str      = 'dall-e-3'
    style: str      = 'natural'
    quality: str    = 'standard'
    size: str       = '1024x1024'

    def as_dict(self):
        return asdict(self)

class InteractiveStories:

    def __init__(self, client: OpenAI = None, conf_file: str = 'config/bots.toml', save_file: str = 'save.json', asset_dir: str = 'assets'):
        self.client = client or OpenAI()
        self.conf_file = conf_file
        self.save_file = save_file
        self.asset_dir = asset_dir
        # Create the asset directory if it doesn't exist.
        Path(self.asset_dir).mkdir(parents=True, exist_ok=True)
        
        self.image_args = ImageGenArgs()
        self.storystate = StoryState()
        self.assistants = AssistantsAPI(self.client)
        self.storyfuncs = Functions(
            self.set_story_config,
            self.get_story_config,
            self.get_entity_names,
            self.set_entity_bio,
            self.get_entity_bio,
            self.get_generated_image,
        )
        self.storybotid = None
        self.activesess = None
        self.action_log = []


    def log_action(self, action: str):
        self.action_log.append(action)

    @property
    def active_session(self):
        try:
            return self.storystate.sessions[self.activesess]
        except KeyError:
            return None
    
    @property
    def sessions(self):
        return self.storystate.sessions
    
    @property
    def messages(self):
        try:
            return self.active_session.messages
        except:
            return []
    
    @property
    def entities(self):
        try:
            return self.active_session.entities
        except:
            return []
    
    def load(self):
        self.log_action(f'Loading saved session from: {self.save_file}')

        try:
            with open(self.save_file, 'r') as f:
                save = json.load(f)
            
            self.storystate.load(save['storystate'])
            self.storybotid = save['storybotid']
            self.activesess = save['activesess']

            if self.assistants.assistant(self.storybotid) is None:
                self.storybotid = self.create_assistant()

            if self.activesess is None and len(self.storystate.sessions) > 0:
                self.activesess = self.storystate.sessions[-1].id
        except FileNotFoundError:
            self.log_action(f'No save file found. Creating a new assistant.')
            self.storybotid = self.create_assistant()
            self.activesess = self.assistants.add_thread().id

        self.activate_session(self.activesess)
    
    def save(self):
        self.log_action(f'Saving session to: {self.save_file}')

        with open(self.save_file, 'w') as f:
            json.dump({
                'storystate': self.storystate.as_dict,
                'storybotid': self.storybotid,
                'activesess': self.activesess,
            }, f)

    def create_assistant(self) -> str:
        self.log_action(f'Creating assistant from: {self.conf_file}')

        with open(resolve_file(self.conf_file), 'r') as f:
            storybot = toml.load(f)['storybot']

        return self.assistants.add_assistant(
            name=storybot['name'],
            description=storybot['desc'],
            instructions=render_template(storybot['instruction_template']),
            model=storybot['model'],
            tools=json.load(open(resolve_file(storybot['tools']))),
        ).id

    def update_assistant(self):
        self.log_action(f'Updating assistant from: {self.conf_file}')
        with open(resolve_file(self.conf_file), 'r') as f:
            storybot = toml.load(f)['storybot']

        self.assistants.update_assistant(
            self.storybotid,
            name=storybot['name'],
            description=storybot['desc'],
            instructions=render_template(storybot['instruction_template']),
            tools=json.load(open(resolve_file(storybot['tools']))),
            model=storybot['model'],
        )

    def activate_session(self, session_id: str = None):
        if session_id is None:
            self.log_action(f'Creating a session.')
            self.activesess = self.assistants.add_thread().id
        else:
            self.log_action(f'Activating session: {session_id}')
            self.activesess = session_id

        if self.activesess not in self.storystate.sessions:
            self.storystate.sessions.add(Session(self.activesess))

        self.save()
        # Load the messages from the session
        self.storystate.sessions[self.activesess].messages.load_messages(
            *[
                Message.from_api(message)
                for message in self.assistants.messages(thread_id=self.activesess)
            ]
        )
        
    def add_message(self, session_id: str, content: str, role: str = 'user', metadata: dict = None) -> Message:
        return self.messages.add(
            Message.from_api(
                self.assistants.add_message(session_id, role, content, metadata=metadata or {})
            )
        )
    
    def prompt_and_wait(self, content: str, role: str = 'user'):
        self.add_message(self.activesess, content, role, metadata={'type': 'prompt'})
        self.wait_for_run(
            self.activesess,
            self.assistants.add_run(self.activesess, self.storybotid).id,
            post_run_metadata={'type': 'narrative'}
        )

    def wait_for_run(self, session_id: str, run_id: str, post_run_metadata: dict = None):
        self.log_action(f'Waiting for run: {run_id} in session: {session_id} with post_run_metadata: {post_run_metadata}')
        
        try:
            run = self.assistants.wait_for_run(session_id, run_id)
        except RunError as e:
            self.log_action(f'Run failed: {e.run.status}. Error: {e.run.last_error.code} - {e.run.last_error.message}')
            raise e

        if run.status == 'requires_action':
            # Check the type of action required. 
            # Currently, the only action supported is submitting tool outputs.
            if run.required_action.type == 'submit_tool_outputs':
                self.log_action(f'Run requires function call results to be submitted.')

                # Call the functions.
                try:
                    called = run.required_action.submit_tool_outputs.tool_calls
                    called = list(self.call_functions(called))
                except Exception as e:
                    self.log_action(f'Error calling functions: {e}')
                    # Before we raise the exception, we need to cancel the run.
                    # Otherwise, the run will remain in the queue and block the thread.
                    self.assistants.cancel_run(session_id, run_id)
                    raise e

                self.log_action(f'Submitting function call output.')
                # Submit the function call results to the API
                subrun = self.assistants.submit_tool_outputs(session_id, run_id, called)
                # Wait for the run to complete.
                self.wait_for_run(session_id, subrun.id)
            else:
                raise Exception(f'Unknown action required: {run.required_action}')
        else:
            self.log_action(f'Run completed with status: {run.status}')
            # Update the local messages with the latest messages from the API.
            for message in self.assistants.messages(thread_id=session_id, after=self.messages.last.id):
                message = Message.from_api(message)

                # If the post run metadata contains key/value pairs not in the message metadata, add them.
                if post_run_metadata is not None:
                    current = message.metadata.copy()
                    # Add the post run metadata to the local message metadata.
                    message.metadata.update(post_run_metadata)

                    if current != message.metadata:
                        self.log_action(f'Updating message metadata: {message.metadata}')
                        # Update the message metadata for the API.
                        self.assistants.update_message(message.id, session_id, message.metadata)
                        
                # Add the message to the local session.
                self.messages.add(message)
        
    def call_functions(self, tool_calls, auto_save: bool = True):
        for call in tool_calls:
            self.log_action(f'Calling function: {call.function.name} with arguments: {call.function.arguments}')
            yield {
                'tool_call_id': call.id,
                'output': self.storyfuncs(call.function.name, **json.loads(call.function.arguments)),
            }
        if auto_save:
            self.save()
    
    def delete_session(self, session_id: str):
        self.log_action(f'Deleting session: {session_id}')
        # 1. attempt to delete the thread.
        if self.assistants.delete_thread(session_id):
            # 2. remove the session from the local storystate
            if session_id in self.storystate.sessions:
                del self.storystate.sessions[session_id]
            # 3. if the deleted thread was the active session, activate the last session, or create a new one.
            if session_id == self.activesess:
                self.activesess = None    
                try:
                    self.activesess = self.storystate.sessions.last.id
                except:
                    pass
                finally:
                    self.activate_session(self.activesess)
            
            self.save()
        else:
            raise Exception(f'Failed to delete thread: {session_id}')

    def get_narration(self, message_id: str, text: str, voice: str = 'alloy', format='opus', model='tts-1'):
        self.log_action(f'Generating narration for message: {message_id} with text: {text} and voice: {voice} in format: {format}')
        audio = generate_audio(self.client, text, voice=voice, format=format, model=model)
        asset = Asset(message_id, 'narration', format, data=audio.content, base=self.asset_dir)
        asset.save()
        self.active_session.assets.add(asset)
        self.save()
    
    def asset(self, message_id, name: str, format='opus'):
        try:
            asset = self.active_session.assets[f'{message_id}-{name}.{format}']
            self.log_action(f'Getting asset: {name} for message: {message_id} in format: {format}')
            return asset
        except KeyError:
            return None
    
    def get_last_run(self, session_id: str):
        self.log_action(f'Getting last run for session: {session_id}')
        return self.assistants.runs(session_id, order='desc', limit=1)[0]
    ###########################################################################
    # Assistant Functions 
    # 
    # These functions are called by AI assistants as "function calls."
    # The caller is responsible for calling the save method from this class 
    # to persist any changes to the local session.
    ###########################################################################
    def set_story_config(self, theme: str = None, guidelines: str = None):
        self.active_session.theme = theme
        self.active_session.guidelines = guidelines
        return f'Configured theme to {theme} and guidelines to {guidelines}'
    
    def get_story_config(self):
        return f'Theme: {self.active_session.theme} | Guidelines: {self.active_session.guidelines}'

    def get_entity_names(self):
        return ','.join([entity.name for entity in self.active_session.entities])

    def set_entity_bio(self, type: str = None,  name: str = None,  desc: str = None):
        if name not in self.active_session.entities:
            self.active_session.entities.add(Entity(type, name, desc))
        else:
            self.active_session.entities[name].type = type
            self.active_session.entities[name].desc = desc
        return f'Entity: {name} of type: {type} set to: {desc}'
    
    def get_entity_bio(self, name: str):
        return str(self.active_session.entities[name])

    def get_generated_image(self, desc: str, entities: list[str]):
        for name in entities:
            try:
                entity = self.entities[name]
                desc += f'Entity: {name} of type: {entity.type} is described as: {entity.desc}'
            except KeyError:
                print(f'Could not find entity: {name}')
                
        image = generate_image(self.client, desc, **self.image_args.as_dict()).data[0]
        # Log with the revised prompt.
        self.log_action(f'Generated image for prompt: {desc} with revised prompt: {image.revised_prompt}')
        # 
        asset = Asset(self.messages.last.id, 'visualization', 'png', data=b64decode(image.model_dump()["b64_json"]), base=self.asset_dir)
        asset.save()
        self.active_session.assets.add(asset)
        return f'Success! Image presented to the user.'
    ###########################################################################
    # UI Assistance Functions
    ###########################################################################
    def welcome(self):
        return render_template('welcome.md')
    
    def sessinfo(self):
        if self.activesess is None:
            return 'No active session.'
        return render_template('sessinfo.md', session=self.active_session)